import sys, os
import logging
import threading
import socket
import time
import re
try:
    # Venus image you tested with (pymodbus 2.5.3) exposes ModbusTcpClient
    # via pymodbus.client.sync (not pymodbus.client or pymodbus.client.tcp).
    from pymodbus.client.sync import ModbusTcpClient
    HAVE_PYMODBUS = True
except Exception as e:
    # If pymodbus is missing, we still want to export settings to keep the UI usable.
    ModbusTcpClient = None
    HAVE_PYMODBUS = False
    _PYMODBUS_IMPORT_ERROR = str(e)

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService
from settingsdevice import SettingsDevice
from dbus.mainloop.glib import DBusGMainLoop
import gi
from gi.repository import GLib
try:
    import dbus
except Exception:
    dbus = None

DBusGMainLoop(set_as_default=True)
logging.basicConfig(level=logging.INFO)


class SolarEdgeHeartbeat:
    MAX_DETECTED_SLOTS = 5
    DBUS_DISCOVERY_THROTTLE_SECS = 60
    SOLAREDGE_PRODUCT_KEYWORD = "SolarEdge"
    # Register map (zero-based addressing)
    REG_GRID_CONTROL = 0xF142       # UINT32
    REG_GRID_CONTROL_COMMIT = 0xF100  # UINT16 write-only
    REG_ENABLE_DYNAMIC = 0xF300     # UINT16
    REG_COMMAND_TIMEOUT = 0xF310    # UINT32
    REG_FALLBACK_LIMIT = 0xF312     # FLOAT32

    def _read_regs(self, client, address, count, slave_id):
        # pymodbus 2.x uses `unit`; some newer variants use `slave`.
        try:
            return client.read_holding_registers(address, count=count, unit=slave_id)
        except TypeError:
            return client.read_holding_registers(address, count=count, slave=slave_id)

    def _write_regs(self, client, address, values, slave_id):
        try:
            return client.write_registers(address, values, unit=slave_id)
        except TypeError:
            return client.write_registers(address, values, slave=slave_id)

    def __init__(self):
        # Victron's VeDbusService supports delaying DBus name registration.
        # Some Venus images warn about outdated registration unless register=False
        # is used and `register()` is called after adding mandatory paths.
        name = 'com.victronenergy.solaredge_heartbeat'
        self._dbus_registered_on_init = True
        try:
            self.dbus = VeDbusService(name, register=False)
            self._dbus_registered_on_init = False
        except TypeError:
            # Older/variant VeDbusService ctor doesn't support register=False.
            self.dbus = VeDbusService(name)

        self.dbus.add_path('/Mgmt/ProcessName', __file__)
        self.dbus.add_path('/Mgmt/ProcessVersion', '1.2')
        self.dbus.add_path('/Mgmt/Connection', 'Modbus TCP')

        self.dbus.add_path('/Status', 'Initializing...')
        self.dbus.add_path('/ActiveDevices', 'None')
        self.dbus.add_path('/GridControlEnabled', 0)
        self.dbus.add_path('/ActualTimeout', 0)
        self.dbus.add_path('/ActualFallbackPower', 0.0)

        # DBus-detected inverter info (populated when AutoDetectDbus=1)
        self.dbus.add_path('/DetectedInverterCount', 0)
        self.detected_slots = [
            {"serial": "", "ip": "", "slave": 0, "product": ""}
            for _ in range(self.MAX_DETECTED_SLOTS)
        ]
        self.slot_serials = [""] * self.MAX_DETECTED_SLOTS
        for idx in range(1, self.MAX_DETECTED_SLOTS + 1):
            self.dbus.add_path(f'/DetectedInverter{idx}/Serial', '')
            self.dbus.add_path(f'/DetectedInverter{idx}/Ip', '')
            self.dbus.add_path(f'/DetectedInverter{idx}/SlaveId', 0)
            self.dbus.add_path(f'/DetectedInverter{idx}/ProductName', '')
            self.dbus.add_path(f'/DetectedInverter{idx}/ActualTimeout', 0)
            self.dbus.add_path(f'/DetectedInverter{idx}/ActualFallbackPower', 0.0)

        self._last_dbus_discovery = 0

        # Changed to IpAddresses to support comma-separated lists
        self.settings = SettingsDevice(
            self.dbus.dbusconn,
            supportedSettings={
                'EnableService': ['/Settings/SolarEdge/EnableService', 1, 0, 1],
                'AutoDetectDbus': ['/Settings/SolarEdge/AutoDetectDbus', 0, 0, 1],
                'FallbackSlot1Enabled': ['/Settings/SolarEdge/FallbackSlot1Enabled', 0, 0, 1],
                'FallbackSlot2Enabled': ['/Settings/SolarEdge/FallbackSlot2Enabled', 0, 0, 1],
                'FallbackSlot3Enabled': ['/Settings/SolarEdge/FallbackSlot3Enabled', 0, 0, 1],
                'FallbackSlot4Enabled': ['/Settings/SolarEdge/FallbackSlot4Enabled', 0, 0, 1],
                'FallbackSlot5Enabled': ['/Settings/SolarEdge/FallbackSlot5Enabled', 0, 0, 1],
                'TargetTimeoutSlot1': ['/Settings/SolarEdge/TargetTimeoutSlot1', 60, 0, 3600],
                'TargetFallbackPowerSlot1': ['/Settings/SolarEdge/TargetFallbackPowerSlot1', 0.0, 0.0, 100.0],
                'TargetTimeoutSlot2': ['/Settings/SolarEdge/TargetTimeoutSlot2', 60, 0, 3600],
                'TargetFallbackPowerSlot2': ['/Settings/SolarEdge/TargetFallbackPowerSlot2', 0.0, 0.0, 100.0],
                'TargetTimeoutSlot3': ['/Settings/SolarEdge/TargetTimeoutSlot3', 60, 0, 3600],
                'TargetFallbackPowerSlot3': ['/Settings/SolarEdge/TargetFallbackPowerSlot3', 0.0, 0.0, 100.0],
                'TargetTimeoutSlot4': ['/Settings/SolarEdge/TargetTimeoutSlot4', 60, 0, 3600],
                'TargetFallbackPowerSlot4': ['/Settings/SolarEdge/TargetFallbackPowerSlot4', 0.0, 0.0, 100.0],
                'TargetTimeoutSlot5': ['/Settings/SolarEdge/TargetTimeoutSlot5', 60, 0, 3600],
                'TargetFallbackPowerSlot5': ['/Settings/SolarEdge/TargetFallbackPowerSlot5', 0.0, 0.0, 100.0],
            },
            eventCallback=self.handle_changed_setting,
        )

        GLib.timeout_add(10000, self.update)

        if not HAVE_PYMODBUS:
            self.dbus['/Status'] = 'Missing dependency: pymodbus'
            logging.error('pymodbus import failed: %s', _PYMODBUS_IMPORT_ERROR)

        # Finish DBus registration after mandatory paths have been added.
        if not self._dbus_registered_on_init:
            try:
                self.dbus.register()
            except Exception:
                # If register() isn't supported or fails, the service may still work.
                pass

    def handle_changed_setting(self, setting, oldvalue, newvalue):
        # When enabled, discover SolarEdge PV inverter connection info from the system DBus.
        if setting == 'AutoDetectDbus' and newvalue == 1:
            threading.Thread(target=self.discover_solar_edge_from_dbus).start()

    def scan_network(self):
        if not HAVE_PYMODBUS:
            GLib.idle_add(self.update_status, 'Missing dependency: pymodbus')
            return

        GLib.idle_add(self.update_status, 'Scanning network (0-255)...')
        found_ips = []
        found_slave = 126

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            base_ip = local_ip.rsplit('.', 1)[0]

            for i in range(1, 255):
                if self.settings['AutoDiscover'] == 0:
                    break
                test_ip = f"{base_ip}.{i}"

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((test_ip, 502))
                sock.close()

                if result == 0:
                    try:
                        client = ModbusTcpClient(test_ip, port=502, timeout=1)
                        if client.connect():
                            for test_slave in [126, 1, 2, 3]:
                                resp = self._read_regs(client, 40000, 2, test_slave)
                                if not resp.isError() and resp.registers[0] == 0x5375 and resp.registers[1] == 0x6E53:
                                    manuf_resp = self._read_regs(client, 40004, 1, test_slave)
                                    if not manuf_resp.isError() and manuf_resp.registers[0] == 0x536F:
                                        found_ips.append(test_ip)
                                        found_slave = test_slave
                                        break
                        client.close()
                    except:
                        pass

        except Exception as e:
            GLib.idle_add(self.update_status, f'Scan Error: {str(e)}')
            GLib.idle_add(self.reset_discover)
            return

        if found_ips:
            GLib.idle_add(self.apply_found_ips, found_ips, found_slave)
        else:
            GLib.idle_add(self.update_status, 'Scan complete: No SE found')
            GLib.idle_add(self.reset_discover)

    def apply_found_ips(self, new_ips, slave):
        current_list = [ip.strip() for ip in self.settings['IpAddresses'].split(',') if ip.strip()]
        for ip in new_ips:
            if ip not in current_list:
                current_list.append(ip)

        self.settings['IpAddresses'] = ", ".join(current_list)
        self.settings['SlaveId'] = slave
        self.settings['AutoDiscover'] = 0
        self.dbus['/Status'] = f'Found SE devices!'
        return False

    def reset_discover(self):
        self.settings['AutoDiscover'] = 0
        return False

    def update_status(self, msg):
        self.dbus['/Status'] = msg
        return False

    def _safe_busitem_value(self, bus, service_name, item_path):
        """
        Read a Victron BusItem value from DBus: Value at item_path (e.g. /Serial, /Mgmt/Connection).
        """
        try:
            obj = bus.get_object(service_name, item_path)
            # On Venus, Victron "BusItem" typically exposes methods (not properties):
            #   GetValue() -> variant
            #   GetText()  -> string
            busitem = dbus.Interface(obj, 'com.victronenergy.BusItem')
            try:
                # Prefer text for ProductName/Serial/Mgmt/Connection.
                txt = busitem.GetText()
                if txt is not None and txt != '':
                    return txt
            except Exception:
                pass

            try:
                return busitem.GetValue()
            except Exception:
                pass

            return None
        except Exception:
            return None

    def discover_solar_edge_from_dbus(self):
        # Avoid doing DBus work if module isn't available.
        if dbus is None:
            GLib.idle_add(self.update_status, 'DBus module not available')
            return

        GLib.idle_add(self.update_status, 'DBus autodetect: scanning SolarEdge pvinverter services...')

        try:
            bus = dbus.SystemBus()
            names = bus.list_names()
        except Exception as e:
            GLib.idle_add(self.update_status, f'DBus scan error: {e}')
            return

        detected = []

        # Typical services look like:
        # com.victronenergy.pvinverter.pv_7E054D25
        for service_name in names:
            if not service_name.startswith('com.victronenergy.pvinverter.pv_'):
                continue

            try:
                product_name = self._safe_busitem_value(bus, service_name, '/ProductName')
                if not product_name:
                    continue

                product_name_str = str(product_name)
                if self.SOLAREDGE_PRODUCT_KEYWORD.lower() not in product_name_str.lower():
                    continue

                serial = self._safe_busitem_value(bus, service_name, '/Serial')
                if not serial:
                    # Fallback to bus-name derived serial suffix
                    serial = service_name.split('pv_', 1)[1] if 'pv_' in service_name else ''
                serial_str = str(serial)

                mgmt_connection = self._safe_busitem_value(bus, service_name, '/Mgmt/Connection')
                mgmt_connection_str = str(mgmt_connection) if mgmt_connection is not None else ''

                # Example: "192.168.117.50 - 126 (sunspec)"
                m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s*-\s*(\d+)', mgmt_connection_str)
                if not m:
                    continue
                ip = m.group(1)
                slave = int(m.group(2))

                detected.append(
                    {
                        "serial": serial_str,
                        "ip": ip,
                        "slave": slave,
                        "product": product_name_str,
                    }
                )
            except Exception:
                # Ignore single device failures to avoid killing discovery.
                continue

        detected.sort(key=lambda d: d.get('serial', ''))
        GLib.idle_add(self.apply_detected_inverters, detected)
        GLib.idle_add(self.update_status, f'DBus autodetect: found {len(detected)} SolarEdge devices')

    def apply_detected_inverters(self, detected):
        # Keep discovered slots stable by sorting by serial.
        self.detected_slots = [
            {"serial": "", "ip": "", "slave": 0, "product": ""}
            for _ in range(self.MAX_DETECTED_SLOTS)
        ]

        count = min(len(detected), self.MAX_DETECTED_SLOTS)
        self.dbus['/DetectedInverterCount'] = count

        for i in range(self.MAX_DETECTED_SLOTS):
            if i < count:
                slot = detected[i]
                self.detected_slots[i] = slot
                self.dbus[f'/DetectedInverter{i+1}/Serial'] = slot.get('serial', '')
                self.dbus[f'/DetectedInverter{i+1}/Ip'] = slot.get('ip', '')
                self.dbus[f'/DetectedInverter{i+1}/SlaveId'] = int(slot.get('slave', 0) or 0)
                self.dbus[f'/DetectedInverter{i+1}/ProductName'] = slot.get('product', '')
                # Clear actual values until the next Modbus poll.
                self.dbus[f'/DetectedInverter{i+1}/ActualTimeout'] = 0
                self.dbus[f'/DetectedInverter{i+1}/ActualFallbackPower'] = 0.0
            else:
                self.dbus[f'/DetectedInverter{i+1}/Serial'] = ''
                self.dbus[f'/DetectedInverter{i+1}/Ip'] = ''
                self.dbus[f'/DetectedInverter{i+1}/SlaveId'] = 0
                self.dbus[f'/DetectedInverter{i+1}/ProductName'] = ''
                self.dbus[f'/DetectedInverter{i+1}/ActualTimeout'] = 0
                self.dbus[f'/DetectedInverter{i+1}/ActualFallbackPower'] = 0.0

        return False

    def update(self):
        if self.settings['EnableService'] == 0:
            self.dbus['/Status'] = 'Service Disabled'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        if not HAVE_PYMODBUS:
            self.dbus['/Status'] = 'Missing dependency: pymodbus'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        status_list = []
        ui_actual_t = 0
        ui_actual_f = 0.0
        ui_grid_enabled = 0
        overall_status = "Running OK"

        targets = []
        if self.settings['AutoDetectDbus'] != 1:
            self.dbus['/Status'] = 'DBus autodetect disabled'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        # Throttle refresh so we don't spam DBus.
        now = time.time()
        if (now - self._last_dbus_discovery) >= self.DBUS_DISCOVERY_THROTTLE_SECS:
            self._last_dbus_discovery = now
            threading.Thread(target=self.discover_solar_edge_from_dbus).start()

        for idx in range(self.MAX_DETECTED_SLOTS):
            slot_index = idx + 1
            enabled_key = f'FallbackSlot{slot_index}Enabled'
            if int(self.settings[enabled_key]) != 1:
                continue
            slot = self.detected_slots[idx]
            if not slot.get('ip'):
                continue
            targets.append((slot_index, slot.get('ip'), int(slot.get('slave', 0) or 0)))

        if not targets:
            self.dbus['/Status'] = 'No enabled SolarEdge inverters'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        # Loop through all enabled targets (per-slot)
        for idx, (slot_index, ip, slave_id) in enumerate(targets):
            client = ModbusTcpClient(ip, port=502, timeout=2)
            if client.connect():
                try:
                    resp = self._read_regs(client, self.REG_GRID_CONTROL, 2, slave_id)
                    if not resp.isError():
                        # 2x uint16 registers -> uint32, little word order
                        regs = resp.registers
                        val = (int(regs[1]) << 16) | int(regs[0])
                        if idx == 0:
                            ui_grid_enabled = val  # Display first device's state on UI

                        wrote_control = False
                        if val == 0:
                            self._write_regs(
                                client,
                                self.REG_GRID_CONTROL,
                                # uint32(1) -> [low_word, high_word] for little word order
                                [1 & 0xFFFF, (1 >> 16) & 0xFFFF],
                                slave_id,
                            )
                            wrote_control = True

                        # Ensure dynamic control is enabled (0xF300 == 1)
                        dyn_resp = self._read_regs(client, self.REG_ENABLE_DYNAMIC, 1, slave_id)
                        if not dyn_resp.isError():
                            if int(dyn_resp.registers[0]) != 1:
                                self._write_regs(client, self.REG_ENABLE_DYNAMIC, [1], slave_id)
                                wrote_control = True

                        # Commit only when we changed control enable flags
                        if wrote_control:
                            self._write_regs(client, self.REG_GRID_CONTROL_COMMIT, [1], slave_id)

                    t_resp = self._read_regs(client, self.REG_COMMAND_TIMEOUT, 2, slave_id)
                    f_resp = self._read_regs(client, self.REG_FALLBACK_LIMIT, 2, slave_id)

                    if not t_resp.isError() and not f_resp.isError():
                        # 2x uint16 -> uint32 (little word order)
                        t_regs = t_resp.registers
                        curr_t = (int(t_regs[1]) << 16) | int(t_regs[0])

                        # 2x uint16 -> float32 (little word order, with big-endian float bytes)
                        import struct
                        f_regs = f_resp.registers
                        # word_order='little' means the *low* word comes first.
                        # So swap word order to form standard big-endian float bytes.
                        f_bytes = int(f_regs[1]).to_bytes(2, 'big') + int(f_regs[0]).to_bytes(2, 'big')
                        curr_f = struct.unpack('>f', f_bytes)[0]

                        if idx == 0:
                            ui_actual_t = curr_t
                            ui_actual_f = curr_f

                        # Publish per-slot actual values for the UI
                        self.dbus[f'/DetectedInverter{slot_index}/ActualTimeout'] = curr_t
                        self.dbus[f'/DetectedInverter{slot_index}/ActualFallbackPower'] = curr_f

                        # Slot-specific target values from settings
                        target_t = int(self.settings[f'TargetTimeoutSlot{slot_index}'])
                        target_f = float(self.settings[f'TargetFallbackPowerSlot{slot_index}'])

                        wrote_setpoint = False
                        if curr_t != target_t:
                            self._write_regs(
                                client,
                                self.REG_COMMAND_TIMEOUT,
                                # uint32 -> [low_word, high_word]
                                [int(target_t) & 0xFFFF, (int(target_t) >> 16) & 0xFFFF],
                                slave_id,
                            )
                            wrote_setpoint = True
                        if curr_f != target_f:
                            import struct
                            # float32 -> 2x uint16 registers, word_order='little'
                            f_bytes = struct.pack('>f', float(target_f))
                            high_word = int.from_bytes(f_bytes[0:2], 'big')
                            low_word = int.from_bytes(f_bytes[2:4], 'big')
                            f_regs_out = [low_word, high_word]
                            self._write_regs(client, self.REG_FALLBACK_LIMIT, f_regs_out, slave_id)
                            wrote_setpoint = True

                        # Verify by re-reading once after write.
                        if wrote_setpoint:
                            t_verify = self._read_regs(client, self.REG_COMMAND_TIMEOUT, 2, slave_id)
                            f_verify = self._read_regs(client, self.REG_FALLBACK_LIMIT, 2, slave_id)
                            if not t_verify.isError() and not f_verify.isError():
                                tv = (int(t_verify.registers[1]) << 16) | int(t_verify.registers[0])
                                import struct
                                fb = int(f_verify.registers[1]).to_bytes(2, 'big') + int(f_verify.registers[0]).to_bytes(2, 'big')
                                fv = struct.unpack('>f', fb)[0]
                                # Keep UI aligned with verified values for first enabled slot
                                if idx == 0:
                                    ui_actual_t = tv
                                    ui_actual_f = fv

                        status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): OK t={curr_t}s f={curr_f:.2f}%")
                    else:
                        status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): REG ERR")
                        overall_status = "Errors Present"
                except Exception:
                    status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): ERR")
                    overall_status = "Errors Present"
                finally:
                    client.close()
            else:
                status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): OFF")
                overall_status = "Offline Devices"

        # Publish the aggregated data to the UI
        self.dbus['/ActiveDevices'] = " | ".join(status_list)
        self.dbus['/GridControlEnabled'] = ui_grid_enabled
        self.dbus['/ActualTimeout'] = ui_actual_t
        self.dbus['/ActualFallbackPower'] = ui_actual_f
        self.dbus['/Status'] = overall_status

        return True


if __name__ == "__main__":
    keeper = SolarEdgeHeartbeat()
    mainloop = GLib.MainLoop()
    mainloop.run()


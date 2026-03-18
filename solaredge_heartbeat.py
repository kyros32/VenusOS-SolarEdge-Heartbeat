import sys, os
import logging
import threading
import socket
import time
import re
try:
    from pymodbus.client.tcp import ModbusTcpClient
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

    def __init__(self):
        self.dbus = VeDbusService('com.victronenergy.solaredge_heartbeat')
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

        self._last_dbus_discovery = 0

        # Changed to IpAddresses to support comma-separated lists
        self.settings = SettingsDevice(
            self.dbus.dbusconn,
            supportedSettings={
                'IpAddresses': ['/Settings/SolarEdge/IpAddresses', '192.168.1.221', 0, 0],
                'SlaveId': ['/Settings/SolarEdge/SlaveId', 126, 1, 255],
                'TargetTimeout': ['/Settings/SolarEdge/TargetTimeout', 60, 0, 3600],
                'TargetFallback': ['/Settings/SolarEdge/TargetFallbackPower', 0.0, 0.0, 100.0],
                'EnableService': ['/Settings/SolarEdge/EnableService', 1, 0, 1],
                'AutoDiscover': ['/Settings/SolarEdge/AutoDiscover', 0, 0, 1],
                'AutoDetectDbus': ['/Settings/SolarEdge/AutoDetectDbus', 0, 0, 1],
                'FallbackSlot1Enabled': ['/Settings/SolarEdge/FallbackSlot1Enabled', 0, 0, 1],
                'FallbackSlot2Enabled': ['/Settings/SolarEdge/FallbackSlot2Enabled', 0, 0, 1],
                'FallbackSlot3Enabled': ['/Settings/SolarEdge/FallbackSlot3Enabled', 0, 0, 1],
                'FallbackSlot4Enabled': ['/Settings/SolarEdge/FallbackSlot4Enabled', 0, 0, 1],
                'FallbackSlot5Enabled': ['/Settings/SolarEdge/FallbackSlot5Enabled', 0, 0, 1],
            },
            eventCallback=self.handle_changed_setting,
        )

        GLib.timeout_add(10000, self.update)

        if not HAVE_PYMODBUS:
            self.dbus['/Status'] = 'Missing dependency: pymodbus'
            logging.error('pymodbus import failed: %s', _PYMODBUS_IMPORT_ERROR)

    def handle_changed_setting(self, setting, oldvalue, newvalue):
        if setting == 'AutoDiscover' and newvalue == 1:
            threading.Thread(target=self.scan_network).start()

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
                                resp = client.read_holding_registers(40000, count=2, slave=test_slave)
                                if not resp.isError() and resp.registers[0] == 0x5375 and resp.registers[1] == 0x6E53:
                                    manuf_resp = client.read_holding_registers(40004, count=1, slave=test_slave)
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
            props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
            return props.Get('com.victronenergy.BusItem', 'Value')
        except Exception:
            return None

    def discover_solar_edge_from_dbus(self):
        # Avoid doing DBus work if module isn't available.
        if dbus is None:
            GLib.idle_add(self.update_status, 'DBus module not available')
            return

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
            else:
                self.dbus[f'/DetectedInverter{i+1}/Serial'] = ''
                self.dbus[f'/DetectedInverter{i+1}/Ip'] = ''
                self.dbus[f'/DetectedInverter{i+1}/SlaveId'] = 0
                self.dbus[f'/DetectedInverter{i+1}/ProductName'] = ''

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

        target_t = int(self.settings['TargetTimeout'])
        target_f = float(self.settings['TargetFallback'])

        status_list = []
        ui_actual_t = 0
        ui_actual_f = 0.0
        ui_grid_enabled = 0
        overall_status = "Running OK"

        targets = []
        # Priority: DBus-based discovery mode
        if self.settings['AutoDetectDbus'] == 1:
            # Throttle refresh so we don't spam DBus.
            now = time.time()
            if (now - self._last_dbus_discovery) >= self.DBUS_DISCOVERY_THROTTLE_SECS:
                self._last_dbus_discovery = now
                threading.Thread(target=self.discover_solar_edge_from_dbus).start()

            for idx in range(self.MAX_DETECTED_SLOTS):
                enabled_key = f'FallbackSlot{idx+1}Enabled'
                if int(self.settings[enabled_key]) != 1:
                    continue
                slot = self.detected_slots[idx]
                if not slot.get('ip'):
                    continue
                targets.append((slot.get('ip'), int(slot.get('slave', 0) or 0), slot.get('serial', '')))
        else:
            # Optional network scan mode (older behavior)
            if self.settings['AutoDiscover'] == 1:
                return True

            # Parse the comma-separated list of IPs
            raw_ips = self.settings['IpAddresses']
            ips = [ip.strip() for ip in raw_ips.split(',') if ip.strip()]

            if not ips:
                self.dbus['/Status'] = 'No IPs configured'
                self.dbus['/ActiveDevices'] = 'None'
                return True

            slave_id = int(self.settings['SlaveId'])
            for ip in ips:
                targets.append((ip, slave_id, ''))

        if not targets:
            self.dbus['/Status'] = 'No enabled SolarEdge inverters'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        # Loop through all configured targets (ip + per-device modbus slave id)
        for idx, (ip, slave_id, serial_hint) in enumerate(targets):
            client = ModbusTcpClient(ip, port=502, timeout=2)
            if client.connect():
                try:
                    resp = client.read_holding_registers(61762, count=2, slave=slave_id)
                    if not resp.isError():
                        # 2x uint16 registers -> uint32, little word order
                        regs = resp.registers
                        val = (int(regs[1]) << 16) | int(regs[0])
                        if idx == 0:
                            ui_grid_enabled = val  # Display first device's state on UI

                        if val == 0:
                            client.write_registers(
                                61762,
                                # uint32(1) -> [low_word, high_word] for little word order
                                [1 & 0xFFFF, (1 >> 16) & 0xFFFF],
                                slave=slave_id,
                            )
                            client.write_registers(
                                61696,
                                [1 & 0xFFFF],
                                slave=slave_id,
                            )

                    t_resp = client.read_holding_registers(62224, count=2, slave=slave_id)
                    f_resp = client.read_holding_registers(62226, count=2, slave=slave_id)

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

                        if curr_t != target_t:
                            client.write_registers(
                                62224,
                                # uint32 -> [low_word, high_word]
                                [int(target_t) & 0xFFFF, (int(target_t) >> 16) & 0xFFFF],
                                slave=slave_id,
                            )
                        if curr_f != target_f:
                            import struct
                            # float32 -> 2x uint16 registers, word_order='little'
                            f_bytes = struct.pack('>f', float(target_f))
                            high_word = int.from_bytes(f_bytes[0:2], 'big')
                            low_word = int.from_bytes(f_bytes[2:4], 'big')
                            f_regs_out = [low_word, high_word]
                            client.write_registers(
                                62226,
                                f_regs_out,
                                slave=slave_id,
                            )

                    status_list.append(f"{ip} (id {slave_id}): OK")
                except Exception:
                    status_list.append(f"{ip} (id {slave_id}): ERR")
                    overall_status = "Errors Present"
                finally:
                    client.close()
            else:
                status_list.append(f"{ip} (id {slave_id}): OFF")
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


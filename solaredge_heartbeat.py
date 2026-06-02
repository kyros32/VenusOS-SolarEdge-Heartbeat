import sys, os
import logging
import threading
import socket
import time
import re
import struct
import glob
import subprocess
import signal
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

try:
    # Used to distinguish a connection-level failure (RST / single Modbus
    # session refused) from a normal Modbus exception (illegal address, etc.).
    from pymodbus.exceptions import ModbusIOException
except Exception:
    ModbusIOException = None

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
    # Some SolarEdge models (e.g. SE30K) serve only ONE Modbus TCP session.
    # dbus-fronius owns it, so a second session from us gets RST. For those we
    # briefly pause dbus-fronius, take the session, write+verify, and hand it
    # back. These registers are persistent and dbus-fronius's polling keeps the
    # inverter's comm-loss watchdog fed, so this only needs to run periodically.
    DBUS_FRONIUS_SERVICE = '/service/dbus-fronius'
    HANDOFF_REASSERT_SECS = 900          # periodic re-assert cadence (15 min)
    SESSION_FREE_TIMEOUT_SECS = 15       # max wait for the inverter to free its session
    HANDOFF_PROBE_TIMEOUT = 3            # per-probe socket timeout while waiting
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

        # Per-inverter (keyed by serial) connection mode and last-verified values.
        #   inv_mode[serial]    -> 'unknown' | 'inplace' | 'handoff'
        #   inv_actuals[serial] -> {'status','timeout','fallback','grid'}
        self.inv_mode = {}
        self.inv_actuals = {}
        # Serialize handoff windows so the periodic timer, startup probe and
        # settings-change triggers never stop dbus-fronius concurrently.
        self._handoff_lock = threading.Lock()
        # True while dbus-fronius is paused for a handoff. Discovery must be
        # skipped then, otherwise the vanished pvinverter services would clear
        # the detected slots until fronius restarts.
        self._handoff_active = False

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
        # Periodic re-assert for single-session (handoff) inverters. No-op when
        # there are none, so inverters that tolerate a 2nd session are never
        # disrupted by this timer.
        GLib.timeout_add(self.HANDOFF_REASSERT_SECS * 1000, self.periodic_handoff)

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

        # If we're killed (Venus shutdown / package update) mid-handoff,
        # dbus-fronius would stay paused and all PV monitoring would stop.
        # Restore it before exiting. Prefer GLib's signal integration since a
        # plain Python handler may not fire while the main loop is blocked.
        try:
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGTERM, self._on_term)
            GLib.unix_signal_add(GLib.PRIORITY_HIGH, signal.SIGINT, self._on_term)
        except Exception:
            signal.signal(signal.SIGTERM, lambda *a: self._on_term())
            signal.signal(signal.SIGINT, lambda *a: self._on_term())

    def _on_term(self, *args):
        if self._handoff_active:
            try:
                self._svc('-u', self._find_fronius_service())
            except Exception:
                pass
        os._exit(0)

    def handle_changed_setting(self, setting, oldvalue, newvalue):
        # When enabled, discover SolarEdge PV inverter connection info from the system DBus.
        if setting == 'AutoDetectDbus' and newvalue == 1:
            threading.Thread(target=self.discover_solar_edge_from_dbus).start()

        # Target/enable changes must reach handoff-mode inverters promptly (the
        # 10s loop only touches in-place ones). No-op when none are in handoff.
        if setting.startswith('TargetTimeoutSlot') or \
           setting.startswith('TargetFallbackPowerSlot') or \
           setting.startswith('FallbackSlot'):
            self.trigger_handoff()

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

        # dbus-fronius is paused for a handoff; its pvinverter services are gone
        # right now, so skip this cycle rather than clearing the detected slots.
        if self._handoff_active:
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
        # A discovery that began just before a handoff could land here with an
        # empty list (fronius down). Don't wipe known slots in that case.
        if not detected and self._handoff_active:
            return False
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

        # Actual (verified) values come from the per-serial cache so handoff
        # readings survive a discovery refresh instead of being zeroed.
        self._publish_slot_ui()
        return False

    def _publish_slot_ui(self):
        """Refresh per-slot Actual* paths from the per-serial cache (main loop)."""
        for i in range(self.MAX_DETECTED_SLOTS):
            serial = self.detected_slots[i].get('serial', '')
            a = self.inv_actuals.get(serial, {})
            self.dbus[f'/DetectedInverter{i+1}/ActualTimeout'] = int(a.get('timeout') or 0)
            self.dbus[f'/DetectedInverter{i+1}/ActualFallbackPower'] = float(a.get('fallback') or 0.0)
        return False

    def _is_conn_error(self, resp):
        """True for a connection-level failure (RST/timeout) vs a Modbus exception."""
        if ModbusIOException is not None and isinstance(resp, ModbusIOException):
            return True
        return type(resp).__name__ == 'ModbusIOException'

    def _configure_inverter(self, client, slot_index, slave_id):
        """Read/ensure grid-control config on an already-connected client.

        Returns a dict with 'status' in {OK, REG ERR, RST, ERR} plus the
        verified 'grid_enabled'/'timeout'/'fallback'. Does no DBus writes so it
        is safe to call from either the main loop or a handoff worker thread.
        """
        result = {'status': 'ERR', 'grid_enabled': None, 'timeout': None, 'fallback': None}
        try:
            resp = self._read_regs(client, self.REG_GRID_CONTROL, 2, slave_id)
            if self._is_conn_error(resp):
                result['status'] = 'RST'
                return result
            if not resp.isError():
                regs = resp.registers
                val = (int(regs[1]) << 16) | int(regs[0])
                result['grid_enabled'] = val

                wrote_control = False
                if val == 0:
                    self._write_regs(
                        client, self.REG_GRID_CONTROL,
                        [1 & 0xFFFF, (1 >> 16) & 0xFFFF], slave_id,
                    )
                    wrote_control = True

                dyn_resp = self._read_regs(client, self.REG_ENABLE_DYNAMIC, 1, slave_id)
                if not dyn_resp.isError() and int(dyn_resp.registers[0]) != 1:
                    self._write_regs(client, self.REG_ENABLE_DYNAMIC, [1], slave_id)
                    wrote_control = True

                if wrote_control:
                    self._write_regs(client, self.REG_GRID_CONTROL_COMMIT, [1], slave_id)

            t_resp = self._read_regs(client, self.REG_COMMAND_TIMEOUT, 2, slave_id)
            f_resp = self._read_regs(client, self.REG_FALLBACK_LIMIT, 2, slave_id)
            if self._is_conn_error(t_resp) or self._is_conn_error(f_resp):
                result['status'] = 'RST'
                return result

            if not t_resp.isError() and not f_resp.isError():
                t_regs = t_resp.registers
                curr_t = (int(t_regs[1]) << 16) | int(t_regs[0])
                f_regs = f_resp.registers
                f_bytes = int(f_regs[1]).to_bytes(2, 'big') + int(f_regs[0]).to_bytes(2, 'big')
                curr_f = struct.unpack('>f', f_bytes)[0]

                target_t = int(self.settings[f'TargetTimeoutSlot{slot_index}'])
                target_f = float(self.settings[f'TargetFallbackPowerSlot{slot_index}'])

                wrote_setpoint = False
                if curr_t != target_t:
                    self._write_regs(
                        client, self.REG_COMMAND_TIMEOUT,
                        [int(target_t) & 0xFFFF, (int(target_t) >> 16) & 0xFFFF], slave_id,
                    )
                    wrote_setpoint = True
                if curr_f != target_f:
                    fb = struct.pack('>f', float(target_f))
                    high_word = int.from_bytes(fb[0:2], 'big')
                    low_word = int.from_bytes(fb[2:4], 'big')
                    self._write_regs(client, self.REG_FALLBACK_LIMIT, [low_word, high_word], slave_id)
                    wrote_setpoint = True

                if wrote_setpoint:
                    t_verify = self._read_regs(client, self.REG_COMMAND_TIMEOUT, 2, slave_id)
                    f_verify = self._read_regs(client, self.REG_FALLBACK_LIMIT, 2, slave_id)
                    if not t_verify.isError() and not f_verify.isError():
                        curr_t = (int(t_verify.registers[1]) << 16) | int(t_verify.registers[0])
                        fb = int(f_verify.registers[1]).to_bytes(2, 'big') + int(f_verify.registers[0]).to_bytes(2, 'big')
                        curr_f = struct.unpack('>f', fb)[0]

                result['timeout'] = curr_t
                result['fallback'] = curr_f
                result['status'] = 'OK'
            else:
                result['status'] = 'REG ERR'
        except Exception:
            result['status'] = 'ERR'
        return result

    def _find_fronius_service(self):
        try:
            matches = glob.glob('/service/*fronius*')
            if matches:
                return matches[0]
        except Exception:
            pass
        return self.DBUS_FRONIUS_SERVICE

    def _svc(self, flag, service):
        try:
            subprocess.call(['svc', flag, service])
            return True
        except Exception as e:
            logging.error('svc %s %s failed: %s', flag, service, e)
            return False

    def _wait_session_free(self, ip, slave_id):
        """After pausing dbus-fronius, wait until the inverter accepts a real
        transaction (its previous session may linger a few seconds)."""
        deadline = time.time() + self.SESSION_FREE_TIMEOUT_SECS
        while time.time() < deadline:
            client = ModbusTcpClient(ip, port=502, timeout=self.HANDOFF_PROBE_TIMEOUT)
            try:
                if client.connect():
                    resp = self._read_regs(client, self.REG_GRID_CONTROL, 2, slave_id)
                    if not resp.isError():
                        return True
            except Exception:
                pass
            finally:
                try:
                    client.close()
                except Exception:
                    pass
            time.sleep(1)
        return False

    def periodic_handoff(self):
        """GLib timer callback: kick a handoff worker (no-op if nothing to do)."""
        threading.Thread(target=self.handoff_reassert, daemon=True).start()
        return True

    def trigger_handoff(self):
        threading.Thread(target=self.handoff_reassert, daemon=True).start()

    def handoff_reassert(self):
        """Pause dbus-fronius once, configure all enabled handoff-mode inverters,
        then always restart dbus-fronius. Runs in a worker thread."""
        if not HAVE_PYMODBUS:
            return
        if not self._handoff_lock.acquire(blocking=False):
            return  # a handoff is already in progress

        try:
            targets = []
            for idx in range(self.MAX_DETECTED_SLOTS):
                slot = self.detected_slots[idx]
                serial = slot.get('serial', '')
                ip = slot.get('ip', '')
                if not ip:
                    continue
                if int(self.settings[f'FallbackSlot{idx+1}Enabled']) != 1:
                    continue
                if self.inv_mode.get(serial) != 'handoff':
                    continue
                targets.append((idx + 1, ip, int(slot.get('slave', 0) or 0), serial))

            if not targets:
                return

            GLib.idle_add(self.update_status, 'Handoff: pausing dbus-fronius to reach inverter(s)...')
            svc_path = self._find_fronius_service()
            self._handoff_active = True
            if not self._svc('-d', svc_path):
                self._handoff_active = False
                GLib.idle_add(self.update_status, 'Handoff: could not stop dbus-fronius')
                return

            try:
                for (slot_index, ip, slave_id, serial) in targets:
                    if not self._wait_session_free(ip, slave_id):
                        self.inv_actuals[serial] = dict(self.inv_actuals.get(serial, {}), status='OFF')
                        continue
                    client = ModbusTcpClient(ip, port=502, timeout=5)
                    try:
                        if client.connect():
                            res = self._configure_inverter(client, slot_index, slave_id)
                            self.inv_actuals[serial] = {
                                'status': res['status'],
                                'timeout': res.get('timeout'),
                                'fallback': res.get('fallback'),
                                'grid': res.get('grid_enabled'),
                            }
                        else:
                            self.inv_actuals[serial] = dict(self.inv_actuals.get(serial, {}), status='OFF')
                    finally:
                        try:
                            client.close()
                        except Exception:
                            pass
            finally:
                # Critical: always hand the session back, even on error.
                self._svc('-u', svc_path)
                self._handoff_active = False

            GLib.idle_add(self._publish_slot_ui)
            GLib.idle_add(self.update_status, 'Handoff: re-asserted; dbus-fronius resumed')
        finally:
            self._handoff_lock.release()

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

        # Throttle refresh so we don't spam DBus. Never start discovery while a
        # handoff has dbus-fronius paused (its pvinverter services are gone).
        now = time.time()
        if not self._handoff_active and (now - self._last_dbus_discovery) >= self.DBUS_DISCOVERY_THROTTLE_SECS:
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
            targets.append((slot_index, slot.get('ip'), int(slot.get('slave', 0) or 0), slot.get('serial', '')))

        if not targets:
            self.dbus['/Status'] = 'No enabled SolarEdge inverters'
            self.dbus['/ActiveDevices'] = 'None'
            return True

        # Per-slot: maintain in-place when the inverter tolerates a 2nd Modbus
        # session; otherwise defer to the periodic handoff window.
        for pos, (slot_index, ip, slave_id, serial) in enumerate(targets):
            mode = self.inv_mode.get(serial, 'unknown')

            if mode == 'handoff':
                a = self.inv_actuals.get(serial, {})
                st = a.get('status')
                if st == 'OK':
                    status_list.append(
                        f"Slot {slot_index}: {ip} (id {slave_id}): HANDOFF OK "
                        f"t={int(a.get('timeout') or 0)}s f={float(a.get('fallback') or 0.0):.2f}%"
                    )
                    if pos == 0:
                        ui_grid_enabled = int(a.get('grid') or 0)
                        ui_actual_t = int(a.get('timeout') or 0)
                        ui_actual_f = float(a.get('fallback') or 0.0)
                elif st in (None, ''):
                    status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): HANDOFF pending")
                else:
                    status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): HANDOFF {st}")
                    overall_status = "Errors Present"
                continue

            # 'unknown' or 'inplace': use our own session.
            client = ModbusTcpClient(ip, port=502, timeout=2)
            if not client.connect():
                status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): OFF")
                overall_status = "Offline Devices"
                continue
            try:
                res = self._configure_inverter(client, slot_index, slave_id)
            finally:
                client.close()

            if res['status'] == 'RST':
                # Single Modbus session (e.g. SE30K) owned by dbus-fronius.
                self.inv_mode[serial] = 'handoff'
                status_list.append(
                    f"Slot {slot_index}: {ip} (id {slave_id}): single session, switching to handoff"
                )
                self.trigger_handoff()
                continue

            self.inv_mode[serial] = 'inplace'
            self.inv_actuals[serial] = {
                'status': res['status'],
                'timeout': res.get('timeout'),
                'fallback': res.get('fallback'),
                'grid': res.get('grid_enabled'),
            }

            if res['status'] == 'OK':
                if pos == 0:
                    ui_grid_enabled = int(res.get('grid_enabled') or 0)
                    ui_actual_t = int(res.get('timeout') or 0)
                    ui_actual_f = float(res.get('fallback') or 0.0)
                status_list.append(
                    f"Slot {slot_index}: {ip} (id {slave_id}): OK "
                    f"t={int(res.get('timeout') or 0)}s f={float(res.get('fallback') or 0.0):.2f}%"
                )
            elif res['status'] == 'REG ERR':
                status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): REG ERR")
                overall_status = "Errors Present"
            else:
                status_list.append(f"Slot {slot_index}: {ip} (id {slave_id}): ERR")
                overall_status = "Errors Present"

        # Refresh per-slot Actual* paths from cache (covers handoff slots).
        self._publish_slot_ui()

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


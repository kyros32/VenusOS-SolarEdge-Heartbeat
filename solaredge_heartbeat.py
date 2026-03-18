import sys, os
import logging
import threading
import socket
from pymodbus.client.tcp import ModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin

sys.path.insert(1, os.path.join(os.path.dirname(__file__), '/opt/victronenergy/dbus-systemcalc-py/ext/velib_python'))
from vedbus import VeDbusService
from settingsdevice import SettingsDevice
from dbus.mainloop.glib import DBusGMainLoop
import gi
from gi.repository import GLib

DBusGMainLoop(set_as_default=True)
logging.basicConfig(level=logging.INFO)


class SolarEdgeHeartbeat:
    def __init__(self):
        self.dbus = VeDbusService('com.victronenergy.solaredge')
        self.dbus.add_path('/Mgmt/ProcessName', __file__)
        self.dbus.add_path('/Mgmt/ProcessVersion', '1.2')
        self.dbus.add_path('/Mgmt/Connection', 'Modbus TCP')

        self.dbus.add_path('/Status', 'Initializing...')
        self.dbus.add_path('/ActiveDevices', 'None')
        self.dbus.add_path('/GridControlEnabled', 0)
        self.dbus.add_path('/ActualTimeout', 0)
        self.dbus.add_path('/ActualFallbackPower', 0.0)

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
            },
            eventCallback=self.handle_changed_setting,
        )

        GLib.timeout_add(10000, self.update)

    def handle_changed_setting(self, setting, oldvalue, newvalue):
        if setting == 'AutoDiscover' and newvalue == 1:
            threading.Thread(target=self.scan_network).start()

    def scan_network(self):
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

    def update(self):
        if self.settings['EnableService'] == 0:
            self.dbus['/Status'] = 'Service Disabled'
            self.dbus['/ActiveDevices'] = 'None'
            return True

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
        target_t = int(self.settings['TargetTimeout'])
        target_f = float(self.settings['TargetFallback'])

        status_list = []
        ui_actual_t = 0
        ui_actual_f = 0.0
        ui_grid_enabled = 0
        overall_status = "Running OK"

        # Loop through all configured IP addresses
        for idx, ip in enumerate(ips):
            client = ModbusTcpClient(ip, port=502, timeout=2)
            if client.connect():
                try:
                    resp = client.read_holding_registers(61762, count=2, slave=slave_id)
                    if not resp.isError():
                        val = client.convert_from_registers(
                            resp.registers,
                            ModbusClientMixin.DATATYPE.UINT32,
                            word_order='little',
                        )
                        if idx == 0:
                            ui_grid_enabled = val  # Display first device's state on UI

                        if val == 0:
                            client.write_registers(
                                61762,
                                client.convert_to_registers(
                                    1,
                                    ModbusClientMixin.DATATYPE.UINT32,
                                    word_order='little',
                                ),
                                slave=slave_id,
                            )
                            client.write_registers(
                                61696,
                                client.convert_to_registers(
                                    1,
                                    ModbusClientMixin.DATATYPE.UINT16,
                                    word_order='little',
                                ),
                                slave=slave_id,
                            )

                    t_resp = client.read_holding_registers(62224, count=2, slave=slave_id)
                    f_resp = client.read_holding_registers(62226, count=2, slave=slave_id)

                    if not t_resp.isError() and not f_resp.isError():
                        curr_t = client.convert_from_registers(
                            t_resp.registers,
                            ModbusClientMixin.DATATYPE.UINT32,
                            word_order='little',
                        )
                        curr_f = client.convert_from_registers(
                            f_resp.registers,
                            ModbusClientMixin.DATATYPE.FLOAT32,
                            word_order='little',
                        )

                        if idx == 0:
                            ui_actual_t = curr_t
                            ui_actual_f = curr_f

                        if curr_t != target_t:
                            client.write_registers(
                                62224,
                                client.convert_to_registers(
                                    target_t,
                                    ModbusClientMixin.DATATYPE.UINT32,
                                    word_order='little',
                                ),
                                slave=slave_id,
                            )
                        if curr_f != target_f:
                            client.write_registers(
                                62226,
                                client.convert_to_registers(
                                    target_f,
                                    ModbusClientMixin.DATATYPE.FLOAT32,
                                    word_order='little',
                                ),
                                slave=slave_id,
                            )

                    status_list.append(f"{ip}: OK")
                except Exception:
                    status_list.append(f"{ip}: ERR")
                    overall_status = "Errors Present"
                finally:
                    client.close()
            else:
                status_list.append(f"{ip}: OFF")
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


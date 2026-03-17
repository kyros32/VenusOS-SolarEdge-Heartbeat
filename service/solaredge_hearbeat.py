import sys, os
import logging
from pymodbus.client.tcp import ModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin

# Import Victron DBus libraries
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
        # 1. Create Local DBus Service (for actual read-only sensor values)
        self.dbus = VeDbusService('com.victronenergy.solaredge')
        self.dbus.add_path('/Mgmt/ProcessName', __file__)
        self.dbus.add_path('/Mgmt/ProcessVersion', '1.0')
        self.dbus.add_path('/Mgmt/Connection', 'Modbus TCP')
        
        self.dbus.add_path('/Status', 'Initializing...')
        self.dbus.add_path('/GridControlEnabled', 0)
        self.dbus.add_path('/ActualTimeout', 0)
        self.dbus.add_path('/ActualFallbackPower', 0.0)

        # 2. Create Persistent User Settings (Saved across reboots, editable via UI)
        self.settings = SettingsDevice(self.dbus.dbusconn, supportedSettings={
            'IpAddress': ['/Settings/SolarEdge/IpAddress', '192.168.1.221', 0, 0],
            'TargetTimeout': ['/Settings/SolarEdge/TargetTimeout', 60, 0, 3600],
            'TargetFallback': ['/Settings/SolarEdge/TargetFallbackPower', 0.0, 0.0, 100.0],
            'EnableService': ['/Settings/SolarEdge/EnableService', 1, 0, 1]
        }, eventCallback=None)
        
        # 3. Start the loop (Runs every 10 seconds)
        GLib.timeout_add(10000, self.update)

    def update(self):
        if self.settings['EnableService'] == 0:
            self.dbus['/Status'] = 'Service Disabled'
            return True

        ip = self.settings['IpAddress']
        client = ModbusTcpClient(ip, port=502, timeout=3)
        
        if client.connect():
            self.dbus['/Status'] = 'Connected'
            try:
                # -- Grid Control Check --
                resp = client.read_holding_registers(61762, count=2, slave=126)
                if not resp.isError():
                    val = client.convert_from_registers(resp.registers, ModbusClientMixin.DATATYPE.UINT32, word_order='little')
                    self.dbus['/GridControlEnabled'] = val
                    
                    if val == 0:
                        logging.info('Enabling Grid Control...')
                        client.write_registers(61762, client.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
                        client.write_registers(61696, client.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT16, word_order='little'), slave=126)
                        self.dbus['/Status'] = 'Committing Grid Control...'
                        return True # Exit loop early, wait for next 10s cycle to verify!

                # -- Limits Check --
                t_resp = client.read_holding_registers(62224, count=2, slave=126)
                f_resp = client.read_holding_registers(62226, count=2, slave=126)
                
                if not t_resp.isError() and not f_resp.isError():
                    actual_t = client.convert_from_registers(t_resp.registers, ModbusClientMixin.DATATYPE.UINT32, word_order='little')
                    actual_f = client.convert_from_registers(f_resp.registers, ModbusClientMixin.DATATYPE.FLOAT32, word_order='little')
                    
                    self.dbus['/ActualTimeout'] = actual_t
                    self.dbus['/ActualFallbackPower'] = actual_f
                    
                    target_t = int(self.settings['TargetTimeout'])
                    target_f = float(self.settings['TargetFallback'])

                    if actual_t != target_t:
                        logging.info(f'Updating Timeout to {target_t}s')
                        client.write_registers(62224, client.convert_to_registers(target_t, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
                    if actual_f != target_f:
                        logging.info(f'Updating Fallback to {target_f}%')
                        client.write_registers(62226, client.convert_to_registers(target_f, ModbusClientMixin.DATATYPE.FLOAT32, word_order='little'), slave=126)

            except Exception as e:
                self.dbus['/Status'] = f'Error: {str(e)}'
            finally:
                client.close()
        else:
            self.dbus['/Status'] = 'Connection Failed'
            
        return True # Return True to keep the GLib timer running

if __name__ == "__main__":
    keeper = SolarEdgeHeartbeat()
    mainloop = GLib.MainLoop()
    mainloop.run()

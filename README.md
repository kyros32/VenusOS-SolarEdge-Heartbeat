# VenusOS-SolarEdge-Heartbeat
A background service (watchdog) for Victron Venus OS that periodically connects to a SolarEdge inverter via Modbus TCP to enforce grid control limits, ensuring a safe fallback state if communication is lost.

## Features
* Runs silently in the background every 10 seconds.
* Automatically enables Grid Control on the SolarEdge inverter if disabled.
* Provides a native Victron GUI menu to adjust the Timeout and Fallback Power limits directly from the screen.
* Survives Venus OS firmware updates using SetupHelper.

## Repository structure:
```
VenusOS-SolarEdge-Heartbeat/
├── README.md
├── setup
├── version
├── solaredge_heartbeat.py
├── service/
│   └── run
└── qml/
    └── PageSolarEdge.qml
```

## Installation 
This driver is packaged to be used with [SetupHelper](https://github.com/kwindrem/SetupHelper), the standard Venus OS package manager.

**Prerequisites:**
You must have [SetupHelper installed](https://github.com/kwindrem/SetupHelper) on your Cerbo GX first.

**Install the Driver (No SSH Required):**
1. On your Cerbo GX touch screen or Remote Console, go to **Settings** -> **Package Manager**.
2. Scroll down to **Inactive packages** and select **New** (or "Add Custom Package").
3. Enter the following details exactly:
   * **Package name:** `VenusOS-SolarEdge-Heartbeat`
   * **GitHub user:** `kyros32`
   * **GitHub branch or tag:** `main`
4. Tap **Save**.
5. The package will now appear in your Inactive packages list. Select it, and press **Download** followed by **Install**.

*Alternatively, install via SSH:*
```bash
rm -rf /data/VenusOS-SolarEdge-Heartbeat
rm -rf /data/setupOptions/VenusOS-SolarEdge-Heartbeat
mkdir -p /data/VenusOS-SolarEdge-Heartbeat
wget -O - https://github.com/kyros32/VenusOS-SolarEdge-Heartbeat/archive/refs/heads/main.tar.gz | tar -xzf - -C /data/VenusOS-SolarEdge-Heartbeat --strip-components=1
chmod +x /data/VenusOS-SolarEdge-Heartbeat/setup
chmod +x /data/VenusOS-SolarEdge-Heartbeat/service/run
bash -x /data/VenusOS-SolarEdge-Heartbeat/setup install
```

## Run script manually from your Terminal (Mac OS) - it runs only once!!!
```bash
pip3 install "pymodbus>=3.8.6“ && python3 -c "
import time
from pymodbus.client.tcp import ModbusTcpClient
from pymodbus.client.mixin import ModbusClientMixin

ip = '192.168.1.221'
c = ModbusTcpClient(ip, port=502)

if c.connect():
    resp = c.read_holding_registers(61762, count=2, slave=126)
    if not resp.isError():
        val = c.convert_from_registers(resp.registers, ModbusClientMixin.DATATYPE.UINT32, word_order='little')
        if val == 0:
            print('⚙️ Enabling Grid Control...')
            c.write_registers(61762, c.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
            c.write_registers(61696, c.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT16, word_order='little'), slave=126)
            print('⏳ Waiting 60s to commit changes to the inverter...')
            time.sleep(60)
        else:
            print('✅ Grid Control already enabled.')
            
    print('⚙️ Setting Limits...')
    c.write_registers(62224, c.convert_to_registers(60, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
    c.write_registers(62226, c.convert_to_registers(0.0, ModbusClientMixin.DATATYPE.FLOAT32, word_order='little'), slave=126)
    c.close()
    print('🎉 Timeout set to 60s and Fallback Power set to 0.0%')
else:
    print('❌ Connection failed')
"
```

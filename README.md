# VenusOS-SolarEdge-Heartbeat

A background watchdog service for Victron Venus OS (Cerbo GX) that keeps one or more SolarEdge inverters configured for a safe grid-control fallback. It periodically verifies — over Modbus TCP — that each inverter's grid power-control is enabled and that its comms-loss **timeout** and **fallback power limit** match your targets, so PV production drops to a safe level if an inverter ever loses communication with the Victron system.

It auto-discovers SolarEdge inverters that Venus has already set up (no manual IP entry), supports up to 5 inverters independently, and automatically adapts to inverter models that allow only a single Modbus session.

## How it works

SolarEdge inverters support a grid power-control mode with a built-in **comms-loss watchdog**:

* While the controller (here, Venus OS) keeps talking to the inverter, the inverter follows normal operation.
* If communication stops for longer than the configured **timeout** (seconds), the inverter falls back to the configured **fallback power** (percentage of nominal output).

Setting the fallback power to `0%` means the inverter stops feeding the grid on a comms loss. This service makes sure that configuration is present, enabled, and matches your chosen targets — and keeps re-asserting it.

The relevant settings are written and verified via Modbus holding registers (see [Modbus register reference](#modbus-register-reference)).

## Features

* **Multi-inverter** — manage up to 5 SolarEdge inverters, each enabled independently ("slots" 1–5).
* **Auto-detection from DBus** — discovers SolarEdge `pvinverter` services already configured in Venus OS and reads each one's IP address and Modbus slave ID from its `Mgmt/Connection`. No IP scanning or manual entry required.
* **Per-slot targets** — independent **timeout** (0–3600 s) and **fallback power** (0–100 %) for every inverter.
* **Automatic connection mode per inverter** — uses a direct Modbus session where the inverter allows it, and a brief *session handoff* on models that allow only one (see below).
* **Native Victron GUI page** — enable the service, turn on auto-detect, view detected inverters, and per slot: enable fallback, set targets, and read back the inverter's current values.
* **Self-healing & periodic re-assert** — in-place inverters are checked every 10 s; handoff inverters are re-asserted every 15 minutes and immediately whenever you change a target or enable a slot.
* **Crash-safe** — never leaves Venus's own inverter driver disabled (see handoff mode).
* **Survives Venus OS firmware updates** using [SetupHelper](https://github.com/kwindrem/SetupHelper).

## Connection modes

### Why there are two modes

Some SolarEdge models accept several simultaneous Modbus TCP connections; others serve only **one** at a time. Venus OS's built-in `dbus-fronius` (SunSpec) driver permanently holds that single session to read the inverter's live data.

On a single-session model, this service's own connection is accepted at the TCP layer but every Modbus request is immediately reset (RST / `ConnectionReset`). Symptomatically this looked like "the device is offline and nothing happens" — and it explains why the same service worked on one model (e.g. SE17K, multi-session) but not another (e.g. SE30K, single-session).

The service detects this automatically and picks the right mode per inverter (keyed by serial number).

### In-place mode (multi-session inverters)

The service opens its own Modbus TCP connection every 10 seconds, alongside `dbus-fronius`, and reads/asserts the grid-control, timeout, and fallback registers directly. Nothing else is disturbed.

### Session-handoff mode (single-session inverters, e.g. SE30K)

When the service sees its connection being reset, it switches that inverter to **handoff** mode and, on a schedule, performs a short handoff:

1. Briefly stop `dbus-fronius` (`svc -d /service/dbus-fronius`) to free the single Modbus session.
2. Wait (up to 15 s) for the inverter to release the previous session.
3. Open its own connection, write + verify grid control / timeout / fallback.
4. **Always** restart `dbus-fronius` (`svc -u`), even if an error occurred.

Because the inverter stores this configuration **persistently**, and `dbus-fronius`'s normal polling keeps the comms-loss watchdog fed during day-to-day operation, the handoff only needs to run **periodically (every 15 minutes)** — plus immediately whenever you change a target or toggle a slot in the GUI.

If the service is stopped, updated, or the system shuts down **mid-handoff**, a signal handler restarts `dbus-fronius` before exiting, so Venus's PV monitoring is never left disabled.

> Note: handoff mode runs `svc -d`/`svc -u` on `dbus-fronius`, which requires the service to run as root (it does, under daemontools on Venus OS).

## GUI / Settings

The package installs a **SolarEdge Heartbeat** page (Settings menu) backed by these settings under `com.victronenergy.settings/Settings/SolarEdge`:

| Setting | Default | Description |
| --- | --- | --- |
| `EnableService` | 1 | Master on/off for the watchdog. |
| `AutoDetectDbus` | 0 | Discover SolarEdge inverters from Venus's DBus. **Required** for the service to act on any inverter. |
| `FallbackSlot{1..5}Enabled` | 0 | Apply/assert the fallback config to that detected slot. |
| `TargetTimeoutSlot{1..5}` | 60 | Comms-loss timeout in seconds (0–3600). |
| `TargetFallbackPowerSlot{1..5}` | 0.0 | Fallback power as a percentage of nominal (0–100). |

For each detected slot the page also shows the discovered **Serial**, **IP**, **Modbus ID**, and the inverter's **current** (read-back) timeout and fallback power.

### DBus paths published by the service (`com.victronenergy.solaredge_heartbeat`)

* `/Status` — overall service status text.
* `/ActiveDevices` — per-slot status line (e.g. `Slot 1: 10.0.0.57 (id 126): HANDOFF OK t=120s f=0.00%`).
* `/GridControlEnabled`, `/ActualTimeout`, `/ActualFallbackPower` — summary of the first active slot.
* `/DetectedInverterCount`.
* `/DetectedInverter{1..5}/` → `Serial`, `Ip`, `SlaveId`, `ProductName`, `ActualTimeout`, `ActualFallbackPower`.

## Repository structure
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
> On a **single-session** inverter (e.g. SE30K) you must first stop Venus's driver so the session is free, otherwise this script will be reset by the inverter:
> `svc -d /service/dbus-fronius` (run on the Cerbo, and `svc -u /service/dbus-fronius` afterwards to restore it).
```bash
pip3 install "pymodbus>=3.8.6" && python3 -c "
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
            print('Enabling Grid Control...')
            c.write_registers(61762, c.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
            c.write_registers(61696, c.convert_to_registers(1, ModbusClientMixin.DATATYPE.UINT16, word_order='little'), slave=126)
            print('Waiting 60s to commit changes to the inverter...')
            time.sleep(60)
        else:
            print('Grid Control already enabled.')

    print('Setting Limits...')
    c.write_registers(62224, c.convert_to_registers(60, ModbusClientMixin.DATATYPE.UINT32, word_order='little'), slave=126)
    c.write_registers(62226, c.convert_to_registers(0.0, ModbusClientMixin.DATATYPE.FLOAT32, word_order='little'), slave=126)
    c.close()
    print('Timeout set to 60s and Fallback Power set to 0.0%')
else:
    print('Connection failed')
"
```

## Modbus register reference

Addresses are zero-based holding-register addresses; values use little word order.

| Register | Address (hex / dec) | Type | Purpose |
| --- | --- | --- | --- |
| Grid control enable | `0xF142` / 61762 | UINT32 | Enable site-limit / grid power control. |
| Grid control commit | `0xF100` / 61696 | UINT16 | Commit grid-control changes. |
| Dynamic power control | `0xF300` / 62208 | UINT16 | Enable dynamic power control. |
| Command timeout | `0xF310` / 62224 | UINT32 | Comms-loss timeout (seconds). |
| Fallback power limit | `0xF312` / 62226 | FLOAT32 | Fallback power (% of nominal). |

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
mkdir -p /data/VenusOS-SolarEdge-Heartbeat
wget -O - [https://github.com/YOUR_GITHUB_USERNAME/VenusOS-SolarEdge-Heartbeat/archive/refs/heads/main.tar.gz](https://github.com/YOUR_GITHUB_USERNAME/VenusOS-SolarEdge-Heartbeat/archive/refs/heads/main.tar.gz) | tar -xzf - -C /data/VenusOS-SolarEdge-Heartbeat --strip-components=1
chmod +x /data/VenusOS-SolarEdge-Heartbeat/setup
chmod +x /data/VenusOS-SolarEdge-Heartbeat/service/run
/data/VenusOS-SolarEdge-Heartbeat/setup install
```

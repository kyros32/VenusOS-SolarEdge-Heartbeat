import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")

    // Define the data sources clearly
    property string settingsBind: "com.victronenergy.settings"
    property string serviceBind: "com.victronenergy.solaredge"

    model: VisibleItemModel {
        // 1. GLOBAL ENABLE
        MbSwitch {
            name: qsTr("Enable Heartbeat Service")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/EnableService")
        }

        // 2. STATUS SECTION
        MbItemText {
            description: qsTr("Connection Status")
            item.bind: Utils.path(serviceBind, "/Status")
        }

        MbItemText {
            description: qsTr("Active Devices")
            item.bind: Utils.path(serviceBind, "/ActiveDevices")
        }

        // 3. AUTO-DISCOVERY
        MbSwitch {
            name: qsTr("Scan Network for Inverters")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/AutoDiscover")
        }

        // 4. CONFIGURATION (INPUTS)
        MbEditBox {
            description: qsTr("Inverter IPs (comma separated)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/IpAddresses")
        }

        MbItemValue {
            description: qsTr("Modbus Slave ID")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/SlaveId")
        }

        // 5. LIVE INVERTER DATA
        MbItemValue {
            description: qsTr("Grid Control Enabled (Live)")
            item.bind: Utils.path(serviceBind, "/GridControlEnabled")
        }

        MbItemValue {
            description: qsTr("Current Timeout (Live)")
            item.bind: Utils.path(serviceBind, "/ActualTimeout")
            unit: "s"
        }

        MbItemValue {
            description: qsTr("Current Fallback Power (Live)")
            item.bind: Utils.path(serviceBind, "/ActualFallbackPower")
            unit: "%"
        }

        // 6. TARGET SETTINGS
        MbItemValue {
            description: qsTr("Target Timeout")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetTimeout")
            unit: "s"
        }

        MbItemValue {
            description: qsTr("Target Fallback Power")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetFallback")
            unit: "%"
        }
    }
}

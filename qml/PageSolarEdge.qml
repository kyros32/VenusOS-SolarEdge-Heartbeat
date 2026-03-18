import QtQuick 1.1
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")

    // Define bindings using VBusItem for maximum stability
    property string settingsBind: "com.victronenergy.settings"
    property string serviceBind: "com.victronenergy.solaredge"

    VBusItem { id: statusItem; bind: serviceBind + "/Status" }
    VBusItem { id: activeDevices; bind: serviceBind + "/ActiveDevices" }
    VBusItem { id: gridControl; bind: serviceBind + "/GridControlEnabled" }
    VBusItem { id: timeout; bind: serviceBind + "/ActualTimeout" }
    VBusItem { id: fallback; bind: serviceBind + "/ActualFallbackPower" }

    model: VisibleItemModel {
        MbSwitch {
            name: qsTr("Enable Heartbeat Service")
            bind: settingsBind + "/Settings/SolarEdge/EnableService"
        }

        MbItemText {
            description: qsTr("System Status")
            text: statusItem.valid ? statusItem.value : "--"
        }

        MbItemText {
            description: qsTr("Active Devices")
            text: activeDevices.valid ? activeDevices.value : "--"
            wrapMode: Text.WordWrap
        }

        MbSwitch {
            name: qsTr("Scan Network for Inverters")
            bind: settingsBind + "/Settings/SolarEdge/AutoDiscover"
        }

        MbEditBox {
            description: qsTr("Inverter IPs (comma separated)")
            item.bind: settingsBind + "/Settings/SolarEdge/IpAddresses"
        }

        MbItemValue {
            description: qsTr("Modbus Slave ID")
            item.bind: settingsBind + "/Settings/SolarEdge/SlaveId"
        }

        MbItemValue {
            description: qsTr("Grid Control Enabled")
            item: gridControl
        }

        MbItemValue {
            description: qsTr("Current Timeout")
            item: timeout
            unit: "s"
        }

        MbItemValue {
            description: qsTr("Current Fallback Power")
            item: fallback
            unit: "%"
        }

        MbItemValue {
            description: qsTr("Set Target Timeout")
            item.bind: settingsBind + "/Settings/SolarEdge/TargetTimeout"
            unit: "s"
        }

        MbItemValue {
            description: qsTr("Set Target Fallback Power")
            item.bind: settingsBind + "/Settings/SolarEdge/TargetFallbackPower"
            unit: "%"
        }
    }
}

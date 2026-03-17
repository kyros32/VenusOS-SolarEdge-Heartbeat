import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")
    
    property string settingsBind: "com.victronenergy.settings"
    property string dbusBind: "com.victronenergy.solaredge"

    VBusItem { id: statusItem; bind: Utils.path(dbusBind, "/Status") }
    VBusItem { id: activeDevicesItem; bind: Utils.path(dbusBind, "/ActiveDevices") }
    VBusItem { id: gridControlItem; bind: Utils.path(dbusBind, "/GridControlEnabled") }
    VBusItem { id: actualTimeoutItem; bind: Utils.path(dbusBind, "/ActualTimeout") }
    VBusItem { id: actualFallbackItem; bind: Utils.path(dbusBind, "/ActualFallbackPower") }

    model: VisibleItemModel {
        MbSwitch {
            name: qsTr("Enable Background Heartbeat")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/EnableService")
        }
        
        MbOK {
            description: qsTr("System Status")
            value: statusItem.valid ? statusItem.value : "--"
        }

        MbSwitch {
            name: qsTr("Scan Network for Inverters")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/AutoDiscover")
        }
        
        MbEditBox {
            description: qsTr("Inverter IPs (comma separated)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/IpAddresses")
        }

        MbEditBox {
            description: qsTr("Modbus Slave ID")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/SlaveId")
        }

        MbOK {
            description: qsTr("Active Devices")
            value: activeDevicesItem.valid ? activeDevicesItem.value : "--"
        }

        MbOK {
            description: qsTr("Grid Control Enabled")
            value: gridControlItem.valid ? gridControlItem.value : "--"
        }

        MbOK {
            description: qsTr("Current Timeout (s)")
            value: actualTimeoutItem.valid ? actualTimeoutItem.value : "--"
        }

        MbOK {
            description: qsTr("Current Fallback Power (%)")
            value: actualFallbackItem.valid ? actualFallbackItem.value : "--"
        }

        // --- User Inputs ---
        MbEditBox {
            description: qsTr("Set Target Timeout (s)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetTimeout")
        }

        MbEditBox {
            description: qsTr("Set Target Fallback Power (%)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetFallback")
        }
    }
}

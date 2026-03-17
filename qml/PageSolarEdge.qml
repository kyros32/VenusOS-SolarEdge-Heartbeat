import QtQuick 1.1
import com.victron.velib 1.0
import "utils.js" as Utils

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")
    
    property string settingsBind: "com.victronenergy.settings"
    property string dbusBind: "com.victronenergy.solaredge"

    model: VisibleItemModel {
        MbSwitch {
            name: qsTr("Enable Background Heartbeat")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/EnableService")
        }
        
        MbItemValue {
            description: qsTr("System Status")
            item.bind: Utils.path(dbusBind, "/Status")
        }

        MbSwitch {
            name: qsTr("Scan Network for Inverters")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/AutoDiscover")
        }
        
        MbItemValue {
            description: qsTr("Inverter IPs (Tap to Edit)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/IpAddresses")
        }

        MbItemValue {
            description: qsTr("Modbus Slave ID")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/SlaveId")
        }

        MbItemValue {
            description: qsTr("Active Devices")
            item.bind: Utils.path(dbusBind, "/ActiveDevices")
        }

        MbItemValue {
            description: qsTr("Grid Control Enabled")
            item.bind: Utils.path(dbusBind, "/GridControlEnabled")
        }

        MbItemValue {
            description: qsTr("Current Timeout (s)")
            item.bind: Utils.path(dbusBind, "/ActualTimeout")
        }

        MbItemValue {
            description: qsTr("Current Fallback Power (%)")
            item.bind: Utils.path(dbusBind, "/ActualFallbackPower")
        }

        // Target settings for user input
        MbItemValue {
            description: qsTr("Set Target Timeout (s)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetTimeout")
        }

        MbItemValue {
            description: qsTr("Set Target Fallback Power (%)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetFallback")
        }
    }
}

import QtQuick 1.1
import "utils.js" as Utils
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")
    
    property string settingsBind: "com.victronenergy.settings"
    property string dbusBind: "com.victronenergy.solaredge"

    model: VisualItemModel {
        MbSwitch {
            name: qsTr("Enable Background Heartbeat")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/EnableService")
        }
        
        MbItemText {
            description: qsTr("System Status")
            item.bind: Utils.path(dbusBind, "/Status")
        }

        MbSwitch {
            name: qsTr("Scan Network for Inverters")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/AutoDiscover")
        }
        
        // Editable box supporting multiple comma-separated IP addresses
        MbEditBox {
            description: qsTr("Inverter IPs (comma separated)")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/IpAddresses")
            matchString: "[0-9., ]*"
        }

        MbItemSpinBox {
            description: qsTr("Modbus Slave ID")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/SlaveId")
            stepSize: 1
            min: 1
            max: 255
        }

        // Live readout showing who is OK, ERR, or OFF
        MbItemText {
            description: qsTr("Active Devices")
            item.bind: Utils.path(dbusBind, "/ActiveDevices")
            wrapMode: Text.WordWrap
        }

        MbItemText {
            description: qsTr("Grid Control Enabled")
            item.bind: Utils.path(dbusBind, "/GridControlEnabled")
        }

        MbItemText {
            description: qsTr("Current Timeout")
            item.bind: Utils.path(dbusBind, "/ActualTimeout")
            item.text: item.valid ? item.value + " s" : "--"
        }

        MbItemText {
            description: qsTr("Current Fallback Power")
            item.bind: Utils.path(dbusBind, "/ActualFallbackPower")
            item.text: item.valid ? item.value.toFixed(1) + " %" : "--"
        }

        // --- User Inputs ---
        MbItemSpinBox {
            description: qsTr("Set Target Timeout")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetTimeout")
            stepSize: 1
            min: 0
            max: 3600
            unit: "s"
        }

        MbItemSpinBox {
            description: qsTr("Set Target Fallback Power")
            bind: Utils.path(settingsBind, "/Settings/SolarEdge/TargetFallback")
            stepSize: 1
            min: 0
            max: 100
            unit: "%"
        }
    }
}

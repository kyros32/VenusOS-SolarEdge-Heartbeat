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
            description: qsTr("Connection Status")
            item.bind: Utils.path(dbusBind, "/Status")
        }
        
        MbItemText {
            description: qsTr("Inverter IP Address")
            item.bind: Utils.path(settingsBind, "/Settings/SolarEdge/IpAddress")
        }

        MbItemText {
            description: qsTr("Grid Control Enabled (Actual)")
            item.bind: Utils.path(dbusBind, "/GridControlEnabled")
        }

        MbItemText {
            description: qsTr("Current Timeout (Actual)")
            item.bind: Utils.path(dbusBind, "/ActualTimeout")
            item.text: item.valid ? item.value + " s" : "--"
        }

        MbItemText {
            description: qsTr("Current Fallback Power (Actual)")
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

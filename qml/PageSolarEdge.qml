import QtQuick 1.1
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")

    // Define bindings using VBusItem for maximum stability
    property string settingsBind: "com.victronenergy.settings"

    VBusItem { id: statusItem; bind: "com.victronenergy.solaredge_heartbeat/Status" }
    VBusItem { id: activeDevices; bind: "com.victronenergy.solaredge_heartbeat/ActiveDevices" }
    VBusItem { id: gridControl; bind: "com.victronenergy.solaredge_heartbeat/GridControlEnabled" }
    VBusItem { id: timeout; bind: "com.victronenergy.solaredge_heartbeat/ActualTimeout" }
    VBusItem { id: fallback; bind: "com.victronenergy.solaredge_heartbeat/ActualFallbackPower" }
    VBusItem { id: detectedCount; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverterCount" }

    // Fixed slots (1..5) - Discovery populates detected info, user enables which slot(s) to apply fallback to.
    VBusItem { id: slot1Serial; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter1/Serial" }
    VBusItem { id: slot1Ip; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter1/Ip" }
    VBusItem { id: slot1Slave; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter1/SlaveId" }

    VBusItem { id: slot2Serial; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter2/Serial" }
    VBusItem { id: slot2Ip; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter2/Ip" }
    VBusItem { id: slot2Slave; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter2/SlaveId" }

    VBusItem { id: slot3Serial; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter3/Serial" }
    VBusItem { id: slot3Ip; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter3/Ip" }
    VBusItem { id: slot3Slave; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter3/SlaveId" }

    VBusItem { id: slot4Serial; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter4/Serial" }
    VBusItem { id: slot4Ip; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter4/Ip" }
    VBusItem { id: slot4Slave; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter4/SlaveId" }

    VBusItem { id: slot5Serial; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter5/Serial" }
    VBusItem { id: slot5Ip; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter5/Ip" }
    VBusItem { id: slot5Slave; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter5/SlaveId" }

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
            name: qsTr("Auto-detect SolarEdge inverters from DBus")
            bind: settingsBind + "/Settings/SolarEdge/AutoDetectDbus"
        }

        MbItemText {
            description: qsTr("Detected SolarEdge Inverters")
            text: detectedCount.valid ? detectedCount.value : "--"
        }

        MbItemText { description: qsTr("Slot 1 Serial"); text: slot1Serial.valid ? slot1Serial.value : "--" }
        MbItemText { description: qsTr("Slot 1 IP"); text: slot1Ip.valid ? slot1Ip.value : "--" }
        MbItemText { description: qsTr("Slot 1 ID"); text: slot1Slave.valid ? slot1Slave.value : "--" }
        MbSwitch {
            name: qsTr("Fallback on Slot 1")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot1Enabled"
        }

        MbItemText { description: qsTr("Slot 2 Serial"); text: slot2Serial.valid ? slot2Serial.value : "--" }
        MbItemText { description: qsTr("Slot 2 IP"); text: slot2Ip.valid ? slot2Ip.value : "--" }
        MbItemText { description: qsTr("Slot 2 ID"); text: slot2Slave.valid ? slot2Slave.value : "--" }
        MbSwitch {
            name: qsTr("Fallback on Slot 2")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot2Enabled"
        }

        MbItemText { description: qsTr("Slot 3 Serial"); text: slot3Serial.valid ? slot3Serial.value : "--" }
        MbItemText { description: qsTr("Slot 3 IP"); text: slot3Ip.valid ? slot3Ip.value : "--" }
        MbItemText { description: qsTr("Slot 3 ID"); text: slot3Slave.valid ? slot3Slave.value : "--" }
        MbSwitch {
            name: qsTr("Fallback on Slot 3")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot3Enabled"
        }

        MbItemText { description: qsTr("Slot 4 Serial"); text: slot4Serial.valid ? slot4Serial.value : "--" }
        MbItemText { description: qsTr("Slot 4 IP"); text: slot4Ip.valid ? slot4Ip.value : "--" }
        MbItemText { description: qsTr("Slot 4 ID"); text: slot4Slave.valid ? slot4Slave.value : "--" }
        MbSwitch {
            name: qsTr("Fallback on Slot 4")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot4Enabled"
        }

        MbItemText { description: qsTr("Slot 5 Serial"); text: slot5Serial.valid ? slot5Serial.value : "--" }
        MbItemText { description: qsTr("Slot 5 IP"); text: slot5Ip.valid ? slot5Ip.value : "--" }
        MbItemText { description: qsTr("Slot 5 ID"); text: slot5Slave.valid ? slot5Slave.value : "--" }
        MbSwitch {
            name: qsTr("Fallback on Slot 5")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot5Enabled"
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

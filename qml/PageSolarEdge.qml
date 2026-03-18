import QtQuick 1.1
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")

    // Define bindings using VBusItem for maximum stability
    property string settingsBind: "com.victronenergy.settings"
    property string serviceBind: "com.victronenergy.solaredge_heartbeat"

    VBusItem { id: statusItem; bind: serviceBind + "/Status" }
    VBusItem { id: activeDevices; bind: serviceBind + "/ActiveDevices" }
    VBusItem { id: gridControl; bind: serviceBind + "/GridControlEnabled" }
    VBusItem { id: timeout; bind: serviceBind + "/ActualTimeout" }
    VBusItem { id: fallback; bind: serviceBind + "/ActualFallbackPower" }
    VBusItem { id: detectedCount; bind: serviceBind + "/DetectedInverterCount" }

    // Fixed slots (1..5) - Discovery populates detected info, user enables which slot(s) to apply fallback to.
    VBusItem { id: slot1Serial; bind: serviceBind + "/DetectedInverter1/Serial" }
    VBusItem { id: slot1Ip; bind: serviceBind + "/DetectedInverter1/Ip" }
    VBusItem { id: slot1Slave; bind: serviceBind + "/DetectedInverter1/SlaveId" }

    VBusItem { id: slot2Serial; bind: serviceBind + "/DetectedInverter2/Serial" }
    VBusItem { id: slot2Ip; bind: serviceBind + "/DetectedInverter2/Ip" }
    VBusItem { id: slot2Slave; bind: serviceBind + "/DetectedInverter2/SlaveId" }

    VBusItem { id: slot3Serial; bind: serviceBind + "/DetectedInverter3/Serial" }
    VBusItem { id: slot3Ip; bind: serviceBind + "/DetectedInverter3/Ip" }
    VBusItem { id: slot3Slave; bind: serviceBind + "/DetectedInverter3/SlaveId" }

    VBusItem { id: slot4Serial; bind: serviceBind + "/DetectedInverter4/Serial" }
    VBusItem { id: slot4Ip; bind: serviceBind + "/DetectedInverter4/Ip" }
    VBusItem { id: slot4Slave; bind: serviceBind + "/DetectedInverter4/SlaveId" }

    VBusItem { id: slot5Serial; bind: serviceBind + "/DetectedInverter5/Serial" }
    VBusItem { id: slot5Ip; bind: serviceBind + "/DetectedInverter5/Ip" }
    VBusItem { id: slot5Slave; bind: serviceBind + "/DetectedInverter5/SlaveId" }

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

        MbItemText {
            description: qsTr("Slot 1")
            text: slot1Serial.valid && slot1Serial.value !== "" ? (slot1Serial.value + " " + slot1Ip.value + " (id " + slot1Slave.value + ")") : "--"
            wrapMode: Text.WordWrap
        }
        MbSwitch {
            name: qsTr("Fallback on Slot 1")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot1Enabled"
        }

        MbItemText {
            description: qsTr("Slot 2")
            text: slot2Serial.valid && slot2Serial.value !== "" ? (slot2Serial.value + " " + slot2Ip.value + " (id " + slot2Slave.value + ")") : "--"
            wrapMode: Text.WordWrap
        }
        MbSwitch {
            name: qsTr("Fallback on Slot 2")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot2Enabled"
        }

        MbItemText {
            description: qsTr("Slot 3")
            text: slot3Serial.valid && slot3Serial.value !== "" ? (slot3Serial.value + " " + slot3Ip.value + " (id " + slot3Slave.value + ")") : "--"
            wrapMode: Text.WordWrap
        }
        MbSwitch {
            name: qsTr("Fallback on Slot 3")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot3Enabled"
        }

        MbItemText {
            description: qsTr("Slot 4")
            text: slot4Serial.valid && slot4Serial.value !== "" ? (slot4Serial.value + " " + slot4Ip.value + " (id " + slot4Slave.value + ")") : "--"
            wrapMode: Text.WordWrap
        }
        MbSwitch {
            name: qsTr("Fallback on Slot 4")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot4Enabled"
        }

        MbItemText {
            description: qsTr("Slot 5")
            text: slot5Serial.valid && slot5Serial.value !== "" ? (slot5Serial.value + " " + slot5Ip.value + " (id " + slot5Slave.value + ")") : "--"
            wrapMode: Text.WordWrap
        }
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

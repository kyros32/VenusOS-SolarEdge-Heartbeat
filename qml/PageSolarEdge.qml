import QtQuick 2.0
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

        MbItemValue {
            description: qsTr("System Status")
            item: statusItem
        }

        MbItemValue {
            description: qsTr("Active Devices")
            item: activeDevices
        }

        MbSwitch {
            name: qsTr("Auto-detect SolarEdge inverters from DBus")
            bind: settingsBind + "/Settings/SolarEdge/AutoDetectDbus"
        }

        MbItemValue {
            description: qsTr("Detected SolarEdge Inverters")
            item: detectedCount
        }

        MbItemValue { description: qsTr("Slot 1 Serial"); item: slot1Serial }
        MbItemValue { description: qsTr("Slot 1 IP"); item: slot1Ip }
        MbItemValue { description: qsTr("Slot 1 ID"); item: slot1Slave }
        MbSwitch {
            name: qsTr("Fallback on Slot 1")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot1Enabled"
        }

        MbItemValue { description: qsTr("Slot 2 Serial"); item: slot2Serial }
        MbItemValue { description: qsTr("Slot 2 IP"); item: slot2Ip }
        MbItemValue { description: qsTr("Slot 2 ID"); item: slot2Slave }
        MbSwitch {
            name: qsTr("Fallback on Slot 2")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot2Enabled"
        }

        MbItemValue { description: qsTr("Slot 3 Serial"); item: slot3Serial }
        MbItemValue { description: qsTr("Slot 3 IP"); item: slot3Ip }
        MbItemValue { description: qsTr("Slot 3 ID"); item: slot3Slave }
        MbSwitch {
            name: qsTr("Fallback on Slot 3")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot3Enabled"
        }

        MbItemValue { description: qsTr("Slot 4 Serial"); item: slot4Serial }
        MbItemValue { description: qsTr("Slot 4 IP"); item: slot4Ip }
        MbItemValue { description: qsTr("Slot 4 ID"); item: slot4Slave }
        MbSwitch {
            name: qsTr("Fallback on Slot 4")
            bind: settingsBind + "/Settings/SolarEdge/FallbackSlot4Enabled"
        }

        MbItemValue { description: qsTr("Slot 5 Serial"); item: slot5Serial }
        MbItemValue { description: qsTr("Slot 5 IP"); item: slot5Ip }
        MbItemValue { description: qsTr("Slot 5 ID"); item: slot5Slave }
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

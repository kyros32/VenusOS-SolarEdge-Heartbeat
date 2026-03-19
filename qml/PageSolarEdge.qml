import QtQuick 2.0
import com.victron.velib 1.0

MbPage {
    id: root
    title: qsTr("SolarEdge Heartbeat")

    // Define bindings using VBusItem for maximum stability
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

    // Per-slot current (Actual*) values
    VBusItem { id: slot1ActualTimeout; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter1/ActualTimeout" }
    VBusItem { id: slot1ActualFallback; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter1/ActualFallbackPower" }
    VBusItem { id: slot2ActualTimeout; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter2/ActualTimeout" }
    VBusItem { id: slot2ActualFallback; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter2/ActualFallbackPower" }
    VBusItem { id: slot3ActualTimeout; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter3/ActualTimeout" }
    VBusItem { id: slot3ActualFallback; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter3/ActualFallbackPower" }
    VBusItem { id: slot4ActualTimeout; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter4/ActualTimeout" }
    VBusItem { id: slot4ActualFallback; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter4/ActualFallbackPower" }
    VBusItem { id: slot5ActualTimeout; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter5/ActualTimeout" }
    VBusItem { id: slot5ActualFallback; bind: "com.victronenergy.solaredge_heartbeat/DetectedInverter5/ActualFallbackPower" }

    // Per-slot target values from settings
    VBusItem { id: slot1TargetTimeout; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetTimeoutSlot1" }
    VBusItem { id: slot1TargetFallback; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetFallbackPowerSlot1" }
    VBusItem { id: slot2TargetTimeout; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetTimeoutSlot2" }
    VBusItem { id: slot2TargetFallback; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetFallbackPowerSlot2" }
    VBusItem { id: slot3TargetTimeout; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetTimeoutSlot3" }
    VBusItem { id: slot3TargetFallback; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetFallbackPowerSlot3" }
    VBusItem { id: slot4TargetTimeout; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetTimeoutSlot4" }
    VBusItem { id: slot4TargetFallback; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetFallbackPowerSlot4" }
    VBusItem { id: slot5TargetTimeout; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetTimeoutSlot5" }
    VBusItem { id: slot5TargetFallback; bind: "com.victronenergy.settings/Settings/SolarEdge/TargetFallbackPowerSlot5" }

    model: VisibleItemModel {
        MbSwitch {
            name: qsTr("Enable Heartbeat Service")
            bind: "com.victronenergy.settings/Settings/SolarEdge/EnableService"
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
            bind: "com.victronenergy.settings/Settings/SolarEdge/AutoDetectDbus"
        }

        MbItemValue {
            description: qsTr("Detected SolarEdge Inverters")
            item: detectedCount
        }

        // Slot 1
        MbItemValue { description: qsTr("Slot 1 Serial"); item: slot1Serial }
        MbItemValue { description: qsTr("Slot 1 IP"); item: slot1Ip }
        MbItemValue { description: qsTr("Slot 1 ID"); item: slot1Slave }
        MbItemValue { description: qsTr("Slot 1 Current Timeout (s)"); item: slot1ActualTimeout }
        MbItemValue { description: qsTr("Slot 1 Current Fallback Power (%)"); item: slot1ActualFallback }
        MbSwitch { name: qsTr("Fallback on Slot 1"); bind: "com.victronenergy.settings/Settings/SolarEdge/FallbackSlot1Enabled" }
        MbItemValue { description: qsTr("Slot 1 Target Timeout (s)"); item: slot1TargetTimeout }
        MbItemValue { description: qsTr("Slot 1 Target Fallback Power (%)"); item: slot1TargetFallback }

        // Slot 2
        MbItemValue { description: qsTr("Slot 2 Serial"); item: slot2Serial }
        MbItemValue { description: qsTr("Slot 2 IP"); item: slot2Ip }
        MbItemValue { description: qsTr("Slot 2 ID"); item: slot2Slave }
        MbItemValue { description: qsTr("Slot 2 Current Timeout (s)"); item: slot2ActualTimeout }
        MbItemValue { description: qsTr("Slot 2 Current Fallback Power (%)"); item: slot2ActualFallback }
        MbSwitch { name: qsTr("Fallback on Slot 2"); bind: "com.victronenergy.settings/Settings/SolarEdge/FallbackSlot2Enabled" }
        MbItemValue { description: qsTr("Slot 2 Target Timeout (s)"); item: slot2TargetTimeout }
        MbItemValue { description: qsTr("Slot 2 Target Fallback Power (%)"); item: slot2TargetFallback }

        // Slot 3
        MbItemValue { description: qsTr("Slot 3 Serial"); item: slot3Serial }
        MbItemValue { description: qsTr("Slot 3 IP"); item: slot3Ip }
        MbItemValue { description: qsTr("Slot 3 ID"); item: slot3Slave }
        MbItemValue { description: qsTr("Slot 3 Current Timeout (s)"); item: slot3ActualTimeout }
        MbItemValue { description: qsTr("Slot 3 Current Fallback Power (%)"); item: slot3ActualFallback }
        MbSwitch { name: qsTr("Fallback on Slot 3"); bind: "com.victronenergy.settings/Settings/SolarEdge/FallbackSlot3Enabled" }
        MbItemValue { description: qsTr("Slot 3 Target Timeout (s)"); item: slot3TargetTimeout }
        MbItemValue { description: qsTr("Slot 3 Target Fallback Power (%)"); item: slot3TargetFallback }

        // Slot 4
        MbItemValue { description: qsTr("Slot 4 Serial"); item: slot4Serial }
        MbItemValue { description: qsTr("Slot 4 IP"); item: slot4Ip }
        MbItemValue { description: qsTr("Slot 4 ID"); item: slot4Slave }
        MbItemValue { description: qsTr("Slot 4 Current Timeout (s)"); item: slot4ActualTimeout }
        MbItemValue { description: qsTr("Slot 4 Current Fallback Power (%)"); item: slot4ActualFallback }
        MbSwitch { name: qsTr("Fallback on Slot 4"); bind: "com.victronenergy.settings/Settings/SolarEdge/FallbackSlot4Enabled" }
        MbItemValue { description: qsTr("Slot 4 Target Timeout (s)"); item: slot4TargetTimeout }
        MbItemValue { description: qsTr("Slot 4 Target Fallback Power (%)"); item: slot4TargetFallback }

        // Slot 5
        MbItemValue { description: qsTr("Slot 5 Serial"); item: slot5Serial }
        MbItemValue { description: qsTr("Slot 5 IP"); item: slot5Ip }
        MbItemValue { description: qsTr("Slot 5 ID"); item: slot5Slave }
        MbItemValue { description: qsTr("Slot 5 Current Timeout (s)"); item: slot5ActualTimeout }
        MbItemValue { description: qsTr("Slot 5 Current Fallback Power (%)"); item: slot5ActualFallback }
        MbSwitch { name: qsTr("Fallback on Slot 5"); bind: "com.victronenergy.settings/Settings/SolarEdge/FallbackSlot5Enabled" }
        MbItemValue { description: qsTr("Slot 5 Target Timeout (s)"); item: slot5TargetTimeout }
        MbItemValue { description: qsTr("Slot 5 Target Fallback Power (%)"); item: slot5TargetFallback }

    }
}

#!/usr/bin/env python3
"""
Test script for firmware update and diagnostics functionality in OCPP server.
This script tests the new UpdateFirmware and GetDiagnostics commands.
"""

import asyncio
import websockets
import json
import time
from datetime import datetime, timedelta
import random

# OCPP 1.6 Message Types
CALL = 2
CALLRESULT = 3
CALLERROR = 4

class TestCharger:
    def __init__(self, charger_id):
        self.charger_id = charger_id
        self.websocket = None
        self.message_id = 1
        
    async def connect(self):
        """Connect to the OCPP server"""
        uri = f"ws://localhost:8000/ws/{self.charger_id}"
        print(f"Connecting to {uri}")
        self.websocket = await websockets.connect(uri, subprotocols=["ocpp1.6"])
        print(f"✅ Connected as {self.charger_id}")
        
    async def disconnect(self):
        """Disconnect from the server"""
        if self.websocket:
            await self.websocket.close()
            print(f"🔌 Disconnected {self.charger_id}")
            
    def get_next_message_id(self):
        """Get next message ID"""
        msg_id = str(self.message_id)
        self.message_id += 1
        return msg_id
        
    async def send_message(self, message_type, action, payload=None):
        """Send OCPP message"""
        if payload is None:
            payload = {}
            
        message = [message_type, self.get_next_message_id(), action, payload]
        message_json = json.dumps(message)
        
        print(f"📤 Sending: {message_json}")
        await self.websocket.send(message_json)
        
        return message[1]  # Return message ID
        
    async def receive_message(self):
        """Receive OCPP message"""
        message_json = await self.websocket.recv()
        message = json.loads(message_json)
        
        print(f"📥 Received: {message_json}")
        return message
        
    async def send_boot_notification(self):
        """Send BootNotification"""
        payload = {
            "chargePointModel": "TestCharger",
            "chargePointVendor": "TestVendor",
            "chargePointSerialNumber": f"TC{self.charger_id}",
            "firmwareVersion": "1.0.0"
        }
        
        await self.send_message(CALL, "BootNotification", payload)
        response = await self.receive_message()
        
        if response[0] == CALLRESULT:
            print("✅ BootNotification accepted")
            return True
        else:
            print("❌ BootNotification failed")
            return False
            
    async def handle_update_firmware(self, message):
        """Handle UpdateFirmware command from server"""
        message_id = message[1]
        payload = message[3]
        
        print(f"🔧 Received UpdateFirmware command:")
        print(f"   Location: {payload['location']}")
        print(f"   Retrieve Date: {payload['retrieveDate']}")
        if 'retries' in payload:
            print(f"   Retries: {payload['retries']}")
        if 'retryInterval' in payload:
            print(f"   Retry Interval: {payload['retryInterval']}")
            
        # Send response (UpdateFirmware has empty response)
        response = [CALLRESULT, message_id, {}]
        await self.websocket.send(json.dumps(response))
        print("✅ UpdateFirmware response sent")
        
        # Simulate firmware status notifications
        await asyncio.sleep(1)
        await self.send_firmware_status_notification("Downloading")
        await asyncio.sleep(2)
        await self.send_firmware_status_notification("Downloaded")
        await asyncio.sleep(1)
        await self.send_firmware_status_notification("Installing")
        await asyncio.sleep(2)
        await self.send_firmware_status_notification("Installed")
        
    async def handle_get_diagnostics(self, message):
        """Handle GetDiagnostics command from server"""
        message_id = message[1]
        payload = message[3]
        
        print(f"🏥 Received GetDiagnostics command:")
        print(f"   Location: {payload['location']}")
        if 'retries' in payload:
            print(f"   Retries: {payload['retries']}")
        if 'retryInterval' in payload:
            print(f"   Retry Interval: {payload['retryInterval']}")
        if 'startTime' in payload:
            print(f"   Start Time: {payload['startTime']}")
        if 'stopTime' in payload:
            print(f"   Stop Time: {payload['stopTime']}")
            
        # Send response with filename
        filename = f"diagnostics_{self.charger_id}_{int(time.time())}.log"
        response = [CALLRESULT, message_id, {"fileName": filename}]
        await self.websocket.send(json.dumps(response))
        print(f"✅ GetDiagnostics response sent with filename: {filename}")
        
        # Simulate diagnostics status notifications
        await asyncio.sleep(1)
        await self.send_diagnostics_status_notification("Uploading")
        await asyncio.sleep(3)
        await self.send_diagnostics_status_notification("Uploaded")
        
    async def handle_unlock_connector(self, message):
        """Handle UnlockConnector command from server"""
        message_id = message[1]
        payload = message[3]
        
        print(f"🔓 Received UnlockConnector command:")
        print(f"   Connector ID: {payload['connectorId']}")
        
        # Simulate unlock operation (you can change this to test different responses)
        possible_statuses = ["Unlocked", "UnlockFailed", "NotSupported"]
        # Mostly successful for testing
        weights = [0.8, 0.1, 0.1]
        status = random.choices(possible_statuses, weights=weights)[0]
        
        # Send response
        response = [CALLRESULT, message_id, {"status": status}]
        await self.websocket.send(json.dumps(response))
        print(f"✅ UnlockConnector response sent with status: {status}")
        
        if status == "Unlocked":
            print("🔓 Connector unlocked successfully!")
        elif status == "UnlockFailed":
            print("❌ Failed to unlock connector")
        else:
            print("⚠️ Unlock operation not supported")
        
    async def send_firmware_status_notification(self, status):
        """Send FirmwareStatusNotification"""
        payload = {"status": status}
        await self.send_message(CALL, "FirmwareStatusNotification", payload)
        response = await self.receive_message()
        print(f"📊 Firmware status: {status}")
        
    async def send_diagnostics_status_notification(self, status):
        """Send DiagnosticsStatusNotification"""
        payload = {"status": status}
        await self.send_message(CALL, "DiagnosticsStatusNotification", payload)
        response = await self.receive_message()
        print(f"📊 Diagnostics status: {status}")
        
    async def listen_for_commands(self):
        """Listen for commands from server"""
        print("👂 Listening for commands...")
        
        while True:
            try:
                message = await self.receive_message()
                
                # Handle incoming CALL messages (commands from server)
                if message[0] == CALL:
                    action = message[2]
                    
                    if action == "UpdateFirmware":
                        await self.handle_update_firmware(message)
                    elif action == "GetDiagnostics":
                        await self.handle_get_diagnostics(message)
                    elif action == "UnlockConnector":
                        await self.handle_unlock_connector(message)
                    else:
                        print(f"🤷 Unknown command: {action}")
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 Connection closed")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                break

async def test_firmware_diagnostics():
    """Test firmware update and diagnostics functionality"""
    charger = TestCharger("TEST_FW_DIAG")
    
    try:
        # Connect and boot
        await charger.connect()
        if not await charger.send_boot_notification():
            return
            
        # Listen for commands (in background)
        listen_task = asyncio.create_task(charger.listen_for_commands())
        
        print("\n" + "="*60)
        print("🚀 Test charger is ready!")
        print("   Charger ID: TEST_FW_DIAG")
        print("   Ready to receive UpdateFirmware, GetDiagnostics, and UnlockConnector commands")
        print("   Use the web UI to send these commands to this charger")
        print("="*60)
        print("\nTo test:")
        print("1. Open http://localhost:8000 in your browser")
        print("2. Select charger 'TEST_FW_DIAG'")
        print("3. Click 'Update Firmware' button")
        print("4. Click 'Get Diagnostics' button")
        print("5. Click 'Unlock Connector' button")
        print("6. Watch the console for status updates")
        print("\nPress Ctrl+C to stop the test charger")
        print("="*60 + "\n")
        
        # Wait indefinitely
        await listen_task
        
    except KeyboardInterrupt:
        print("\n👋 Test stopped by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        await charger.disconnect()

if __name__ == "__main__":
    print("🧪 OCPP Firmware Update, Diagnostics & Unlock Connector Test")
    print("============================================================")
    asyncio.run(test_firmware_diagnostics()) 
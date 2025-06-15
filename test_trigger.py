#!/usr/bin/env python3
"""
Test script for TriggerMessage functionality
"""
import requests
import json

def test_trigger_message():
    """Test TriggerMessage functionality"""
    base_url = "http://localhost:8000"
    charger_id = "kushagra01"
    
    print("🧪 Testing TriggerMessage Functionality")
    print("=" * 50)
    
    # Test 1: Heartbeat trigger
    print("\n1. Testing Heartbeat Trigger...")
    try:
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/trigger_message",
            headers={"Content-Type": "application/json"},
            json={"requested_message": "Heartbeat"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 2: StatusNotification trigger with connector ID
    print("\n2. Testing StatusNotification Trigger (Connector 1)...")
    try:
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/trigger_message",
            headers={"Content-Type": "application/json"},
            json={"requested_message": "StatusNotification", "connector_id": 1}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 3: BootNotification trigger
    print("\n3. Testing BootNotification Trigger...")
    try:
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/trigger_message",
            headers={"Content-Type": "application/json"},
            json={"requested_message": "BootNotification"}
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {json.dumps(result, indent=2)}")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    # Test 4: Invalid message type
    print("\n4. Testing Invalid Message Type...")
    try:
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/trigger_message",
            headers={"Content-Type": "application/json"},
            json={"requested_message": "InvalidMessage"}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Error (expected): {response.text}")
    except Exception as e:
        print(f"   Exception: {e}")
    
    print("\n" + "=" * 50)
    print("✅ TriggerMessage Test Complete!")

if __name__ == "__main__":
    test_trigger_message() 
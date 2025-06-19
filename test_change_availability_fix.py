#!/usr/bin/env python3
"""
Test script to verify that the ChangeAvailability fix works correctly.
This script will test the change availability functionality by sending requests to the server.
"""
import asyncio
import requests
import time
from datetime import datetime

SERVER_URL = "http://localhost:8000"
CHARGER_ID = "DEMO001"

def test_change_availability():
    """Test the ChangeAvailability functionality"""
    print("🔧 Testing ChangeAvailability Fix")
    print("=" * 50)
    
    # Test 1: Change to Inoperative
    print("1. Testing Change to Inoperative...")
    try:
        response = requests.post(
            f"{SERVER_URL}/api/chargers/{CHARGER_ID}/change_availability",
            json={
                "connector_id": 1,
                "availability_type": "Inoperative"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Wait a moment
    print("     Waiting 3 seconds...")
    time.sleep(3)
    
    # Test 2: Change to Operative
    print("2. Testing Change to Operative...")
    try:
        response = requests.post(
            f"{SERVER_URL}/api/chargers/{CHARGER_ID}/change_availability",
            json={
                "connector_id": 1,
                "availability_type": "Operative"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Success: {result}")
        else:
            print(f"   ❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 3: Check charger status
    print("3. Checking charger status...")
    try:
        response = requests.get(f"{SERVER_URL}/api/chargers", timeout=5)
        if response.status_code == 200:
            chargers = response.json()
            demo_charger = next((c for c in chargers if c['charge_point_id'] == CHARGER_ID), None)
            if demo_charger:
                print(f"   ✅ Charger Status: {demo_charger['status']}")
                print(f"   📡 Connected: {demo_charger['connected']}")
            else:
                print(f"   ⚠️  Charger {CHARGER_ID} not found")
        else:
            print(f"   ❌ Failed to get charger status: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting status: {e}")
    
    print("\n🎯 Test Summary:")
    print("   - If both tests show 'Success' and no timeout errors,")
    print("     then the ChangeAvailability fix is working correctly!")
    print("   - The charger should now respond immediately to ChangeAvailability requests")
    print("   - StatusNotification messages are sent asynchronously")

if __name__ == "__main__":
    print(f"🕐 Test started at: {datetime.now().strftime('%H:%M:%S')}")
    print("📋 Prerequisites:")
    print("   1. OCPP Server should be running on localhost:8000")
    print("   2. Demo charger (DEMO001) should be connected")
    print("   3. Server should be responding to API requests")
    print()
    
    # Small delay to ensure services are ready
    time.sleep(2)
    
    test_change_availability() 
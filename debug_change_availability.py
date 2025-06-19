#!/usr/bin/env python3
"""
Debug script to test ChangeAvailability function directly
"""

import asyncio
import logging
import requests
import json
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('DebugChangeAvailability')

async def test_change_availability():
    """Test the ChangeAvailability API directly."""
    
    # Test data
    charger_id = "DEMO001"
    base_url = "http://localhost:8000"
    
    print("🔧 Testing ChangeAvailability Function...")
    print(f"   Target charger: {charger_id}")
    print(f"   Server URL: {base_url}")
    
    # Test 1: Check if charger is connected
    try:
        response = requests.get(f"{base_url}/api/chargers")
        if response.status_code == 200:
            chargers_data = response.json()
            chargers = chargers_data.get('chargers', [])
            demo_charger = None
            for charger in chargers:
                if charger.get('id') == charger_id:
                    demo_charger = charger
                    break
            
            if demo_charger:
                print(f"✅ Found charger {charger_id}")
                print(f"   Connected: {demo_charger.get('connected', False)}")
                print(f"   Status: {demo_charger.get('status', 'Unknown')}")
            else:
                print(f"❌ Charger {charger_id} not found")
                return
        else:
            print(f"❌ Failed to get chargers list: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error checking chargers: {e}")
        return
    
    # Test 2: Try ChangeAvailability with Operative
    print("\n📋 Test 1: Setting connector to Operative")
    try:
        payload = {
            "connector_id": 1,
            "availability_type": "Operative"
        }
        
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/change_availability",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ChangeAvailability (Operative) successful")
            print(f"   Server response: {result}")
        else:
            print(f"❌ ChangeAvailability (Operative) failed")
            
    except Exception as e:
        print(f"❌ Error in ChangeAvailability (Operative): {e}")
    
    # Test 3: Try ChangeAvailability with Inoperative
    print("\n📋 Test 2: Setting connector to Inoperative")
    try:
        payload = {
            "connector_id": 1,
            "availability_type": "Inoperative"
        }
        
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{base_url}/api/send/{charger_id}/change_availability",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Response Status: {response.status_code}")
        print(f"   Response Headers: {dict(response.headers)}")
        print(f"   Response Body: {response.text}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ ChangeAvailability (Inoperative) successful")
            print(f"   Server response: {result}")
        else:
            print(f"❌ ChangeAvailability (Inoperative) failed")
            
    except Exception as e:
        print(f"❌ Error in ChangeAvailability (Inoperative): {e}")
    
    # Test 4: Check logs
    print("\n📋 Test 3: Checking charger logs")
    try:
        response = requests.get(f"{base_url}/api/logs/{charger_id}")
        if response.status_code == 200:
            logs = response.json()
            print(f"✅ Retrieved {len(logs)} log entries")
            
            # Show last 5 logs
            print("   Recent logs:")
            for log in logs[-5:]:
                timestamp = log.get('timestamp', 'Unknown')
                message = log.get('message', 'No message')
                print(f"     [{timestamp}] {message}")
        else:
            print(f"❌ Failed to get logs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting logs: {e}")

def main():
    """Main function."""
    print("🎯 OCPP ChangeAvailability Debug Test")
    print("=" * 50)
    
    # Run the async test
    asyncio.run(test_change_availability())
    
    print("\n" + "=" * 50)
    print("🏁 Debug test completed")

if __name__ == "__main__":
    main() 
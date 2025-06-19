#!/usr/bin/env python3
"""
Test script to verify UI improvements:
1. Connected chargers appear at the top
2. Reserve Now shows ID tags in dropdown
"""
import requests
import time
from datetime import datetime

SERVER_URL = "http://localhost:8000"

def test_charger_sorting():
    """Test that connected chargers appear at the top of the list"""
    print("🔧 Testing Charger List Sorting")
    print("=" * 40)
    
    try:
        response = requests.get(f"{SERVER_URL}/api/chargers", timeout=5)
        if response.status_code == 200:
            chargers = response.json()['chargers']
            
            print(f"📋 Found {len(chargers)} chargers:")
            
            connected_count = 0
            disconnected_count = 0
            found_connected_after_disconnected = False
            
            for i, charger in enumerate(chargers):
                status = "Connected" if charger['connected'] else "Disconnected"
                icon = "🟢" if charger['connected'] else "🔴"
                
                print(f"   {i+1}. {icon} {charger['id']} - {status}")
                
                if charger['connected']:
                    connected_count += 1
                    if disconnected_count > 0:
                        found_connected_after_disconnected = True
                else:
                    disconnected_count += 1
            
            print(f"\n📊 Summary:")
            print(f"   - Connected: {connected_count}")
            print(f"   - Disconnected: {disconnected_count}")
            
            if not found_connected_after_disconnected:
                print("   ✅ Connected chargers are properly sorted to the top!")
            else:
                print("   ⚠️  Connected chargers are NOT sorted to the top")
            
        else:
            print(f"   ❌ Failed to get chargers: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_id_tags_available():
    """Test that ID tags are available for the Reserve Now dropdown"""
    print("\n🏷️  Testing ID Tags for Reserve Now")
    print("=" * 40)
    
    try:
        response = requests.get(f"{SERVER_URL}/api/idtags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            id_tags = data.get('id_tags', [])
            
            print(f"📋 Found {len(id_tags)} ID tags:")
            
            accepted_count = 0
            for tag in id_tags:
                status_icon = "✅" if tag['status'] == 'Accepted' else \
                             "🚫" if tag['status'] == 'Blocked' else \
                             "⏰" if tag['status'] == 'Expired' else \
                             "❌" if tag['status'] == 'Invalid' else "❓"
                
                print(f"   {status_icon} {tag['id_tag']} ({tag['status']})")
                
                if tag['status'] == 'Accepted':
                    accepted_count += 1
            
            print(f"\n📊 Summary:")
            print(f"   - Total ID tags: {len(id_tags)}")
            print(f"   - Accepted (usable): {accepted_count}")
            
            if len(id_tags) > 0:
                print("   ✅ ID tags are available for Reserve Now dropdown!")
                if accepted_count > 0:
                    print("   ✅ Accepted ID tags available for reservation!")
                else:
                    print("   ⚠️  No accepted ID tags - reservations may not work")
            else:
                print("   ⚠️  No ID tags found - Reserve Now dropdown will be empty")
            
        else:
            print(f"   ❌ Failed to get ID tags: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error: {e}")

def test_server_connectivity():
    """Test basic server connectivity"""
    print("🌐 Testing Server Connectivity")
    print("=" * 40)
    
    try:
        # Test main page
        response = requests.get(SERVER_URL, timeout=5)
        if response.status_code == 200:
            print("   ✅ Server is running and responsive")
        else:
            print(f"   ⚠️  Server responded with status: {response.status_code}")
        
        # Test API endpoint
        response = requests.get(f"{SERVER_URL}/api/chargers", timeout=5)
        if response.status_code == 200:
            print("   ✅ API endpoints are working")
        else:
            print(f"   ⚠️  API responded with status: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Server connectivity error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print(f"🕐 UI Improvements Test started at: {datetime.now().strftime('%H:%M:%S')}")
    print("🎯 Testing the following improvements:")
    print("   1. Connected chargers appear at the top of the list")
    print("   2. Reserve Now dialog shows ID tags from database")
    print()
    
    # Test server connectivity first
    if not test_server_connectivity():
        print("\n❌ Server is not running. Please start the server first.")
        exit(1)
    
    print()
    
    # Test charger sorting
    test_charger_sorting()
    
    # Test ID tags availability
    test_id_tags_available()
    
    print("\n🎯 Test Summary:")
    print("   - Open http://localhost:8000 in your browser")
    print("   - Connected chargers should appear at the top with green wifi icons")
    print("   - Disconnected chargers should appear below with red wifi-off icons")
    print("   - Click 'Reserve Now' to see ID tags in the dropdown")
    print("   - Accepted ID tags should be highlighted in green and appear first")
    print("   - The dropdown should show status icons (✅, 🚫, ⏰, ❌) for each tag") 
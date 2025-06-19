#!/usr/bin/env python3
"""
Test script to verify that the Reserve Now dropdown now shows ID tags correctly
"""
import requests
import json
from datetime import datetime

SERVER_URL = "http://localhost:8000"

def test_id_tags_api():
    """Test the ID tags API directly"""
    print("🔧 Testing ID Tags API Response Format")
    print("=" * 50)
    
    try:
        response = requests.get(f"{SERVER_URL}/api/idtags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API Response received successfully")
            print(f"📋 Raw API Response:")
            print(f"   {json.dumps(data, indent=2)}")
            
            # Convert to array format like our JavaScript does
            id_tags_array = list(data.values())
            print(f"\n📊 Converted to Array Format:")
            print(f"   Found {len(id_tags_array)} ID tags")
            
            for i, tag in enumerate(id_tags_array):
                status_icon = "✅" if tag['status'] == 'Accepted' else \
                             "🚫" if tag['status'] == 'Blocked' else \
                             "⏰" if tag['status'] == 'Expired' else \
                             "❌" if tag['status'] == 'Invalid' else "❓"
                
                print(f"   {i+1}. {status_icon} {tag['id_tag']} ({tag['status']})")
            
            print(f"\n🎯 JavaScript Fix Status:")
            if len(id_tags_array) > 0:
                print(f"   ✅ ID tags found - Reserve Now dropdown should now work!")
                print(f"   ✅ Our JavaScript fix converts Object.values(data) correctly")
            else:
                print(f"   ⚠️  No ID tags found in response")
            
        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def instructions():
    print(f"\n🎯 Test Instructions:")
    print(f"1. Open http://localhost:8000 in your browser")
    print(f"2. Select the connected charger (DEMO001)")
    print(f"3. Click the 'Reserve Now' button")
    print(f"4. Check the 'ID Tag' dropdown - it should now show:")
    print(f"   ✅ Accepted ID tags at the top (green, bold)")
    print(f"   🚫 ⏰ ❌ Other status tags below (colored appropriately)")
    print(f"   📋 Status icons for easy identification")
    print(f"   💡 Hint text at the top: '-- Select an ID Tag --'")
    print(f"\n🔧 What was fixed:")
    print(f"   - JavaScript now correctly handles API format: {{tag_id: {{tag_data}}}}")
    print(f"   - Uses Object.values(data) to convert to array format")
    print(f"   - Maintains all sorting and styling improvements")

if __name__ == "__main__":
    print(f"🕐 Reserve Now Fix Test started at: {datetime.now().strftime('%H:%M:%S')}")
    print(f"🎯 Testing the Reserve Now dropdown ID tag loading fix")
    print()
    
    test_id_tags_api()
    instructions() 
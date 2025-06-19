#!/usr/bin/env python3
"""
Script to add sample ID tags for testing Reserve Now dropdown functionality
"""
import requests
import json

SERVER_URL = "http://localhost:8000"

def add_sample_id_tags():
    """Add sample ID tags to the database"""
    id_tags = [
        {'id_tag': '1234', 'status': 'Accepted'},
        {'id_tag': '5678', 'status': 'Accepted'},
        {'id_tag': 'TEST_TAG_01', 'status': 'Accepted'},
        {'id_tag': 'USER_CARD_A', 'status': 'Accepted'},
        {'id_tag': 'USER_CARD_B', 'status': 'Accepted'},
        {'id_tag': 'EXPIRED_TAG', 'status': 'Expired'},
        {'id_tag': 'BLOCKED_TAG', 'status': 'Blocked'},
        {'id_tag': 'INVALID_TAG', 'status': 'Invalid'}
    ]
    
    print("🏷️  Adding sample ID tags for Reserve Now testing...")
    print("=" * 50)
    
    success_count = 0
    for tag in id_tags:
        try:
            response = requests.post(f'{SERVER_URL}/api/idtags', 
                                   json=tag, 
                                   headers={'Content-Type': 'application/json'},
                                   timeout=10)
            
            if response.status_code == 201:
                status_icon = "✅" if tag['status'] == 'Accepted' else \
                             "🚫" if tag['status'] == 'Blocked' else \
                             "⏰" if tag['status'] == 'Expired' else \
                             "❌" if tag['status'] == 'Invalid' else "❓"
                
                print(f"   {status_icon} Added: {tag['id_tag']} ({tag['status']})")
                success_count += 1
            else:
                print(f"   ❌ Failed to add {tag['id_tag']}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error adding {tag['id_tag']}: {e}")
    
    print(f"\n📊 Summary: {success_count}/{len(id_tags)} ID tags added successfully")
    
    if success_count > 0:
        print(f"\n🎯 Test the Reserve Now dropdown:")
        print(f"   1. Open http://localhost:8000 in your browser")
        print(f"   2. Select a connected charger (DEMO001)")
        print(f"   3. Click 'Reserve Now' button")
        print(f"   4. Check the ID Tag dropdown - it should show:")
        print(f"      - Accepted tags at the top (in green)")
        print(f"      - Other status tags below (with appropriate colors)")
        print(f"      - Status icons (✅, 🚫, ⏰, ❌) for each tag")

if __name__ == "__main__":
    add_sample_id_tags() 
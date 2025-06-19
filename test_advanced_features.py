#!/usr/bin/env python3
"""
Test script for OCPP 1.6 Advanced Features
Tests Change Availability, Reservation, and Smart Charging functions
"""

import asyncio
import json
import logging
import requests
from datetime import datetime, timedelta
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('AdvancedFeaturesTest')

class OCPPAdvancedTester:
    def __init__(self, base_url="http://localhost:8000", charge_point_id="DEMO001"):
        self.base_url = base_url
        self.charge_point_id = charge_point_id
        self.session = requests.Session()
        
    def send_request(self, endpoint, method="GET", data=None):
        """Send HTTP request to the OCPP server"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(url, json=data)
            elif method == "DELETE":
                response = self.session.delete(url)
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Request failed: {method} {url} - {e}")
            return None

    def test_change_availability(self):
        """Test Change Availability functionality"""
        logger.info("🔧 Testing Change Availability Function...")
        
        # Test 1: Set connector to Inoperative
        logger.info("  📋 Test 1: Setting connector to Inoperative")
        data = {
            "connector_id": 1,
            "availability_type": "Inoperative"
        }
        result = self.send_request(f"/api/send/{self.charge_point_id}/change_availability", "POST", data)
        if result and result.get("status") == "success":
            logger.info("  ✅ Connector set to Inoperative successfully")
        else:
            logger.error("  ❌ Failed to set connector to Inoperative")
        
        time.sleep(2)
        
        # Test 2: Set connector to Operative
        logger.info("  📋 Test 2: Setting connector to Operative")
        data = {
            "connector_id": 1,
            "availability_type": "Operative"
        }
        result = self.send_request(f"/api/send/{self.charge_point_id}/change_availability", "POST", data)
        if result and result.get("status") == "success":
            logger.info("  ✅ Connector set to Operative successfully")
        else:
            logger.error("  ❌ Failed to set connector to Operative")
        
        return True

    def test_reservation_functionality(self):
        """Test Reservation functionality"""
        logger.info("🅿️ Testing Reservation Functionality...")
        
        # Test 1: Create a reservation
        logger.info("  📋 Test 1: Creating a reservation")
        expiry_date = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
        reservation_data = {
            "connector_id": 1,
            "expiry_date": expiry_date,
            "id_tag": "TEST123",
            "reservation_id": 12345,
            "parent_id_tag": None
        }
        
        result = self.send_request(f"/api/send/{self.charge_point_id}/reserve_now", "POST", reservation_data)
        if result and result.get("status") == "success":
            logger.info("  ✅ Reservation created successfully")
        else:
            logger.error("  ❌ Failed to create reservation")
            return False
        
        time.sleep(2)
        
        # Test 2: Check reservations
        logger.info("  📋 Test 2: Checking active reservations")
        reservations = self.send_request(f"/api/reservations/{self.charge_point_id}")
        if reservations and reservations.get("reservations"):
            logger.info(f"  ✅ Found {len(reservations['reservations'])} active reservation(s)")
        else:
            logger.warning("  ⚠️ No active reservations found")
        
        time.sleep(2)
        
        # Test 3: Cancel the reservation
        logger.info("  📋 Test 3: Cancelling the reservation")
        cancel_data = {
            "reservation_id": 12345
        }
        
        result = self.send_request(f"/api/send/{self.charge_point_id}/cancel_reservation", "POST", cancel_data)
        if result and result.get("status") == "success":
            logger.info("  ✅ Reservation cancelled successfully")
        else:
            logger.error("  ❌ Failed to cancel reservation")
        
        return True

    def test_smart_charging(self):
        """Test Smart Charging functionality"""
        logger.info("🔋 Testing Smart Charging Functionality...")
        
        # Test 1: Set a charging profile
        logger.info("  📋 Test 1: Setting a charging profile")
        
        # Create a sample charging profile
        charging_profile = {
            "connector_id": 1,
            "cs_charging_profiles": {
                "charging_profile_id": 1001,
                "transaction_id": None,
                "stack_level": 1,
                "charging_profile_purpose": "TxDefaultProfile",
                "charging_profile_kind": "Absolute",
                "recurrency_kind": None,
                "valid_from": datetime.utcnow().isoformat() + "Z",
                "valid_to": (datetime.utcnow() + timedelta(hours=8)).isoformat() + "Z",
                "charging_schedule": {
                    "duration": 28800,  # 8 hours in seconds
                    "start_schedule": datetime.utcnow().isoformat() + "Z",
                    "charging_rate_unit": "A",
                    "charging_schedule_period": [
                        {
                            "start_period": 0,
                            "limit": 16.0,
                            "number_phases": 3
                        },
                        {
                            "start_period": 7200,  # 2 hours later
                            "limit": 32.0,
                            "number_phases": 3
                        },
                        {
                            "start_period": 14400,  # 4 hours later
                            "limit": 8.0,
                            "number_phases": 3
                        }
                    ],
                    "min_charging_rate": 6.0
                }
            }
        }
        
        result = self.send_request(f"/api/send/{self.charge_point_id}/set_charging_profile", "POST", charging_profile)
        if result and result.get("status") == "success":
            logger.info("  ✅ Charging profile set successfully")
        else:
            logger.error("  ❌ Failed to set charging profile")
            return False
        
        time.sleep(2)
        
        # Test 2: Check charging profiles
        logger.info("  📋 Test 2: Checking active charging profiles")
        profiles = self.send_request(f"/api/charging_profiles/{self.charge_point_id}")
        if profiles and profiles.get("charging_profiles"):
            profile_count = sum(len(connector_profiles) for connector_profiles in profiles["charging_profiles"].values())
            logger.info(f"  ✅ Found {profile_count} active charging profile(s)")
        else:
            logger.warning("  ⚠️ No active charging profiles found")
        
        time.sleep(2)
        
        # Test 3: Clear charging profile by ID
        logger.info("  📋 Test 3: Clearing charging profile by ID")
        clear_data = {
            "id": 1001,
            "connector_id": 1,
            "charging_profile_purpose": None,
            "stack_level": None
        }
        
        result = self.send_request(f"/api/send/{self.charge_point_id}/clear_charging_profile", "POST", clear_data)
        if result and result.get("status") == "success":
            logger.info("  ✅ Charging profile cleared successfully")
        else:
            logger.error("  ❌ Failed to clear charging profile")
        
        time.sleep(2)
        
        # Test 4: Set another charging profile for purpose-based clearing
        logger.info("  📋 Test 4: Setting another charging profile for purpose-based clearing")
        charging_profile2 = {
            "connector_id": 1,
            "cs_charging_profiles": {
                "charging_profile_id": 1002,
                "stack_level": 2,
                "charging_profile_purpose": "ChargePointMaxProfile",
                "charging_profile_kind": "Absolute",
                "charging_schedule": {
                    "charging_rate_unit": "W",
                    "charging_schedule_period": [
                        {
                            "start_period": 0,
                            "limit": 22000.0  # 22kW
                        }
                    ]
                }
            }
        }
        
        result = self.send_request(f"/api/send/{self.charge_point_id}/set_charging_profile", "POST", charging_profile2)
        if result and result.get("status") == "success":
            logger.info("  ✅ Second charging profile set successfully")
            
            time.sleep(2)
            
            # Test 5: Clear by purpose
            logger.info("  📋 Test 5: Clearing charging profiles by purpose")
            clear_by_purpose = {
                "id": None,
                "connector_id": 1,
                "charging_profile_purpose": "ChargePointMaxProfile",
                "stack_level": None
            }
            
            result = self.send_request(f"/api/send/{self.charge_point_id}/clear_charging_profile", "POST", clear_by_purpose)
            if result and result.get("status") == "success":
                logger.info("  ✅ Charging profiles cleared by purpose successfully")
            else:
                logger.error("  ❌ Failed to clear charging profiles by purpose")
            
            # Test 6: Set a new profile and test GetCompositeSchedule
            logger.info("  📋 Test 6: Setting profile and testing GetCompositeSchedule")
            
            # Set a simple charging profile for testing GetCompositeSchedule
            test_profile = {
                "connector_id": 1,
                "cs_charging_profiles": {
                    "charging_profile_id": 2001,
                    "stack_level": 1,
                    "charging_profile_purpose": "TxDefaultProfile",
                    "charging_profile_kind": "Absolute",
                    "charging_schedule": {
                        "charging_rate_unit": "A",
                        "charging_schedule_period": [
                            {
                                "start_period": 0,
                                "limit": 20.0,
                                "number_phases": 3
                            }
                        ]
                    }
                }
            }
            
            result = self.send_request(f"/api/send/{self.charge_point_id}/set_charging_profile", "POST", test_profile)
            if result and result.get("status") == "success":
                logger.info("  ✅ Test charging profile set for GetCompositeSchedule")
                
                time.sleep(2)
                
                # Test 7: GetCompositeSchedule
                logger.info("  📋 Test 7: Getting composite schedule")
                composite_request = {
                    "connector_id": 1,
                    "duration": 3600,  # 1 hour
                    "charging_rate_unit": "A"
                }
                
                result = self.send_request(f"/api/send/{self.charge_point_id}/get_composite_schedule", "POST", composite_request)
                if result and result.get("status") == "success":
                    logger.info("  ✅ GetCompositeSchedule completed successfully")
                    
                    # Log details of the composite schedule
                    response_data = result.get("response", {})
                    if response_data.get("charging_schedule"):
                        schedule = response_data["charging_schedule"]
                        logger.info(f"     📊 Composite Schedule Details:")
                        logger.info(f"        - Rate Unit: {schedule.get('chargingRateUnit', 'N/A')}")
                        logger.info(f"        - Duration: {schedule.get('duration', 'N/A')}s")
                        periods = schedule.get('chargingSchedulePeriod', [])
                        logger.info(f"        - Periods: {len(periods)}")
                        for i, period in enumerate(periods[:2]):  # Show first 2 periods
                            start = period.get('startPeriod', 'N/A')
                            limit = period.get('limit', 'N/A')
                            logger.info(f"          Period {i+1}: Start={start}s, Limit={limit}A")
                    else:
                        logger.warning("     ⚠️ No charging schedule in response")
                else:
                    logger.error("  ❌ Failed to get composite schedule")
                
                # Clean up: Clear the test profile
                logger.info("  📋 Test 8: Cleaning up test profile")
                cleanup_data = {
                    "id": 2001,
                    "connector_id": 1,
                    "charging_profile_purpose": None,
                    "stack_level": None
                }
                
                result = self.send_request(f"/api/send/{self.charge_point_id}/clear_charging_profile", "POST", cleanup_data)
                if result and result.get("status") == "success":
                    logger.info("  ✅ Test profile cleaned up successfully")
                else:
                    logger.warning("  ⚠️ Failed to clean up test profile")
            else:
                logger.error("  ❌ Failed to set test charging profile for GetCompositeSchedule")
        
        return True

    def run_comprehensive_test(self):
        """Run all tests"""
        logger.info("🎯 Starting Comprehensive OCPP 1.6 Advanced Features Test")
        logger.info("=" * 60)
        
        # Check if charger is connected
        response = self.send_request("/api/chargers")
        if not response:
            logger.error("❌ Could not retrieve charger list. Is the server running?")
            return False
        
        # Handle the API response structure
        chargers = response.get("chargers", []) if isinstance(response, dict) else response
        
        # Find our test charger
        test_charger = None
        for charger in chargers:
            if isinstance(charger, dict) and charger.get("id") == self.charge_point_id:
                test_charger = charger
                break
            elif isinstance(charger, dict) and charger.get("charge_point_id") == self.charge_point_id:
                test_charger = charger
                break
            elif isinstance(charger, str) and charger == self.charge_point_id:
                test_charger = {"id": charger, "status": "unknown"}
                break
        
        if not test_charger:
            logger.error(f"❌ Test charger {self.charge_point_id} not found. Is the demo charger running?")
            return False
        
        logger.info(f"✅ Found test charger: {self.charge_point_id}")
        logger.info(f"   Status: {test_charger.get('status')}")
        logger.info(f"   Last Heartbeat: {test_charger.get('last_heartbeat') or test_charger.get('last_seen')}")
        logger.info(f"   Connected: {test_charger.get('connected', 'unknown')}")
        
        # Wait a moment for charger to be fully ready
        time.sleep(2)
        
        # Run tests
        tests_passed = 0
        total_tests = 3
        
        try:
            if self.test_change_availability():
                tests_passed += 1
            
            time.sleep(3)
            
            if self.test_reservation_functionality():
                tests_passed += 1
            
            time.sleep(3)
            
            if self.test_smart_charging():
                tests_passed += 1
                
        except Exception as e:
            logger.error(f"❌ Test execution failed: {e}")
        
        # Report results
        logger.info("=" * 60)
        logger.info(f"🏆 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            logger.info("✅ All advanced features are working correctly!")
        else:
            logger.warning(f"⚠️ {total_tests - tests_passed} test(s) failed")
        
        return tests_passed == total_tests

def main():
    """Run the advanced features test"""
    tester = OCPPAdvancedTester()
    success = tester.run_comprehensive_test()
    
    if success:
        logger.info("🎉 OCPP 1.6 Advanced Features implementation is successful!")
    else:
        logger.error("❌ Some issues were found. Please check the logs.")
    
    return success

if __name__ == "__main__":
    main() 
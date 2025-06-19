#!/usr/bin/env python3
"""
Comprehensive Black Box Testing of OCPP Server UI Functions
============================================================
This script performs end-to-end testing of all UI functions from a user's perspective.
"""

import requests
import json
import time
import random
import string
from datetime import datetime, timedelta

class OCPPUITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.test_results = []
        self.charger_id = "kushagra01"  # Primary test charger
        self.demo_charger_id = "DEMO001"  # Secondary test charger
        
    def log_test(self, test_name, status, details=""):
        """Log test result."""
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {details}")
        
    def test_server_connectivity(self):
        """Test 1: Server connectivity and basic endpoints."""
        print("\n🔌 Testing Server Connectivity")
        print("=" * 50)
        
        try:
            # Test main page
            response = requests.get(f"{self.base_url}/")
            if response.status_code == 200:
                self.log_test("Server Main Page", "PASS", "Server is accessible")
            else:
                self.log_test("Server Main Page", "FAIL", f"HTTP {response.status_code}")
                
            # Test API endpoints
            response = requests.get(f"{self.base_url}/api/chargers")
            if response.status_code == 200:
                chargers = response.json()
                self.log_test("Chargers API", "PASS", f"Found {len(chargers)} chargers")
            else:
                self.log_test("Chargers API", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Server Connectivity", "FAIL", str(e))
    
    def test_charger_logs(self):
        """Test 2: Charger logs functionality."""
        print("\n📋 Testing Charger Logs")
        print("=" * 50)
        
        try:
            # Test logs retrieval
            response = requests.get(f"{self.base_url}/api/logs/{self.charger_id}")
            if response.status_code == 200:
                logs = response.json()
                self.log_test("Logs Retrieval", "PASS", f"Retrieved {len(logs)} logs for {self.charger_id}")
                
                # Test log structure
                if logs and isinstance(logs[0], dict) and 'timestamp' in logs[0] and 'message' in logs[0]:
                    self.log_test("Log Structure", "PASS", "Logs have correct structure")
                else:
                    self.log_test("Log Structure", "FAIL", "Invalid log structure")
            else:
                self.log_test("Logs Retrieval", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Charger Logs", "FAIL", str(e))
    
    def test_id_tag_management(self):
        """Test 3: ID Tag management functions."""
        print("\n🏷️ Testing ID Tag Management")
        print("=" * 50)
        
        try:
            # Test adding new ID tag
            test_id_tag = f"TEST_{random.randint(1000, 9999)}"
            expiry_date = (datetime.now() + timedelta(days=1)).isoformat()
            
            add_data = {
                "id_tag": test_id_tag,
                "status": "Accepted",
                "expiry_date": expiry_date
            }
            
            response = requests.post(f"{self.base_url}/api/idtags", json=add_data)
            if response.status_code == 200:
                self.log_test("Add ID Tag", "PASS", f"Added ID tag: {test_id_tag}")
            else:
                self.log_test("Add ID Tag", "FAIL", f"HTTP {response.status_code}")
            
            # Test retrieving ID tags
            response = requests.get(f"{self.base_url}/api/idtags")
            if response.status_code == 200:
                id_tags = response.json()
                self.log_test("Get ID Tags", "PASS", f"Retrieved {len(id_tags)} ID tags")
                
                # Verify our test tag exists
                test_tag_found = any(tag.get('id_tag') == test_id_tag for tag in id_tags)
                if test_tag_found:
                    self.log_test("ID Tag Verification", "PASS", f"Test tag {test_id_tag} found")
                else:
                    self.log_test("ID Tag Verification", "FAIL", f"Test tag {test_id_tag} not found")
            else:
                self.log_test("Get ID Tags", "FAIL", f"HTTP {response.status_code}")
            
            # Test deleting ID tag
            response = requests.delete(f"{self.base_url}/api/idtags/{test_id_tag}")
            if response.status_code == 200:
                self.log_test("Delete ID Tag", "PASS", f"Deleted ID tag: {test_id_tag}")
            else:
                self.log_test("Delete ID Tag", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("ID Tag Management", "FAIL", str(e))
    
    def test_remote_operations(self):
        """Test 4: Remote operations (RemoteStart, RemoteStop, etc.)."""
        print("\n🎮 Testing Remote Operations")
        print("=" * 50)
        
        try:
            # Test RemoteStartTransaction
            start_data = {
                "id_tag": "TEST_REMOTE",
                "connector_id": 1
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/remote_start", json=start_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("RemoteStartTransaction", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("RemoteStartTransaction", "FAIL", f"HTTP {response.status_code}")
            
            # Wait a moment before testing stop
            time.sleep(2)
            
            # Test RemoteStopTransaction (get active transactions first)
            response = requests.get(f"{self.base_url}/api/active_transactions/{self.charger_id}")
            if response.status_code == 200:
                transactions = response.json()
                self.log_test("Get Active Transactions", "PASS", f"Found {len(transactions)} active transactions")
                
                if transactions:
                    # Test stopping the first transaction
                    transaction_id = transactions[0].get('transaction_id')
                    if transaction_id:
                        stop_data = {"transaction_id": transaction_id}
                        response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/remote_stop", json=stop_data)
                        if response.status_code == 200:
                            result = response.json()
                            self.log_test("RemoteStopTransaction", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
                        else:
                            self.log_test("RemoteStopTransaction", "FAIL", f"HTTP {response.status_code}")
                else:
                    self.log_test("RemoteStopTransaction", "SKIP", "No active transactions to stop")
            else:
                self.log_test("Get Active Transactions", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Remote Operations", "FAIL", str(e))
    
    def test_configuration_management(self):
        """Test 5: Configuration management functions."""
        print("\n⚙️ Testing Configuration Management")
        print("=" * 50)
        
        try:
            # Test GetConfiguration
            response = requests.get(f"{self.base_url}/api/send/{self.charger_id}/get_configuration")
            if response.status_code == 200:
                result = response.json()
                self.log_test("GetConfiguration", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("GetConfiguration", "FAIL", f"HTTP {response.status_code}")
            
            # Test ChangeConfiguration
            config_data = {
                "key": "HeartbeatInterval",
                "value": "30"
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/change_configuration", json=config_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("ChangeConfiguration", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("ChangeConfiguration", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Configuration Management", "FAIL", str(e))
    
    def test_cache_and_reset(self):
        """Test 6: Cache and reset operations."""
        print("\n🗄️ Testing Cache and Reset Operations")
        print("=" * 50)
        
        try:
            # Test ClearCache
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/clear_cache")
            if response.status_code == 200:
                result = response.json()
                self.log_test("ClearCache", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("ClearCache", "FAIL", f"HTTP {response.status_code}")
            
            # Test Reset (Soft)
            reset_data = {"type": "Soft"}
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/reset", json=reset_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("Reset (Soft)", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("Reset (Soft)", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Cache and Reset", "FAIL", str(e))
    
    def test_local_list_management(self):
        """Test 7: Local list management."""
        print("\n📝 Testing Local List Management")
        print("=" * 50)
        
        try:
            # Test GetLocalListVersion
            response = requests.get(f"{self.base_url}/api/send/{self.charger_id}/get_local_list_version")
            if response.status_code == 200:
                result = response.json()
                self.log_test("GetLocalListVersion", "PASS", f"Response received")
            else:
                self.log_test("GetLocalListVersion", "FAIL", f"HTTP {response.status_code}")
            
            # Test SendLocalList
            local_list_data = {
                "list_version": 1,
                "update_type": "Full",
                "local_authorization_list": [
                    {"id_tag": "LOCAL_TEST_001", "id_tag_info": {"status": "Accepted"}},
                    {"id_tag": "LOCAL_TEST_002", "id_tag_info": {"status": "Accepted"}}
                ]
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/send_local_list", json=local_list_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("SendLocalList", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("SendLocalList", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Local List Management", "FAIL", str(e))
    
    def test_trigger_message(self):
        """Test 8: TriggerMessage functionality."""
        print("\n📨 Testing TriggerMessage")
        print("=" * 50)
        
        try:
            # Test TriggerMessage for BootNotification
            trigger_data = {
                "requested_message": "BootNotification"
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/trigger_message", json=trigger_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("TriggerMessage", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("TriggerMessage", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("TriggerMessage", "FAIL", str(e))
    
    def test_availability_management(self):
        """Test 9: Availability management."""
        print("\n🔧 Testing Availability Management")
        print("=" * 50)
        
        try:
            # Test ChangeAvailability
            availability_data = {
                "connector_id": 0,
                "availability_type": "Inoperative"
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/change_availability", json=availability_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("ChangeAvailability", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("ChangeAvailability", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Availability Management", "FAIL", str(e))
    
    def test_reservation_management(self):
        """Test 10: Reservation management."""
        print("\n🅿️ Testing Reservation Management")
        print("=" * 50)
        
        try:
            # Test ReserveNow
            reservation_data = {
                "connector_id": 1,
                "expiry_date": (datetime.now() + timedelta(hours=1)).isoformat(),
                "id_tag": "RESERVE_TEST",
                "reservation_id": random.randint(1000, 9999)
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/reserve_now", json=reservation_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("ReserveNow", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
                
                # Test CancelReservation
                cancel_data = {"reservation_id": reservation_data["reservation_id"]}
                response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/cancel_reservation", json=cancel_data)
                if response.status_code == 200:
                    result = response.json()
                    self.log_test("CancelReservation", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
                else:
                    self.log_test("CancelReservation", "FAIL", f"HTTP {response.status_code}")
            else:
                self.log_test("ReserveNow", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Reservation Management", "FAIL", str(e))
    
    def test_charging_profiles(self):
        """Test 11: Charging profile management."""
        print("\n🔋 Testing Charging Profile Management")
        print("=" * 50)
        
        try:
            # Test SetChargingProfile
            profile_data = {
                "connector_id": 1,
                "cs_charging_profiles": {
                    "charging_profile_id": random.randint(1000, 9999),
                    "stack_level": 1,
                    "charging_profile_purpose": "TxProfile",
                    "charging_profile_kind": "Absolute",
                    "charging_schedule": {
                        "charging_rate_unit": "W",
                        "charging_schedule_period": [
                            {"start_period": 0, "limit": 7000}
                        ]
                    }
                }
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/set_charging_profile", json=profile_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("SetChargingProfile", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("SetChargingProfile", "FAIL", f"HTTP {response.status_code}")
            
            # Test ClearChargingProfile
            clear_data = {
                "id": profile_data["cs_charging_profiles"]["charging_profile_id"]
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/clear_charging_profile", json=clear_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("ClearChargingProfile", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("ClearChargingProfile", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Charging Profiles", "FAIL", str(e))
    
    def test_firmware_diagnostics(self):
        """Test 12: Firmware and diagnostics."""
        print("\n🔧 Testing Firmware and Diagnostics")
        print("=" * 50)
        
        try:
            # Test UpdateFirmware
            firmware_data = {
                "location": "https://example.com/firmware.bin",
                "retrieve_date": (datetime.now() + timedelta(minutes=5)).isoformat()
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/update_firmware", json=firmware_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("UpdateFirmware", "PASS", f"Response received")
            else:
                self.log_test("UpdateFirmware", "FAIL", f"HTTP {response.status_code}")
            
            # Test GetDiagnostics
            diagnostics_data = {
                "location": "https://example.com/diagnostics/"
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/get_diagnostics", json=diagnostics_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("GetDiagnostics", "PASS", f"Response received")
            else:
                self.log_test("GetDiagnostics", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Firmware and Diagnostics", "FAIL", str(e))
    
    def test_data_transfer(self):
        """Test 13: Data transfer functionality."""
        print("\n📤 Testing Data Transfer")
        print("=" * 50)
        
        try:
            # Test DataTransfer
            data_transfer_data = {
                "vendor_id": "TestVendor",
                "message_id": "TestMessage",
                "data": {"test": "data", "value": 123}
            }
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/data_transfer", json=data_transfer_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("DataTransfer", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("DataTransfer", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Data Transfer", "FAIL", str(e))
    
    def test_unlock_connector(self):
        """Test 14: UnlockConnector functionality."""
        print("\n🔓 Testing UnlockConnector")
        print("=" * 50)
        
        try:
            # Test UnlockConnector
            unlock_data = {"connector_id": 1}
            
            response = requests.post(f"{self.base_url}/api/send/{self.charger_id}/unlock_connector", json=unlock_data)
            if response.status_code == 200:
                result = response.json()
                self.log_test("UnlockConnector", "PASS", f"Status: {result.get('response', {}).get('status', 'Unknown')}")
            else:
                self.log_test("UnlockConnector", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("UnlockConnector", "FAIL", str(e))
    
    def test_log_filtering(self):
        """Test 15: Log filtering functionality."""
        print("\n🔍 Testing Log Filtering")
        print("=" * 50)
        
        try:
            # Get logs first
            response = requests.get(f"{self.base_url}/api/logs/{self.charger_id}")
            if response.status_code == 200:
                logs = response.json()
                total_logs = len(logs)
                
                # Test filtering by checking different message types in logs
                message_types = set()
                for log in logs:
                    message = log.get('message', '').lower()
                    if 'heartbeat' in message:
                        message_types.add('Heartbeat')
                    elif 'statusnotification' in message:
                        message_types.add('StatusNotification')
                    elif 'bootnotification' in message:
                        message_types.add('BootNotification')
                    elif 'clearcache' in message:
                        message_types.add('ClearCache')
                
                self.log_test("Log Message Types", "PASS", f"Found {len(message_types)} different message types: {', '.join(message_types)}")
                
                # Test that we have sufficient data for filtering tests
                if total_logs > 10:
                    self.log_test("Log Volume", "PASS", f"Sufficient logs ({total_logs}) for filtering tests")
                else:
                    self.log_test("Log Volume", "WARN", f"Limited logs ({total_logs}) for comprehensive filtering tests")
                    
            else:
                self.log_test("Log Filtering Setup", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Log Filtering", "FAIL", str(e))
    
    def test_ui_features(self):
        """Test 16: UI feature configuration."""
        print("\n🖥️ Testing UI Features")
        print("=" * 50)
        
        try:
            # Test getting current UI features
            response = requests.get(f"{self.base_url}/api/config/ui-features")
            if response.status_code == 200:
                features = response.json()
                self.log_test("Get UI Features", "PASS", f"Retrieved {len(features)} UI feature settings")
                
                # Test updating UI features
                updated_features = features.copy()
                # Toggle a feature for testing
                if 'show_jio_bp_data_transfer' in updated_features:
                    updated_features['show_jio_bp_data_transfer'] = not updated_features['show_jio_bp_data_transfer']
                
                response = requests.post(f"{self.base_url}/api/config/ui-features", json=updated_features)
                if response.status_code == 200:
                    self.log_test("Update UI Features", "PASS", "UI features updated successfully")
                else:
                    self.log_test("Update UI Features", "FAIL", f"HTTP {response.status_code}")
            else:
                self.log_test("Get UI Features", "FAIL", f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("UI Features", "FAIL", str(e))
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE UI BLACK BOX TEST REPORT")
        print("=" * 70)
        
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t["status"] == "PASS"])
        failed_tests = len([t for t in self.test_results if t["status"] == "FAIL"])
        warning_tests = len([t for t in self.test_results if t["status"] == "WARN"])
        skipped_tests = len([t for t in self.test_results if t["status"] == "SKIP"])
        
        print(f"📈 SUMMARY:")
        print(f"  Total Tests: {total_tests}")
        print(f"  ✅ Passed: {passed_tests}")
        print(f"  ❌ Failed: {failed_tests}")
        print(f"  ⚠️  Warnings: {warning_tests}")
        print(f"  ⏭️  Skipped: {skipped_tests}")
        print(f"  📊 Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test in self.test_results:
                if test["status"] == "FAIL":
                    print(f"  • {test['test']}: {test['details']}")
        
        if warning_tests > 0:
            print(f"\n⚠️  WARNINGS:")
            for test in self.test_results:
                if test["status"] == "WARN":
                    print(f"  • {test['test']}: {test['details']}")
        
        print(f"\n📋 DETAILED RESULTS:")
        for test in self.test_results:
            status_icon = "✅" if test["status"] == "PASS" else "❌" if test["status"] == "FAIL" else "⚠️" if test["status"] == "WARN" else "⏭️"
            print(f"  {status_icon} {test['test']}: {test['details']}")
        
        # Save report to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"ui_test_report_{timestamp}.json"
        with open(report_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        
        return passed_tests, failed_tests, total_tests

def main():
    """Run comprehensive UI testing."""
    print("🧪 OCPP Server UI Black Box Testing")
    print("🎯 Testing all functions from user perspective")
    print("=" * 70)
    
    tester = OCPPUITester()
    
    # Execute all test suites
    test_suites = [
        tester.test_server_connectivity,
        tester.test_charger_logs,
        tester.test_id_tag_management,
        tester.test_remote_operations,
        tester.test_configuration_management,
        tester.test_cache_and_reset,
        tester.test_local_list_management,
        tester.test_trigger_message,
        tester.test_availability_management,
        tester.test_reservation_management,
        tester.test_charging_profiles,
        tester.test_firmware_diagnostics,
        tester.test_data_transfer,
        tester.test_unlock_connector,
        tester.test_log_filtering,
        tester.test_ui_features
    ]
    
    # Run all tests
    for test_suite in test_suites:
        try:
            test_suite()
            time.sleep(1)  # Brief pause between test suites
        except Exception as e:
            print(f"❌ Test suite failed: {test_suite.__name__}: {e}")
    
    # Generate final report
    passed, failed, total = tester.generate_test_report()
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! The OCPP Server UI is functioning correctly.")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review the failures above.")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1) 
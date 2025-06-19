#!/usr/bin/env python3
"""
Production-Ready OCPP Server Test Suite
=========================================
Comprehensive test suite for validating OCPP Server production readiness.
"""

import requests
import json
import time
import sys
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionOCPPTest:
    def __init__(self, base_url="http://localhost:8000", charger_id="kushagra01"):
        self.base_url = base_url
        self.charger_id = charger_id
        self.test_results = []
        self.start_time = datetime.now()
        self.passed = 0
        self.failed = 0
        
    def log_result(self, test_name, success, details=""):
        status = "PASS" if success else "FAIL"
        if success:
            self.passed += 1
        else:
            self.failed += 1
        logger.info(f"[{status}] {test_name}: {details}")
        self.test_results.append({
            'test': test_name,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
        
    def make_request(self, method, endpoint, data=None):
        url = f"{self.base_url}{endpoint}"
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=data, timeout=30)
            elif method == "DELETE":
                response = requests.delete(url, timeout=30)
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text[:500]}")
            
            if response.status_code in [200, 201]:
                try:
                    json_response = response.json()
                    return True, json_response
                except:
                    return True, response.text
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
        except Exception as e:
            logger.error(f"Request exception: {e}")
            return False, str(e)
    
    def test_server_connectivity(self):
        logger.info("Testing server connectivity...")
        success, response = self.make_request("GET", "/api/chargers")
        if success:
            # Handle both list format and dict format
            chargers = response if isinstance(response, list) else response.get('chargers', [])
            charger_count = len(chargers)
            self.log_result("Server Connectivity", True, f"Server responsive, {charger_count} chargers found")
            return True
        else:
            self.log_result("Server Connectivity", False, f"Server unreachable: {response}")
            return False
    
    def test_charger_status(self):
        logger.info(f"Testing charger status for {self.charger_id}...")
        success, response = self.make_request("GET", "/api/chargers")
        if success:
            # Handle both list format and dict format
            chargers = response if isinstance(response, list) else response.get('chargers', [])
            for charger in chargers:
                if charger.get('id') == self.charger_id:
                    status = charger.get('status', 'Unknown')
                    connected = charger.get('websocket_connected', False)
                    self.log_result("Charger Status", True, f"Status: {status}, Connected: {connected}")
                    return True
            self.log_result("Charger Status", False, f"Charger {self.charger_id} not found")
            return False
        else:
            self.log_result("Charger Status", False, f"Failed to get charger list: {response}")
            return False
    
    def test_charger_logs(self):
        logger.info("Testing charger logs retrieval...")
        success, response = self.make_request("GET", f"/api/logs/{self.charger_id}")
        if success and isinstance(response, list):
            log_count = len(response)
            self.log_result("Charger Logs", True, f"Retrieved {log_count} logs")
            return True
        else:
            self.log_result("Charger Logs", False, f"Failed to retrieve logs: {response}")
            return False
    
    def test_id_tag_management(self):
        logger.info("Testing ID tag management...")
        test_tag = f"TEST_{int(time.time())}"
        
        # Create tag
        success, response = self.make_request("POST", "/api/idtags", {
            "id_tag": test_tag,
            "status": "Accepted"
        })
        if not success:
            self.log_result("ID Tag Creation", False, f"Failed to create tag: {response}")
            return False
        
        # Get tags
        success, response = self.make_request("GET", "/api/idtags")
        if not success or not isinstance(response, dict) or test_tag not in response:
            self.log_result("ID Tag Retrieval", False, "Tag not found after creation")
            return False
        
        # Delete tag
        success, response = self.make_request("DELETE", f"/api/idtags/{test_tag}")
        if not success:
            self.log_result("ID Tag Deletion", False, f"Failed to delete tag: {response}")
            return False
        
        self.log_result("ID Tag Management", True, "CRUD operations successful")
        return True
    
    def test_ocpp_commands(self):
        logger.info("Testing OCPP commands...")
        
        # Test TriggerMessage
        success, response = self.make_request("POST", f"/api/send/{self.charger_id}/trigger_message", {
            "requested_message": "StatusNotification",
            "connector_id": 1
        })
        if success:
            if isinstance(response, dict):
                status = response.get('response', {}).get('status', 'Unknown')
                self.log_result("TriggerMessage", True, f"Status: {status}")
            else:
                self.log_result("TriggerMessage", True, f"Response: {response}")
        else:
            self.log_result("TriggerMessage", False, f"Failed: {response}")
            return False
        
        # Test GetConfiguration
        success, response = self.make_request("GET", f"/api/send/{self.charger_id}/get_configuration")
        if success:
            if isinstance(response, dict):
                config_count = len(response.get('response', {}).get('configuration_key', []))
                self.log_result("GetConfiguration", True, f"Retrieved {config_count} config items")
            else:
                self.log_result("GetConfiguration", True, f"Response: {response}")
        else:
            self.log_result("GetConfiguration", False, f"Failed: {response}")
            return False
        
        # Test ClearCache
        success, response = self.make_request("POST", f"/api/send/{self.charger_id}/clear_cache")
        if success:
            if isinstance(response, dict):
                status = response.get('response', {}).get('status', 'Unknown')
                self.log_result("ClearCache", True, f"Status: {status}")
            else:
                self.log_result("ClearCache", True, f"Response: {response}")
        else:
            self.log_result("ClearCache", False, f"Failed: {response}")
            return False
        
        return True
    
    def test_remote_start(self):
        logger.info("Testing RemoteStartTransaction...")
        try:
            success, response = self.make_request("POST", f"/api/send/{self.charger_id}/remote_start", {
                "id_tag": "VALID_TAG_001",
                "connector_id": 1
            })
            logger.debug(f"RemoteStart - Success: {success}, Response type: {type(response)}, Response: {response}")
            
            if success:
                if isinstance(response, dict):
                    status = response.get('response', {}).get('status', 'Unknown')
                    self.log_result("RemoteStartTransaction", True, f"Status: {status}")
                    return status == "Accepted"
                else:
                    self.log_result("RemoteStartTransaction", True, f"Response: {response}")
                    return True
            else:
                self.log_result("RemoteStartTransaction", False, f"Failed: {response}")
                return False
        except Exception as e:
            logger.error(f"Exception in test_remote_start: {e}")
            self.log_result("RemoteStartTransaction", False, f"Exception: {e}")
            return False
    
    def test_active_transaction(self):
        logger.info("Testing active transaction detection...")
        success, response = self.make_request("GET", f"/api/active_transactions/{self.charger_id}")
        if success and isinstance(response, dict):
            active_txn = response.get('active_transaction')
            if active_txn:
                txn_id = active_txn.get('transaction_id')
                self.log_result("Active Transaction", True, f"Transaction ID: {txn_id}")
                return txn_id
            else:
                self.log_result("Active Transaction", False, "No active transaction found")
                return None
        else:
            self.log_result("Active Transaction", False, f"Failed to check: {response}")
            return None
    
    def test_remote_stop(self, transaction_id):
        if not transaction_id:
            self.log_result("RemoteStopTransaction", False, "No transaction ID available")
            return False
        
        logger.info(f"Testing RemoteStopTransaction for txn {transaction_id}...")
        success, response = self.make_request("POST", f"/api/send/{self.charger_id}/remote_stop", {
            "transaction_id": transaction_id
        })
        if success:
            if isinstance(response, dict):
                status = response.get('response', {}).get('status', 'Unknown')
                self.log_result("RemoteStopTransaction", True, f"Status: {status}")
            else:
                self.log_result("RemoteStopTransaction", True, f"Response: {response}")
            return True
        else:
            self.log_result("RemoteStopTransaction", False, f"Failed: {response}")
            return False
    
    def test_ui_features(self):
        logger.info("Testing UI features...")
        success, response = self.make_request("GET", "/api/config/ui-features")
        if success:
            feature_count = len(response) if isinstance(response, dict) else 0
            self.log_result("UI Features", True, f"Retrieved {feature_count} features")
            return True
        else:
            self.log_result("UI Features", False, f"Failed: {response}")
            return False
    
    def run_all_tests(self):
        logger.info("=" * 60)
        logger.info("🚀 STARTING PRODUCTION OCPP SERVER TEST SUITE")
        logger.info("=" * 60)
        
        # Core infrastructure tests
        if not self.test_server_connectivity():
            logger.error("❌ Critical: Server connectivity failed - aborting tests")
            return self.generate_report()
        
        self.test_charger_status()
        self.test_charger_logs()
        self.test_id_tag_management()
        self.test_ocpp_commands()
        self.test_ui_features()
        
        # Transaction lifecycle tests
        if self.test_remote_start():
            # Wait a bit for transaction to start
            time.sleep(5)
            transaction_id = self.test_active_transaction()
            if transaction_id:
                # Wait for meter values
                logger.info("Waiting 15 seconds for meter values...")
                time.sleep(15)
                self.test_remote_stop(transaction_id)
        
        return self.generate_report()
    
    def generate_report(self):
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 PRODUCTION TEST RESULTS")
        logger.info("=" * 60)
        logger.info(f"Total Tests: {total_tests}")
        logger.info(f"Passed: {self.passed}")
        logger.info(f"Failed: {self.failed}")
        logger.info(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 95:
            logger.info("🟢 STATUS: PRODUCTION READY!")
        elif success_rate >= 80:
            logger.info("🟡 STATUS: MOSTLY READY - Minor issues to address")
        else:
            logger.info("🔴 STATUS: NOT PRODUCTION READY - Critical issues found")
        
        # Save detailed report
        report = {
            "test_session": {
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "charger_id": self.charger_id,
                "server_url": self.base_url
            },
            "summary": {
                "total_tests": total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "success_rate": success_rate
            },
            "detailed_results": self.test_results
        }
        
        report_file = f"production_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"📄 Detailed report saved: {report_file}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
        
        return success_rate >= 95

def main():
    print("🚀 Production-Ready OCPP Server Test Suite v3.0.0")
    print("=" * 60)
    
    test_suite = ProductionOCPPTest()
    
    try:
        production_ready = test_suite.run_all_tests()
        return 0 if production_ready else 1
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
        return 2
    except Exception as e:
        logger.error(f"Critical error: {e}")
        return 3

if __name__ == "__main__":
    sys.exit(main()) 
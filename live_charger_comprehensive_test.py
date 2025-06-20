#!/usr/bin/env python3
"""
Comprehensive Live Charger Testing Script
==========================================
Permanent test script for OCPP Server with live charger connected.
Handles RemoteStop timing by monitoring meter values and transaction status.

Key Features:
- Smart transaction monitoring
- Meter values detection before RemoteStop
- Real-world timing scenarios
- Comprehensive OCPP command testing
"""

import requests
import json
import time
import random
import threading
from datetime import datetime, timedelta

class ComprehensiveLiveChargerTester:
    def __init__(self, base_url="http://localhost:8000", charger_id="kushagra01"):
        self.base_url = base_url
        self.charger_id = charger_id
        self.test_results = []
        self.test_id_tag = f"TEST_{random.randint(10000, 99999)}"
        self.transaction_started = False
        self.active_transaction_id = None
        self.meter_values_received = False
        self.stop_monitoring = False
        
    def log_test(self, test_name, success, details="", warning=False):
        """Log test result."""
        if warning:
            status = "⚠️  WARN"
        else:
            status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    📝 {details}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'details': details,
            'warning': warning,
            'timestamp': datetime.now().isoformat()
        })
    
    def monitor_transaction_status(self, timeout_seconds=30):
        """Monitor transaction status and meter values in background."""
        start_time = time.time()
        
        while not self.stop_monitoring and (time.time() - start_time) < timeout_seconds:
            try:
                # Check for active transaction
                response = requests.get(f"{self.base_url}/api/active_transactions/{self.charger_id}", timeout=5)
                if response.status_code == 200:
                    transaction = response.json()
                    if transaction and transaction.get('transaction_id'):
                        self.active_transaction_id = transaction['transaction_id']
                        print(f"    🔄 Monitoring transaction {self.active_transaction_id}")
                        
                        # Check recent logs for meter values
                        log_response = requests.get(f"{self.base_url}/api/logs/{self.charger_id}", timeout=5)
                        if log_response.status_code == 200:
                            logs = log_response.json()
                            # Check last few logs for meter values
                            recent_logs = logs[-10:] if len(logs) >= 10 else logs
                            for log in recent_logs:
                                if 'MeterValues' in log.get('message', ''):
                                    self.meter_values_received = True
                                    print(f"    ⚡ Meter values detected!")
                                    return True
                    else:
                        # Transaction completed naturally
                        if self.transaction_started:
                            print(f"    🏁 Transaction completed naturally")
                            return False
                
                time.sleep(1)
                
            except Exception as e:
                print(f"    ⚠️  Monitor error: {str(e)[:50]}")
                time.sleep(1)
        
        return False
    
    def test_basic_connectivity(self):
        """Test basic server connectivity."""
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            success = response.status_code == 200
            self.log_test("Basic Server Connectivity", success, 
                         f"Status: {response.status_code}")
            return success
        except Exception as e:
            self.log_test("Basic Server Connectivity", False, str(e))
            return False
    
    def test_charger_status(self):
        """Test charger status retrieval."""
        try:
            response = requests.get(f"{self.base_url}/api/chargers", timeout=10)
            if response.status_code == 200:
                data = response.json()
                chargers = data.get('chargers', []) if isinstance(data, dict) else data
                charger_found = any(c['id'] == self.charger_id for c in chargers)
                if charger_found:
                    charger = next(c for c in chargers if c['id'] == self.charger_id)
                    connected = charger.get('connected', False)
                    websocket_connected = charger.get('websocket_connected', False)
                    status = charger.get('status', 'Unknown')
                    
                    self.log_test("Charger Status Check", connected, 
                                 f"Connected: {connected}, WebSocket: {websocket_connected}, Status: {status}")
                    return connected
                else:
                    self.log_test("Charger Status Check", False, 
                                 f"Charger {self.charger_id} not found")
                    return False
            else:
                self.log_test("Charger Status Check", False, 
                             f"Status: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Charger Status Check", False, str(e))
            return False
    
    def test_remote_start_with_monitoring(self):
        """Test RemoteStartTransaction with intelligent monitoring."""
        print("\n🚀 Testing RemoteStart with Transaction Monitoring")
        
        # Start the transaction
        data = {"id_tag": self.test_id_tag, "connector_id": 1}
        try:
            url = f"{self.base_url}/api/send/{self.charger_id}/remote_start"
            response = requests.post(url, json=data, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('status') == 'success'
                
                if success:
                    self.transaction_started = True
                    self.log_test("OCPP: RemoteStartTransaction", True, 
                                 "Transaction start command accepted")
                    
                    # Start monitoring in background
                    print("    🔍 Starting transaction monitoring...")
                    self.stop_monitoring = False
                    
                    # Start monitoring thread
                    monitor_thread = threading.Thread(
                        target=self.monitor_transaction_status,
                        args=(45,)  # 45 second timeout
                    )
                    monitor_thread.daemon = True
                    monitor_thread.start()
                    
                    # Wait for monitoring to complete
                    monitor_thread.join(timeout=50)
                    self.stop_monitoring = True
                    
                    return True
                else:
                    self.log_test("OCPP: RemoteStartTransaction", False, 
                                 f"Start rejected: {result.get('response', {})}")
                    return False
            else:
                self.log_test("OCPP: RemoteStartTransaction", False, 
                             f"HTTP {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("OCPP: RemoteStartTransaction", False, str(e))
            return False
    
    def test_remote_stop_after_meter_values(self):
        """Test RemoteStopTransaction after detecting meter values."""
        print("\n🛑 Testing RemoteStop After Meter Values Detection")
        
        if not self.transaction_started:
            self.log_test("OCPP: RemoteStopTransaction", False, 
                         "No transaction was started", warning=True)
            return False
        
        if not self.active_transaction_id:
            self.log_test("OCPP: RemoteStopTransaction", False, 
                         "No active transaction ID found", warning=True)
            return False
        
        if not self.meter_values_received:
            self.log_test("OCPP: RemoteStopTransaction", False, 
                         "No meter values detected - transaction may have completed", warning=True)
            return False
        
        # Now try to stop the transaction
        try:
            data = {"transaction_id": self.active_transaction_id}
            url = f"{self.base_url}/api/send/{self.charger_id}/remote_stop"
            response = requests.post(url, json=data, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('status') == 'success'
                
                if success:
                    response_data = result.get('response', {})
                    status = response_data.get('status', 'Unknown')
                    self.log_test("OCPP: RemoteStopTransaction", True, 
                                 f"Stop command sent, Status: {status}")
                    return True
                else:
                    self.log_test("OCPP: RemoteStopTransaction", False, 
                                 f"Stop rejected: {response_data}")
                    return False
            else:
                self.log_test("OCPP: RemoteStopTransaction", False, 
                             f"HTTP {response.status_code}: {response.text[:100]}")
                return False
                
        except Exception as e:
            self.log_test("OCPP: RemoteStopTransaction", False, str(e))
            return False
    
    def run_comprehensive_test(self):
        """Run all tests with intelligent transaction monitoring."""
        print("🧪 Comprehensive Live Charger Testing with Smart Transaction Monitoring")
        print("=" * 80)
        print(f"🎯 Target: {self.charger_id} at {self.base_url}")
        print(f"🏷️  Test ID Tag: {self.test_id_tag}")
        print(f"⏰ Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Basic tests
        print("📊 Phase 1: Basic Tests")
        self.test_basic_connectivity()
        charger_connected = self.test_charger_status()
        print()
        
        if charger_connected:
            # Transaction Flow with Smart Monitoring
            print("📊 Phase 2: Smart Transaction Flow Tests")
            print("🔬 This test will:")
            print("   1. Start a transaction with RemoteStart")
            print("   2. Monitor for meter values and transaction status")
            print("   3. Send RemoteStop only after meter values are detected")
            print("   4. Handle timing issues intelligently")
            print()
            
            # Start transaction with monitoring
            start_success = self.test_remote_start_with_monitoring()
            
            if start_success:
                # Test RemoteStop with intelligent timing
                self.test_remote_stop_after_meter_values()
            else:
                print("⚠️  Skipping RemoteStop test - RemoteStart failed")
        else:
            print("⚠️  Skipping transaction tests - charger not connected")
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r['success'])
        warning_tests = sum(1 for r in self.test_results if r.get('warning', False))
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print("\n📈 FINAL RESULTS")
        print("=" * 50)
        print(f"✅ Passed: {passed_tests}/{total_tests}")
        if warning_tests > 0:
            print(f"⚠️  Warnings: {warning_tests} (timing scenarios)")
        print(f"📊 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("🌟 EXCELLENT - Live charger working exceptionally well!")
        elif success_rate >= 80:
            print("✅ VERY GOOD - Live charger working well!")
        elif success_rate >= 70:
            print("👍 GOOD - Most functionality working")
        else:
            print("⚠️  NEEDS ATTENTION - Multiple issues detected")
        
        return success_rate

def main():
    print("🚀 Starting Comprehensive Live Charger Test...")
    print("⏳ Ensure your live charger is connected as 'kushagra01'")
    print("🧠 This test uses smart monitoring for transaction timing")
    print()
    
    tester = ComprehensiveLiveChargerTester()
    success_rate = tester.run_comprehensive_test()
    
    print()
    print("🎯 TESTING COMPLETE!")
    print(f"📊 Final Success Rate: {success_rate:.1f}%")
    print()
    print("📚 Key Features Tested:")
    print("   • Smart transaction monitoring")
    print("   • Meter values detection")
    print("   • Intelligent RemoteStop timing")
    print("   • Real-world scenario handling")

if __name__ == "__main__":
    main()

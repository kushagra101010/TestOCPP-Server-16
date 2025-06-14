import asyncio
import logging
import websockets
from datetime import datetime
import random
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import RegistrationStatus, ChargePointStatus, AuthorizationStatus, Action, RemoteStartStopStatus
from ocpp.routing import on

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("ocpp").setLevel(logging.DEBUG)
logger = logging.getLogger('DemoCharger')

class ChargePoint(cp):
    def __init__(self, id, connection):
        super().__init__(id, connection)
        self.current_transaction_id = None
        self.meter_start_value = 0
        self.meter_current_value = 0
        self.charging = False
        self.authorized_tags = set()  # Store authorized ID tags
        self._authorization_lock = asyncio.Lock()  # Prevent concurrent authorizations

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charge_point_model="DemoModel",
            charge_point_vendor="DemoVendor"
        )
        response = await self.call(request)
        logger.info(f"BootNotification response: {response}")
        return response

    async def send_heartbeat(self):
        request = call.HeartbeatPayload()
        response = await self.call(request)
        logger.info(f"Heartbeat response: {response}")
        return response

    async def send_status_notification(self, connector_id: int, status: str):
        request = call.StatusNotificationPayload(
            connector_id=connector_id,
            error_code="NoError",
            status=status
        )
        response = await self.call(request)
        logger.info(f"StatusNotification response: {response}")
        return response

    async def send_authorize(self, id_tag: str):
        """Send authorization request for an ID tag"""
        async with self._authorization_lock:
            # Check if we already have this tag authorized
            if id_tag in self.authorized_tags:
                logger.info(f"✅ ID tag {id_tag} already authorized")
                return True
            
            try:
                request = call.AuthorizePayload(id_tag=id_tag)
                response = await self.call(request)
                logger.info(f"Authorize response for {id_tag}: {response}")
                
                # Store authorization result
                if hasattr(response, 'id_tag_info') and isinstance(response.id_tag_info, dict):
                    status = response.id_tag_info.get('status')
                    if status == AuthorizationStatus.accepted:
                        self.authorized_tags.add(id_tag)
                        logger.info(f"✅ ID tag {id_tag} authorized successfully")
                        return True
                    else:
                        logger.warning(f"❌ ID tag {id_tag} authorization rejected: {status}")
                        return False
                else:
                    logger.warning(f"❌ ID tag {id_tag} authorization failed - invalid response: {response}")
                    return False
            except Exception as e:
                logger.error(f"❌ Authorization error for {id_tag}: {e}")
                return False

    async def send_start_transaction(self, connector_id: int, id_tag: str):
        """Start a charging transaction"""
        self.meter_start_value = random.randint(1000, 5000)  # Random starting meter value
        self.meter_current_value = self.meter_start_value
        
        request = call.StartTransactionPayload(
            connector_id=connector_id,
            id_tag=id_tag,
            meter_start=self.meter_start_value,
            timestamp=datetime.utcnow().isoformat()
        )
        response = await self.call(request)
        logger.info(f"StartTransaction response: {response}")
        
        if hasattr(response, 'transaction_id'):
            self.current_transaction_id = response.transaction_id
            self.charging = True
            logger.info(f"🔋 Transaction started with ID: {self.current_transaction_id}")
            
            # Update status to charging
            await self.send_status_notification(connector_id, ChargePointStatus.charging)
        
        return response

    async def send_stop_transaction(self, connector_id: int, reason="Remote"):
        """Stop the current charging transaction"""
        if not self.current_transaction_id:
            logger.warning("No active transaction to stop")
            return
        
        # Update status to finishing
        await self.send_status_notification(connector_id, ChargePointStatus.finishing)
        
        request = call.StopTransactionPayload(
            transaction_id=self.current_transaction_id,
            meter_stop=self.meter_current_value,
            timestamp=datetime.utcnow().isoformat(),
            reason=reason
        )
        response = await self.call(request)
        logger.info(f"StopTransaction response: {response}")
        
        energy_consumed = self.meter_current_value - self.meter_start_value
        logger.info(f"🛑 Transaction {self.current_transaction_id} stopped. Energy consumed: {energy_consumed} Wh")
        
        self.current_transaction_id = None
        self.charging = False
        
        # Update status back to available
        await self.send_status_notification(connector_id, ChargePointStatus.available)
        
        return response

    async def send_meter_values(self, connector_id: int, transaction_id: int = None):
        """Send meter values - if charging, increment the value"""
        if self.charging:
            # Simulate energy consumption (add 10-50 Wh per reading)
            self.meter_current_value += random.randint(10, 50)
        
        request = call.MeterValuesPayload(
            connector_id=connector_id,
            transaction_id=transaction_id or self.current_transaction_id,
            meter_value=[{
                "timestamp": datetime.utcnow().isoformat(),
                "sampledValue": [{
                    "value": str(self.meter_current_value),
                    "context": "Sample.Periodic",
                    "format": "Raw",
                    "measurand": "Energy.Active.Import.Register",
                    "unit": "Wh"
                }]
            }]
        )
        response = await self.call(request)
        logger.info(f"MeterValues response: {response} (Current: {self.meter_current_value} Wh)")

    # Handle remote start transaction request from CMS
    @on(Action.RemoteStartTransaction)
    async def on_remote_start_transaction(self, id_tag, connector_id=None, charging_profile=None):
        """Handle RemoteStartTransaction request from CMS"""
        # Default to connector 1 if not specified
        if connector_id is None:
            connector_id = 1
            
        logger.info(f"🎯 Received RemoteStartTransaction request - Connector: {connector_id}, ID Tag: {id_tag}")
        
        try:
            # Check if charger is available
            if self.charging:
                logger.warning("⚠️ Charger is already charging, cannot start new transaction")
                return call_result.RemoteStartTransactionPayload(status=RemoteStartStopStatus.rejected)
            
            # Skip explicit authorization for now - CMS handles this
            # The demo charger will trust that the CMS has already authorized the tag
            logger.info(f"🔐 Trusting CMS authorization for ID tag: {id_tag}")
            self.authorized_tags.add(id_tag)  # Add to our local cache
            
            # Start the process asynchronously to avoid timeouts
            asyncio.create_task(self._handle_remote_start_async(connector_id, id_tag))
            
            logger.info(f"✅ Remote start transaction accepted for {id_tag}")
            return call_result.RemoteStartTransactionPayload(status=RemoteStartStopStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in remote start transaction: {e}")
            return call_result.RemoteStartTransactionPayload(status=RemoteStartStopStatus.rejected)

    # Handle remote stop transaction request from CMS
    @on(Action.RemoteStopTransaction)
    async def on_remote_stop_transaction(self, transaction_id):
        """Handle RemoteStopTransaction request from CMS"""
        logger.info(f"🛑 Received RemoteStopTransaction request - Transaction ID: {transaction_id}")
        
        try:
            # Check if this is the current transaction
            if not self.charging or self.current_transaction_id != transaction_id:
                logger.warning(f"⚠️ No matching active transaction found for ID: {transaction_id}")
                return call_result.RemoteStopTransactionPayload(status=RemoteStartStopStatus.rejected)
            
            # Start the stop process asynchronously to avoid timeouts
            asyncio.create_task(self._handle_remote_stop_async(transaction_id))
            
            logger.info(f"✅ Remote stop transaction accepted for {transaction_id}")
            return call_result.RemoteStopTransactionPayload(status=RemoteStartStopStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in remote stop transaction: {e}")
            return call_result.RemoteStopTransactionPayload(status=RemoteStartStopStatus.rejected)

    # Handle GetConfiguration request from CMS
    @on(Action.GetConfiguration)
    async def on_get_configuration(self, key=None, **kwargs):
        """Handle GetConfiguration request from CMS"""
        logger.info(f"⚙️ Received GetConfiguration request - Keys: {key}")
        
        # Sample configuration data for the demo charger
        all_config_keys = [
            {"key": "AuthorizeRemoteTxRequests", "readonly": False, "value": "true"},
            {"key": "ClockAlignedDataInterval", "readonly": False, "value": "900"},
            {"key": "ConnectionTimeOut", "readonly": False, "value": "60"},
            {"key": "HeartbeatInterval", "readonly": False, "value": "30"},
            {"key": "LocalAuthorizeOffline", "readonly": False, "value": "true"},
            {"key": "LocalPreAuthorize", "readonly": False, "value": "false"},
            {"key": "MeterValuesAlignedData", "readonly": False, "value": "Energy.Active.Import.Register"},
            {"key": "MeterValuesSampledData", "readonly": False, "value": "Energy.Active.Import.Register"},
            {"key": "MeterValueSampleInterval", "readonly": False, "value": "60"},
            {"key": "NumberOfConnectors", "readonly": True, "value": "1"},
            {"key": "ResetRetries", "readonly": False, "value": "3"},
            {"key": "StopTransactionOnEVSideDisconnect", "readonly": False, "value": "true"},
            {"key": "StopTransactionOnInvalidId", "readonly": False, "value": "true"},
            {"key": "SupportedFeatureProfiles", "readonly": True, "value": "Core,LocalAuthListManagement,RemoteTrigger"},
            {"key": "TransactionMessageAttempts", "readonly": False, "value": "3"},
            {"key": "TransactionMessageRetryInterval", "readonly": False, "value": "60"},
            {"key": "UnlockConnectorOnEVSideDisconnect", "readonly": False, "value": "true"},
            {"key": "WebSocketPingInterval", "readonly": False, "value": "54"},
            {"key": "LocalAuthListEnabled", "readonly": False, "value": "true"},
            {"key": "LocalAuthListMaxLength", "readonly": True, "value": "100"},
            {"key": "SendLocalListMaxLength", "readonly": True, "value": "20"}
        ]
        
        # Filter configuration keys if specific keys were requested
        if key:
            filtered_keys = [config for config in all_config_keys if config["key"] in key]
            unknown_keys = [k for k in key if k not in [config["key"] for config in all_config_keys]]
        else:
            filtered_keys = all_config_keys
            unknown_keys = []
        
        logger.info(f"✅ Returning {len(filtered_keys)} configuration keys")
        if unknown_keys:
            logger.warning(f"⚠️ Unknown keys requested: {unknown_keys}")
        
        return call_result.GetConfigurationPayload(
            configurationKey=filtered_keys,
            unknownKey=unknown_keys
        )

    # Handle ChangeConfiguration request from CMS
    @on(Action.ChangeConfiguration)
    async def on_change_configuration(self, key, value, **kwargs):
        """Handle ChangeConfiguration request from CMS"""
        logger.info(f"🔧 Received ChangeConfiguration request - Key: {key}, Value: {value}")
        
        # Define read-only keys that cannot be changed
        readonly_keys = [
            "NumberOfConnectors",
            "SupportedFeatureProfiles", 
            "LocalAuthListMaxLength",
            "SendLocalListMaxLength"
        ]
        
        # Check if key is read-only
        if key in readonly_keys:
            logger.warning(f"❌ Cannot change read-only key: {key}")
            return call_result.ChangeConfigurationPayload(status="Rejected")
        
        # Simulate configuration change (in a real charger, this would update actual settings)
        logger.info(f"✅ Configuration changed: {key} = {value}")
        
        # For demo purposes, we'll accept most changes
        # In a real implementation, you'd validate the value and update internal settings
        return call_result.ChangeConfigurationPayload(status="Accepted")

    async def _handle_remote_start_async(self, connector_id: int, id_tag: str):
        """Handle the actual remote start process asynchronously"""
        try:
            # Set status to preparing
            await self.send_status_notification(connector_id, ChargePointStatus.preparing)
            await asyncio.sleep(2)  # Simulate preparation time
            
            # Start the transaction
            await self.send_start_transaction(connector_id, id_tag)
            
            # Start meter value updates
            asyncio.create_task(self._meter_value_loop(connector_id))
            
            logger.info(f"🔋 Remote start process completed for {id_tag}")
        except Exception as e:
            logger.error(f"❌ Error in remote start async process: {e}")
            # Reset to available state on error
            await self.send_status_notification(connector_id, ChargePointStatus.available)

    async def _handle_remote_stop_async(self, transaction_id: int):
        """Handle the actual remote stop process asynchronously"""
        try:
            # Stop the transaction
            await self.send_stop_transaction(1, reason="Remote")
            
            logger.info(f"🛑 Remote stop process completed for transaction {transaction_id}")
        except Exception as e:
            logger.error(f"❌ Error in remote stop async process: {e}")
            # Reset to available state on error
            await self.send_status_notification(1, ChargePointStatus.available)

    async def _meter_value_loop(self, connector_id):
        """Continuously send meter values while charging"""
        while self.charging:
            await self.send_meter_values(connector_id)
            await asyncio.sleep(10)  # Send meter values every 10 seconds

    async def simulate_charging_session(self):
        """Simulate a complete charging session (for demo purposes)"""
        try:
            connector_id = 1
            id_tag = "1234"  # Make sure this ID tag exists in your CMS
            
            logger.info("🔌 Starting automatic charging session simulation...")
            
            # 1. Authorize the ID tag first
            logger.info(f"🔐 Authorizing ID tag: {id_tag}")
            authorized = await self.send_authorize(id_tag)
            
            if not authorized:
                logger.error(f"❌ Authorization failed for {id_tag}, stopping simulation")
                return
            
            # 2. User plugs in cable
            logger.info("📱 User plugged in cable")
            await self.send_status_notification(connector_id, ChargePointStatus.preparing)
            await asyncio.sleep(2)
            
            # 3. Start transaction
            logger.info(f"🏁 Starting transaction with ID tag: {id_tag}")
            await self.send_start_transaction(connector_id, id_tag)
            await asyncio.sleep(2)
            
            # 4. Send meter values during charging (simulate 30 seconds of charging)
            logger.info("⚡ Charging in progress...")
            for i in range(6):  # 6 readings over 30 seconds
                await self.send_meter_values(connector_id)
                await asyncio.sleep(5)  # Send meter values every 5 seconds
            
            # 5. Stop charging
            logger.info("🛑 Stopping charging session...")
            await self.send_stop_transaction(connector_id, reason="Local")
            
            logger.info("✅ Automatic charging session completed!")
            
            energy_consumed = self.meter_current_value - self.meter_start_value
            logger.info(f"📊 Session Summary: {energy_consumed} Wh consumed")
            
        except Exception as e:
            logger.error(f"Error during charging session: {e}")
            # Ensure we're back to available state
            await self.send_status_notification(1, ChargePointStatus.available)

async def main():
    async with websockets.connect(
        "ws://192.168.1.10:8000/ws/DEMO001",
        subprotocols=["ocpp1.6"]
    ) as ws:
        charge_point = ChargePoint("DEMO001", ws)
        
        # Start the OCPP message loop in the background
        asyncio.create_task(charge_point.start())
        
        # Give the server a moment to be ready
        await asyncio.sleep(1)
        
        # Initial setup
        await charge_point.send_boot_notification()
        await charge_point.send_status_notification(1, ChargePointStatus.available)
        
        logger.info("🎯 Demo charger ready! Supports:")
        logger.info("   • Remote Start Transaction")
        logger.info("   • Remote Stop Transaction") 
        logger.info("   • Authorization requests")
        logger.info("   • Automatic charging simulation")
        
        # Ask user if they want to run automatic simulation
        logger.info("⏳ Waiting 10 seconds, then running automatic simulation...")
        logger.info("   (Use Remote Start/Stop from CMS to control manually)")
        await asyncio.sleep(10)
        
        # Run automatic simulation if no manual control happened
        if not charge_point.charging:
            await charge_point.simulate_charging_session()
        
        # Continue with heartbeats
        logger.info("💓 Continuing with regular heartbeats...")
        logger.info("   Charger remains available for remote commands...")
        while True:
            await charge_point.send_heartbeat()
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main()) 
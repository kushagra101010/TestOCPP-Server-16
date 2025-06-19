import asyncio
import logging
import websockets
from datetime import datetime
import random
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call, call_result
from ocpp.v16.enums import RegistrationStatus, ChargePointStatus, AuthorizationStatus, RemoteStartStopStatus, AvailabilityStatus, ReservationStatus, CancelReservationStatus, ChargingProfileStatus, ClearChargingProfileStatus, GetCompositeScheduleStatus
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
        request = call.BootNotification(
            charge_point_model="DemoModel",
            charge_point_vendor="DemoVendor"
        )
        response = await self.call(request)
        logger.info(f"BootNotification response: {response}")
        return response

    async def send_heartbeat(self):
        request = call.Heartbeat()
        response = await self.call(request)
        logger.info(f"Heartbeat response: {response}")
        return response

    async def send_status_notification(self, connector_id: int, status: str):
        request = call.StatusNotification(
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
                request = call.Authorize(id_tag=id_tag)
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
        
        request = call.StartTransaction(
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
        
        request = call.StopTransaction(
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
        
        request = call.MeterValues(
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
    @on('RemoteStartTransaction')
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
                return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.rejected)
            
            # Skip explicit authorization for now - CMS handles this
            # The demo charger will trust that the CMS has already authorized the tag
            logger.info(f"🔐 Trusting CMS authorization for ID tag: {id_tag}")
            self.authorized_tags.add(id_tag)  # Add to our local cache
            
            # Start the process asynchronously to avoid timeouts
            asyncio.create_task(self._handle_remote_start_async(connector_id, id_tag))
            
            logger.info(f"✅ Remote start transaction accepted for {id_tag}")
            return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in remote start transaction: {e}")
            return call_result.RemoteStartTransaction(status=RemoteStartStopStatus.rejected)

    # Handle remote stop transaction request from CMS
    @on('RemoteStopTransaction')
    async def on_remote_stop_transaction(self, transaction_id):
        """Handle RemoteStopTransaction request from CMS"""
        logger.info(f"🛑 Received RemoteStopTransaction request - Transaction ID: {transaction_id}")
        
        try:
            # Check if this is the current transaction
            if not self.charging or self.current_transaction_id != transaction_id:
                logger.warning(f"⚠️ No matching active transaction found for ID: {transaction_id}")
                return call_result.RemoteStopTransaction(status=RemoteStartStopStatus.rejected)
            
            # Start the stop process asynchronously to avoid timeouts
            asyncio.create_task(self._handle_remote_stop_async(transaction_id))
            
            logger.info(f"✅ Remote stop transaction accepted for {transaction_id}")
            return call_result.RemoteStopTransaction(status=RemoteStartStopStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in remote stop transaction: {e}")
            return call_result.RemoteStopTransaction(status=RemoteStartStopStatus.rejected)

    # Handle GetConfiguration request from CMS
    @on('GetConfiguration')
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
        
        return call_result.GetConfiguration(
            configurationKey=filtered_keys,
            unknownKey=unknown_keys
        )

    # Handle ChangeConfiguration request from CMS
    @on('ChangeConfiguration')
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
            return call_result.ChangeConfiguration(status="Rejected")
        
        # Simulate configuration change (in a real charger, this would update actual settings)
        logger.info(f"✅ Configuration changed: {key} = {value}")
        
        # For demo purposes, we'll accept most changes
        # In a real implementation, you'd validate the value and update internal settings
        return call_result.ChangeConfiguration(status="Accepted")

    # Handle Reset request from CMS
    @on('Reset')
    async def on_reset(self, type, **kwargs):
        """Handle Reset request from CMS"""
        logger.info(f"🔄 Received Reset request - Type: {type}")
        
        try:
            if type.lower() == "hard":
                logger.info("⚡ Performing HARD RESET - Simulating complete restart...")
                # In a real charger, this would trigger a hardware reset/reboot
                
                # Stop any active transaction first
                if self.charging and self.current_transaction_id:
                    logger.info("🛑 Stopping active transaction before reset...")
                    await self.send_stop_transaction(1, reason="PowerLoss")
                
                # Simulate reset delay
                await asyncio.sleep(2)
                logger.info("💀 Hard reset completed - charger would restart now")
                
            elif type.lower() == "soft":
                logger.info("🔄 Performing SOFT RESET - Restarting software...")
                # In a real charger, this would restart the software without power cycle
                
                # Stop any active transaction first
                if self.charging and self.current_transaction_id:
                    logger.info("🛑 Stopping active transaction before reset...")
                    await self.send_stop_transaction(1, reason="SoftReset")
                
                # Reset internal state
                self.current_transaction_id = None
                self.charging = False
                self.authorized_tags.clear()
                
                # Simulate restart
                await asyncio.sleep(1)
                # Send status notification asynchronously to avoid blocking the response
                asyncio.create_task(self.send_status_notification(1, ChargePointStatus.available))
                logger.info("✅ Soft reset completed - charger software restarted")
            
            return call_result.Reset(status="Accepted")
            
        except Exception as e:
            logger.error(f"❌ Error during reset: {e}")
            return call_result.Reset(status="Rejected")

    # === NEW HANDLERS FOR ADVANCED FUNCTIONS ===
    
    # Handle ChangeAvailability request from CMS
    @on('ChangeAvailability')
    async def on_change_availability(self, connector_id, **kwargs):
        """Handle ChangeAvailability request from CMS"""
        availability_type = kwargs.get('type')
        logger.info(f"🔧 ChangeAvailability: connector={connector_id}, type={availability_type}")
        
        try:
            # Check if it's a valid AvailabilityType enum or string
            type_str = str(availability_type)
            logger.info(f"🔧 Type string: {type_str}")
            
            if "inoperative" in type_str.lower() or "Inoperative" in type_str:
                logger.info(f"🚫 Setting connector {connector_id} to INOPERATIVE")
                # Send status notification asynchronously to avoid blocking the response
                asyncio.create_task(self.send_status_notification(connector_id, ChargePointStatus.unavailable))
                return call_result.ChangeAvailability(status=AvailabilityStatus.accepted)
                
            elif "operative" in type_str.lower() or "Operative" in type_str:
                logger.info(f"✅ Setting connector {connector_id} to OPERATIVE")
                # Send status notification asynchronously to avoid blocking the response
                asyncio.create_task(self.send_status_notification(connector_id, ChargePointStatus.available))
                return call_result.ChangeAvailability(status=AvailabilityStatus.accepted)
            
            else:
                logger.warning(f"❌ Unknown availability type: {availability_type}")
                return call_result.ChangeAvailability(status=AvailabilityStatus.rejected)
                
        except Exception as e:
            logger.error(f"❌ Error in ChangeAvailability: {e}")
            return call_result.ChangeAvailability(status=AvailabilityStatus.rejected)

    # Handle ReserveNow request from CMS
    @on('ReserveNow')
    async def on_reserve_now(self, connector_id, expiry_date, id_tag, reservation_id, parent_id_tag=None, **kwargs):
        """Handle ReserveNow request from CMS"""
        logger.info(f"🅿️ Received ReserveNow request - Connector: {connector_id}, ID Tag: {id_tag}, Reservation ID: {reservation_id}")
        
        try:
            # Check if connector is available
            if self.charging and connector_id == 1:
                logger.warning("⚠️ Connector is occupied, cannot reserve")
                return call_result.ReserveNow(status=ReservationStatus.occupied)
            
            # Store reservation (in a real charger, this would be persistent)
            if not hasattr(self, 'reservations'):
                self.reservations = {}
            
            self.reservations[reservation_id] = {
                'connector_id': connector_id,
                'id_tag': id_tag,
                'expiry_date': expiry_date,
                'parent_id_tag': parent_id_tag
            }
            
            # Update status to reserved asynchronously
            asyncio.create_task(self.send_status_notification(connector_id, ChargePointStatus.reserved))
            
            logger.info(f"✅ Reservation {reservation_id} created for connector {connector_id}")
            return call_result.ReserveNow(status=ReservationStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in ReserveNow handler: {e}")
            return call_result.ReserveNow(status=ReservationStatus.rejected)

    # Handle CancelReservation request from CMS
    @on('CancelReservation')
    async def on_cancel_reservation(self, reservation_id, **kwargs):
        """Handle CancelReservation request from CMS"""
        logger.info(f"❌ Received CancelReservation request - Reservation ID: {reservation_id}")
        
        try:
            # Check if reservation exists
            if not hasattr(self, 'reservations') or reservation_id not in self.reservations:
                logger.warning(f"⚠️ Reservation {reservation_id} not found")
                return call_result.CancelReservation(status=CancelReservationStatus.rejected)
            
            # Get reservation details
            reservation = self.reservations[reservation_id]
            connector_id = reservation['connector_id']
            
            # Remove reservation
            del self.reservations[reservation_id]
            
            # Update status back to available (if not charging) asynchronously
            if not self.charging:
                asyncio.create_task(self.send_status_notification(connector_id, ChargePointStatus.available))
            
            logger.info(f"✅ Reservation {reservation_id} cancelled for connector {connector_id}")
            return call_result.CancelReservation(status=CancelReservationStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in CancelReservation handler: {e}")
            return call_result.CancelReservation(status=CancelReservationStatus.rejected)

    # Handle SetChargingProfile request from CMS
    @on('SetChargingProfile')
    async def on_set_charging_profile(self, connector_id, cs_charging_profiles, **kwargs):
        """Handle SetChargingProfile request from CMS"""
        profile_id = cs_charging_profiles.get('chargingProfileId', 'Unknown')
        logger.info(f"🔋 Received SetChargingProfile request - Connector: {connector_id}, Profile ID: {profile_id}")
        
        try:
            # Store charging profile (in a real charger, this would control actual charging behavior)
            if not hasattr(self, 'charging_profiles'):
                self.charging_profiles = {}
            
            connector_key = f"connector_{connector_id}"
            if connector_key not in self.charging_profiles:
                self.charging_profiles[connector_key] = {}
            
            self.charging_profiles[connector_key][profile_id] = cs_charging_profiles
            
            # Log profile details
            purpose = cs_charging_profiles.get('chargingProfilePurpose', 'Unknown')
            kind = cs_charging_profiles.get('chargingProfileKind', 'Unknown')
            stack_level = cs_charging_profiles.get('stackLevel', 'Unknown')
            
            logger.info(f"📊 Charging Profile Details:")
            logger.info(f"   - Purpose: {purpose}")
            logger.info(f"   - Kind: {kind}")
            logger.info(f"   - Stack Level: {stack_level}")
            
            # Log charging schedule if present
            if 'chargingSchedule' in cs_charging_profiles:
                schedule = cs_charging_profiles['chargingSchedule']
                rate_unit = schedule.get('chargingRateUnit', 'Unknown')
                periods = schedule.get('chargingSchedulePeriod', [])
                logger.info(f"   - Rate Unit: {rate_unit}")
                logger.info(f"   - Schedule Periods: {len(periods)}")
                
                for i, period in enumerate(periods[:3]):  # Show first 3 periods
                    start = period.get('startPeriod', 'Unknown')
                    limit = period.get('limit', 'Unknown')
                    logger.info(f"     Period {i+1}: Start={start}s, Limit={limit}{rate_unit}")
            
            logger.info(f"✅ Charging profile {profile_id} set for connector {connector_id}")
            return call_result.SetChargingProfile(status=ChargingProfileStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in SetChargingProfile handler: {e}")
            return call_result.SetChargingProfile(status=ChargingProfileStatus.rejected)

    # Handle ClearChargingProfile request from CMS
    @on('ClearChargingProfile')
    async def on_clear_charging_profile(self, id=None, connector_id=None, charging_profile_purpose=None, stack_level=None, **kwargs):
        """Handle ClearChargingProfile request from CMS"""
        logger.info(f"🗑️ Received ClearChargingProfile request")
        if id: logger.info(f"   - Profile ID: {id}")
        if connector_id: logger.info(f"   - Connector ID: {connector_id}")
        if charging_profile_purpose: logger.info(f"   - Purpose: {charging_profile_purpose}")
        if stack_level: logger.info(f"   - Stack Level: {stack_level}")
        
        try:
            if not hasattr(self, 'charging_profiles'):
                self.charging_profiles = {}
            
            profiles_cleared = 0
            
            # Clear profiles based on criteria
            connectors_to_check = []
            if connector_id is not None:
                connectors_to_check = [f"connector_{connector_id}"]
            else:
                connectors_to_check = list(self.charging_profiles.keys())
            
            for conn_key in connectors_to_check:
                if conn_key in self.charging_profiles:
                    profiles_to_remove = []
                    
                    for prof_id, profile in self.charging_profiles[conn_key].items():
                        should_remove = True
                        
                        # Check all criteria
                        if id is not None and profile.get('chargingProfileId') != id:
                            should_remove = False
                        if charging_profile_purpose and profile.get('chargingProfilePurpose') != charging_profile_purpose:
                            should_remove = False
                        if stack_level is not None and profile.get('stackLevel') != stack_level:
                            should_remove = False
                        
                        if should_remove:
                            profiles_to_remove.append(prof_id)
                    
                    # Remove matching profiles
                    for prof_id in profiles_to_remove:
                        del self.charging_profiles[conn_key][prof_id]
                        profiles_cleared += 1
                        logger.info(f"🗑️ Cleared charging profile {prof_id} from {conn_key}")
                    
                    # Clean up empty connector entries
                    if not self.charging_profiles[conn_key]:
                        del self.charging_profiles[conn_key]
            
            logger.info(f"✅ Cleared {profiles_cleared} charging profile(s)")
            return call_result.ClearChargingProfile(status=ClearChargingProfileStatus.accepted)
            
        except Exception as e:
            logger.error(f"❌ Error in ClearChargingProfile handler: {e}")
            return call_result.ClearChargingProfile(status=ClearChargingProfileStatus.unknown)

    # Handle GetCompositeSchedule request from CMS
    @on('GetCompositeSchedule')
    async def on_get_composite_schedule(self, connector_id, duration, charging_rate_unit=None, **kwargs):
        """Handle GetCompositeSchedule request from CMS"""
        logger.info(f"📊 Received GetCompositeSchedule request - Connector: {connector_id}, Duration: {duration}s")
        if charging_rate_unit:
            logger.info(f"   - Charging Rate Unit: {charging_rate_unit}")
        
        try:
            if not hasattr(self, 'charging_profiles'):
                self.charging_profiles = {}
            
            connector_key = f"connector_{connector_id}"
            
            # Check if we have any profiles for this connector
            if connector_key not in self.charging_profiles or not self.charging_profiles[connector_key]:
                logger.info("📋 No charging profiles found for connector")
                return call_result.GetCompositeSchedule(status=GetCompositeScheduleStatus.rejected)
            
            # Get current time as schedule start
            from datetime import datetime
            schedule_start = datetime.utcnow().isoformat() + "Z"
            
            # Build a composite schedule from all active profiles
            # For demo purposes, we'll use the profile with the highest stack level
            active_profiles = self.charging_profiles[connector_key]
            
            # Sort profiles by stack level (higher number = higher priority)
            sorted_profiles = sorted(
                active_profiles.values(), 
                key=lambda x: x.get('stackLevel', 0), 
                reverse=True
            )
            
            if not sorted_profiles:
                logger.info("📋 No valid charging profiles found")
                return call_result.GetCompositeSchedule(status=GetCompositeScheduleStatus.rejected)
            
            # Use the highest priority profile as the basis for composite schedule
            primary_profile = sorted_profiles[0]
            charging_schedule = primary_profile.get('chargingSchedule', {})
            
            # Determine the charging rate unit
            if charging_rate_unit:
                # Use requested rate unit
                effective_rate_unit = charging_rate_unit
            else:
                # Use the rate unit from the profile
                effective_rate_unit = charging_schedule.get('chargingRateUnit', 'A')
            
            # Build the composite schedule
            composite_schedule = {
                'duration': min(duration, charging_schedule.get('duration', duration)),
                'startSchedule': schedule_start,
                'chargingRateUnit': effective_rate_unit,
                'chargingSchedulePeriod': charging_schedule.get('chargingSchedulePeriod', [
                    {
                        'startPeriod': 0,
                        'limit': 16.0,  # Default 16A limit
                        'numberPhases': 3
                    }
                ])
            }
            
            # Add min charging rate if present
            if 'minChargingRate' in charging_schedule:
                composite_schedule['minChargingRate'] = charging_schedule['minChargingRate']
            
            logger.info(f"📊 Composite Schedule Details:")
            logger.info(f"   - Rate Unit: {effective_rate_unit}")
            logger.info(f"   - Duration: {composite_schedule['duration']}s")
            logger.info(f"   - Periods: {len(composite_schedule['chargingSchedulePeriod'])}")
            
            # Log first few periods
            for i, period in enumerate(composite_schedule['chargingSchedulePeriod'][:3]):
                start = period.get('startPeriod', 0)
                limit = period.get('limit', 0)
                logger.info(f"     Period {i+1}: Start={start}s, Limit={limit}{effective_rate_unit}")
            
            logger.info(f"✅ Returning composite schedule for connector {connector_id}")
            
            return call_result.GetCompositeSchedule(
                status=GetCompositeScheduleStatus.accepted,
                connector_id=connector_id,
                schedule_start=schedule_start,
                charging_schedule=composite_schedule
            )
            
        except Exception as e:
            logger.error(f"❌ Error in GetCompositeSchedule handler: {e}")
            return call_result.GetCompositeSchedule(status=GetCompositeScheduleStatus.rejected)

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

    async def demonstrate_advanced_features(self):
        """Demonstrate the new OCPP 1.6 features (for testing purposes)"""
        try:
            logger.info("🎯 Demonstrating Advanced OCPP 1.6 Features...")
            logger.info("   (These features are now available for CMS to use)")
            
            # Display current capabilities
            logger.info("✨ Supported Advanced Features:")
            logger.info("   🔧 Change Availability (Operative/Inoperative)")
            logger.info("   🅿️ Reservation Management (ReserveNow/CancelReservation)")
            logger.info("   🔋 Smart Charging (SetChargingProfile/ClearChargingProfile/GetCompositeSchedule)")
            
            # Show current states
            logger.info("📊 Current Charger State:")
            logger.info(f"   - Charging: {self.charging}")
            logger.info(f"   - Current Transaction: {self.current_transaction_id}")
            logger.info(f"   - Authorized Tags: {len(self.authorized_tags)}")
            
            if hasattr(self, 'reservations'):
                logger.info(f"   - Active Reservations: {len(self.reservations)}")
            
            if hasattr(self, 'charging_profiles'):
                profile_count = sum(len(profiles) for profiles in self.charging_profiles.values())
                logger.info(f"   - Charging Profiles: {profile_count}")
            
            logger.info("🎮 Use the CMS web interface or API to test these features:")
            logger.info("   • Send ChangeAvailability to make connector operative/inoperative")
            logger.info("   • Create reservations with ReserveNow")
            logger.info("   • Set charging profiles for smart charging")
            logger.info("   • Get composite schedules to see active charging limits")
            
        except Exception as e:
            logger.error(f"Error in advanced features demonstration: {e}")

async def main():
    async with websockets.connect(
        "ws://localhost:8000/ws/DEMO001",
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
        logger.info("   • Change Availability")
        logger.info("   • Reservation Management")
        logger.info("   • Smart Charging")
        logger.info("   • Automatic charging simulation")
        
        # Demonstrate advanced features
        await charge_point.demonstrate_advanced_features()
        
        # Ask user if they want to run automatic simulation
        logger.info("⏳ Waiting 10 seconds, then running automatic simulation...")
        logger.info("   (Use CMS interface to test new features manually)")
        await asyncio.sleep(10)
        
        # Run automatic simulation if no manual control happened
        if not charge_point.charging:
            await charge_point.simulate_charging_session()
        
        # Continue with heartbeats
        logger.info("💓 Continuing with regular heartbeats...")
        logger.info("   Charger remains available for remote commands...")
        logger.info("   ✨ NEW: Test Change Availability, Reservations, and Smart Charging!")
        while True:
            await charge_point.send_heartbeat()
            await asyncio.sleep(30)

if __name__ == "__main__":
    asyncio.run(main()) 
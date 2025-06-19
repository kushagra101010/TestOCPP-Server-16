import logging
import json
import asyncio
from datetime import datetime
from ocpp.routing import on
from ocpp.v16.enums import (
    RegistrationStatus, AuthorizationStatus, ChargePointStatus,
    RemoteStartStopStatus, DataTransferStatus, AvailabilityType
)
from ocpp.v16 import ChargePoint as BaseChargePoint
from ocpp.v16 import call, call_result
from ocpp.v16.datatypes import IdTagInfo, MeterValue, SampledValue

from .database import db, Charger, IdTag
from .charger_store import charger_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChargePoint(BaseChargePoint):
    def __init__(self, id, connection):
        super().__init__(id, connection)
        self.charge_point_id = id
        
        # Add or update charger in database
        charger = db.session.query(Charger).filter_by(charge_point_id=id).first()
        if not charger:
            charger = Charger(charge_point_id=id, status=ChargePointStatus.available)
            db.session.add(charger)
        db.session.commit()
        
        logger.info(f"Initialized ChargePoint: {id}")

    async def on_connect(self):
        """Handle charger connection."""
        # Don't update status here - let StatusNotification handle it
        # The API will show the correct status based on WebSocket connectivity
        logger.info(f"Charger {self.charge_point_id} connected")

    async def on_disconnect(self):
        """Handle charger disconnection."""
        # Don't update status here - the API will show "Disconnected" when WebSocket is not connected
        # This preserves the last known status from StatusNotification
        logger.info(f"Charger {self.charge_point_id} disconnected")

    @on('BootNotification')
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        try:
            logger.info(f"BootNotification from {self.charge_point_id}: vendor={charge_point_vendor}, model={charge_point_model}")
            
            # Add charger to store
            charger_store.add_charger(self.charge_point_id)
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"BootNotification: vendor={charge_point_vendor}, model={charge_point_model}")
            
            return call_result.BootNotification(
                current_time=datetime.utcnow().isoformat(),
                interval=30,
                status=RegistrationStatus.accepted
            )
        except Exception as e:
            logger.error(f"Error in BootNotification handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('StatusNotification')
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        try:
            logger.info(f"Status notification from {self.charge_point_id}: connector {connector_id} - {status}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"StatusNotification: connector={connector_id}, error_code={error_code}, status={status}")
            
            # Update charger status in database
            charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
            if charger:
                charger.status = status
                db.session.commit()
            
            # Also update connector-specific status using charger store
            charger_store.update_connector_status(self.charge_point_id, connector_id, status)
            
            logger.debug(f"Updated {self.charge_point_id} status to {status}")
                
            return call_result.StatusNotification()
        except Exception as e:
            logger.error(f"Error in StatusNotification handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('Heartbeat')
    async def on_heartbeat(self, **kwargs):
        try:
            logger.info(f"Heartbeat received from {self.charge_point_id}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, "Heartbeat received")
            
            # Update last heartbeat timestamp
            charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
            if charger:
                charger.last_heartbeat = datetime.utcnow()
                db.session.commit()
            
            return call_result.Heartbeat(
                current_time=datetime.utcnow().isoformat()
            )
        except Exception as e:
            logger.error(f"Error in Heartbeat handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('Authorize')
    async def on_authorize(self, id_tag: str, **kwargs):
        try:
            logger.info(f"Authorization request from {self.charge_point_id} for ID tag: {id_tag}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"Authorization request for ID tag: {id_tag}")
            
            # Check if ID tag is authorized
            tag = db.session.query(IdTag).filter_by(id_tag=id_tag).first()
            
            if tag and tag.status == AuthorizationStatus.accepted:
                status = AuthorizationStatus.accepted
            else:
                status = AuthorizationStatus.invalid
            
            return call_result.Authorize(
                id_tag_info=IdTagInfo(
                    status=status
                )
            )
        except Exception as e:
            logger.error(f"Error in Authorize handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('StartTransaction')
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        try:
            logger.info(f"Start transaction from {self.charge_point_id}: connector={connector_id}, id_tag={id_tag}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"StartTransaction: connector={connector_id}, id_tag={id_tag}, meter_start={meter_start}")
            
            # Generate transaction ID
            transaction_id = int(datetime.utcnow().timestamp())
            
            # Store active transaction in database (without changing overall status)
            charger_store.set_active_transaction(self.charge_point_id, transaction_id, connector_id, id_tag)
            
            logger.info(f"✅ Transaction {transaction_id} started for {self.charge_point_id}")
            
            # Create the response
            response = call_result.StartTransaction(
                transaction_id=transaction_id,
                id_tag_info=IdTagInfo(
                    status=AuthorizationStatus.accepted
                )
            )
            
            # Send Jio_BP data transfer packets after StartTransaction response if configured
            # Use asyncio.create_task to send packets after 500ms delay without blocking the response
            asyncio.create_task(self._send_jio_bp_data_transfer_after_delay())
            
            # Send MSIL data transfer packets after StartTransaction response if configured
            asyncio.create_task(self._send_msil_data_transfer_after_delay())
            
            # Send CZ data transfer packets after StartTransaction response if configured
            asyncio.create_task(self._send_cz_data_transfer_after_delay())
            
            return response
        except Exception as e:
            logger.error(f"Error in StartTransaction handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('StopTransaction')
    async def on_stop_transaction(self, meter_stop: int, timestamp: str, transaction_id: int, **kwargs):
        try:
            logger.info(f"Stop transaction from {self.charge_point_id}: transaction_id={transaction_id}, meter_stop={meter_stop}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"StopTransaction: transaction_id={transaction_id}, meter_stop={meter_stop}")
            
            # Clear active transaction from database
            charger_store.clear_active_transaction(self.charge_point_id, transaction_id)
            
            logger.info(f"✅ Transaction {transaction_id} stopped for {self.charge_point_id}")
            
            return call_result.StopTransaction()
        except Exception as e:
            logger.error(f"Error in StopTransaction handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('MeterValues')
    async def on_meter_values(self, connector_id: int, meter_value: list, **kwargs):
        try:
            logger.info(f"Meter values from {self.charge_point_id}: connector={connector_id}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"MeterValues: connector={connector_id}, values={len(meter_value)} readings")
            
            return call_result.MeterValues()
        except Exception as e:
            logger.error(f"Error in MeterValues handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('DataTransfer')
    async def on_data_transfer(self, vendor_id: str, **kwargs):
        try:
            import json
            logger.info(f"Data transfer from {self.charge_point_id}: vendor_id={vendor_id}")
            
            # Extract message_id and data from kwargs
            message_id = kwargs.get('message_id', None)
            data = kwargs.get('data', None)
            
            # Check if data is an object (OCPP violation) or string (compliant)
            if data is not None:
                if isinstance(data, dict):
                    # Data is an object - OCPP violation but accept it
                    charger_store.add_log(self.charge_point_id, f"⚠️ RECEIVED OCPP VIOLATION ⚠️ DataTransfer from charger: data field received as OBJECT instead of STRING")
                    charger_store.add_log(self.charge_point_id, f"📥 Charger DataTransfer: vendorId={vendor_id}, messageId={message_id}, data={json.dumps(data)} [VIOLATES OCPP 1.6 STANDARD]")
                    logger.warning(f"OCPP violation: Charger {self.charge_point_id} sent DataTransfer with object data (accepted)")
                elif isinstance(data, str):
                    # Data is a string - OCPP compliant
                    charger_store.add_log(self.charge_point_id, f"✅ DataTransfer from charger: vendorId={vendor_id}, messageId={message_id}, data={data} [OCPP COMPLIANT]")
                else:
                    # Data is some other type
                    charger_store.add_log(self.charge_point_id, f"⚠️ DataTransfer from charger: vendorId={vendor_id}, messageId={message_id}, data={data} [UNEXPECTED DATA TYPE: {type(data).__name__}]")
            else:
                # No data field
                charger_store.add_log(self.charge_point_id, f"DataTransfer from charger: vendorId={vendor_id}, messageId={message_id}, data=None")
            
            # Log additional details for specific vendors
            if vendor_id == "MSIL":
                charger_store.add_log(self.charge_point_id, f"🔍 MSIL DataTransfer received - checking for object format (expected violation)")
            elif vendor_id == "CZ":
                charger_store.add_log(self.charge_point_id, f"🔍 CZ DataTransfer received - checking for string format (OCPP compliant)")
            
            return call_result.DataTransfer(
                status=DataTransferStatus.accepted
            )
        except Exception as e:
            logger.error(f"Error in DataTransfer handler: {e}")
            charger_store.add_log(self.charge_point_id, f"❌ DataTransfer handler failed: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('FirmwareStatusNotification')
    async def on_firmware_status_notification(self, status: str, **kwargs):
        try:
            logger.info(f"Firmware status notification from {self.charge_point_id}: status={status}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"FirmwareStatusNotification: status={status}")
            
            return call_result.FirmwareStatusNotification()
        except Exception as e:
            logger.error(f"Error in FirmwareStatusNotification handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    @on('DiagnosticsStatusNotification')
    async def on_diagnostics_status_notification(self, status: str, **kwargs):
        try:
            logger.info(f"Diagnostics status notification from {self.charge_point_id}: status={status}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"DiagnosticsStatusNotification: status={status}")
            
            return call_result.DiagnosticsStatusNotification()
        except Exception as e:
            logger.error(f"Error in DiagnosticsStatusNotification handler: {e}")
            import traceback
            traceback.print_exc()
            raise

    # Remote commands that can be sent to chargers
    async def remote_start_transaction(self, connector_id: int, id_tag: str):
        """Send remote start transaction command to charger."""
        try:
            request_params = {"id_tag": id_tag}
            
            # Only include connector_id if explicitly provided (not None)
            if connector_id is not None:
                request_params["connector_id"] = int(connector_id)
            
            request = call.RemoteStartTransaction(**request_params)
            response = await self.call(request)
            
            connector_msg = f", connector={connector_id}" if connector_id is not None else ""
            charger_store.add_log(self.charge_point_id, f"RemoteStartTransaction sent: id_tag={id_tag}{connector_msg}, status={response.status}")
            
            return response.status == RemoteStartStopStatus.accepted
        except Exception as e:
            logger.error(f"Error sending RemoteStartTransaction: {e}")
            charger_store.add_log(self.charge_point_id, f"RemoteStartTransaction failed: {e}")
            return False

    async def remote_stop_transaction(self, transaction_id: int):
        """Send remote stop transaction command to charger."""
        try:
            # Ensure transaction_id is an integer
            transaction_id = int(transaction_id)
            
            request = call.RemoteStopTransaction(
                transaction_id=transaction_id
            )
            response = await self.call(request)
            
            charger_store.add_log(self.charge_point_id, f"RemoteStopTransaction sent: transaction_id={transaction_id}, status={response.status}")
            
            return response.status == RemoteStartStopStatus.accepted
        except Exception as e:
            logger.error(f"Error sending RemoteStopTransaction: {e}")
            charger_store.add_log(self.charge_point_id, f"RemoteStopTransaction failed: {e}")
            return False

    async def get_configuration(self, keys: list = None):
        """Send GetConfiguration request."""
        try:
            logger.info(f"Sending get configuration to {self.charge_point_id}")
            # Only include 'key' parameter if keys is provided and not empty
            if keys:
                request = call.GetConfiguration(key=keys)
            else:
                request = call.GetConfiguration()
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending GetConfiguration: {e}")
            return None

    async def change_configuration(self, key: str, value: str):
        """Send ChangeConfiguration request."""
        try:
            logger.info(f"Sending change configuration to {self.charge_point_id}")
            request = call.ChangeConfiguration(key=key, value=value)
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending ChangeConfiguration: {e}")
            return None

    async def clear_cache(self):
        """Send ClearCache request."""
        try:
            logger.info(f"Sending clear cache to {self.charge_point_id}")
            request = call.ClearCache()
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending ClearCache: {e}")
            return None

    async def send_local_list(self, list_version: int, update_type: str, local_authorization_list: list = None):
        """Send SendLocalList request."""
        try:
            logger.info(f"Sending local list to {self.charge_point_id}")
            request = call.SendLocalList(
                list_version=int(list_version),
                update_type=update_type,
                local_authorization_list=local_authorization_list or []
            )
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending SendLocalList: {e}")
            return None

    async def clear_local_list(self):
        """Clear the local authorization list on the charge point."""
        try:
            logger.info(f"Clearing local list for {self.charge_point_id}")
            # Clear local list by sending an empty list with version 0
            request = call.SendLocalList(
                list_version=0,
                update_type="Full",
                local_authorization_list=[]
            )
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error clearing local list: {e}")
            return None

    async def get_local_list_version(self):
        """Get the current local list version from the charge point."""
        try:
            logger.info(f"Getting local list version for {self.charge_point_id}")
            request = call.GetLocalListVersion()
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error getting local list version: {e}")
            return None

    async def data_transfer(self, vendor_id: str, message_id: str = None, data: str = None):
        """Send DataTransfer request."""
        try:
            logger.info(f"Sending data transfer to {self.charge_point_id}")
            # Only include optional parameters if they are provided
            request_params = {"vendor_id": vendor_id}
            if message_id is not None:
                request_params["message_id"] = message_id
            if data is not None:
                request_params["data"] = data
            
            request = call.DataTransfer(**request_params)
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending DataTransfer: {e}")
            return None

    async def reset(self, type: str):
        """Send Reset request to charger."""
        try:
            from ocpp.v16.enums import ResetType
            
            # Validate reset type
            if type.lower() == "hard":
                reset_type = ResetType.hard
            elif type.lower() == "soft":
                reset_type = ResetType.soft
            else:
                raise ValueError("Reset type must be 'hard' or 'soft'")
            
            charger_store.add_log(self.charge_point_id, f"Sending Reset request: type={type}")
            logger.info(f"Sending {type} reset to {self.charge_point_id}")
            request = call.Reset(type=reset_type)
            return await self.call(request)
        except Exception as e:
            logger.error(f"Error sending Reset: {e}")
            return None

    async def trigger_message(self, requested_message: str, connector_id: int = None):
        """Send TriggerMessage request to charger."""
        try:
            # Validate requested message type
            valid_messages = [
                "BootNotification", "DiagnosticsStatusNotification", "FirmwareStatusNotification",
                "Heartbeat", "MeterValues", "StatusNotification"
            ]
            
            if requested_message not in valid_messages:
                raise ValueError(f"Invalid message type. Must be one of: {', '.join(valid_messages)}")
            
            # Add log entry
            log_msg = f"Sending TriggerMessage request: requested_message={requested_message}"
            if connector_id is not None:
                log_msg += f", connector_id={connector_id}"
            charger_store.add_log(self.charge_point_id, log_msg)
            
            logger.info(f"Sending TriggerMessage to {self.charge_point_id}: {requested_message}")
            
            # Create TriggerMessage request - only include connector_id if provided
            request_params = {"requested_message": requested_message}
            if connector_id is not None:
                request_params["connector_id"] = int(connector_id)
            
            request = call.TriggerMessage(**request_params)
            
            response = await self.call(request)
            
            # Add log entry for response
            charger_store.add_log(self.charge_point_id, f"TriggerMessage response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending TriggerMessage to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"TriggerMessage failed: {str(e)}")
            return None

    # === CHANGE AVAILABILITY FUNCTIONALITY ===
    async def change_availability(self, connector_id: int, availability_type: str):
        """Send ChangeAvailability request to charger."""
        try:
            logger.info(f"[DEBUG] change_availability called with: connector_id={connector_id}, availability_type={availability_type}")
            
            # Validate availability type
            if availability_type.lower() == "operative":
                avail_type = AvailabilityType.operative
                logger.info(f"[DEBUG] Set avail_type to AvailabilityType.operative: {avail_type}")
            elif availability_type.lower() == "inoperative":
                avail_type = AvailabilityType.inoperative
                logger.info(f"[DEBUG] Set avail_type to AvailabilityType.inoperative: {avail_type}")
            else:
                logger.error(f"[DEBUG] Invalid availability type: {availability_type}")
                raise ValueError("Availability type must be 'Operative' or 'Inoperative'")
            
            charger_store.add_log(self.charge_point_id, f"Sending ChangeAvailability request: connector_id={connector_id}, type={availability_type}")
            logger.info(f"Sending ChangeAvailability to {self.charge_point_id}: connector {connector_id} -> {availability_type}")
            
            logger.info(f"[DEBUG] Creating call.ChangeAvailability with connector_id={int(connector_id)}, type={avail_type}")
            request = call.ChangeAvailability(connector_id=int(connector_id), type=avail_type)
            logger.info(f"[DEBUG] Request created successfully: {request}")
            
            logger.info(f"[DEBUG] Calling self.call(request)...")
            response = await self.call(request)
            logger.info(f"[DEBUG] Response received: {response}")
            
            # Log response
            charger_store.add_log(self.charge_point_id, f"ChangeAvailability response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"[DEBUG] Exception in change_availability: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[DEBUG] Traceback: {traceback.format_exc()}")
            charger_store.add_log(self.charge_point_id, f"ChangeAvailability failed: {str(e)}")
            return None

    # === RESERVATION FUNCTIONALITY ===
    async def reserve_now(self, connector_id: int, expiry_date: str, id_tag: str, reservation_id: int, parent_id_tag: str = None):
        """Send ReserveNow request to charger."""
        try:
            charger_store.add_log(self.charge_point_id, f"Sending ReserveNow request: connector_id={connector_id}, reservation_id={reservation_id}, id_tag={id_tag}, expiry_date={expiry_date}")
            logger.info(f"Sending ReserveNow to {self.charge_point_id}: connector {connector_id} for {id_tag}")
            
            request_params = {
                "connector_id": int(connector_id),
                "expiry_date": expiry_date,
                "id_tag": id_tag,
                "reservation_id": int(reservation_id)
            }
            
            # Only include parent_id_tag if it's provided and not None/empty
            if parent_id_tag:
                request_params["parent_id_tag"] = parent_id_tag
            
            request = call.ReserveNow(**request_params)
            response = await self.call(request)
            
            # Log response and store reservation if accepted
            charger_store.add_log(self.charge_point_id, f"ReserveNow response: {response}")
            
            if hasattr(response, 'status') and response.status == "Accepted":
                # Store reservation in charger store
                charger_store.add_reservation(self.charge_point_id, reservation_id, connector_id, id_tag, expiry_date, parent_id_tag)
                logger.info(f"✅ Reservation {reservation_id} created for {self.charge_point_id}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending ReserveNow to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"ReserveNow failed: {str(e)}")
            return None

    async def cancel_reservation(self, reservation_id: int):
        """Send CancelReservation request to charger."""
        try:
            charger_store.add_log(self.charge_point_id, f"Sending CancelReservation request: reservation_id={reservation_id}")
            logger.info(f"Sending CancelReservation to {self.charge_point_id}: reservation {reservation_id}")
            
            request = call.CancelReservation(reservation_id=int(reservation_id))
            response = await self.call(request)
            
            # Log response and remove reservation if accepted
            charger_store.add_log(self.charge_point_id, f"CancelReservation response: {response}")
            
            if hasattr(response, 'status') and response.status == "Accepted":
                # Remove reservation from charger store
                charger_store.remove_reservation(self.charge_point_id, reservation_id)
                logger.info(f"✅ Reservation {reservation_id} cancelled for {self.charge_point_id}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending CancelReservation to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"CancelReservation failed: {str(e)}")
            return None

    # === SMART CHARGING FUNCTIONALITY ===
    async def set_charging_profile(self, connector_id: int, charging_profile: dict):
        """Send SetChargingProfile request to charger."""
        try:
            charger_store.add_log(self.charge_point_id, f"Sending SetChargingProfile request: connector_id={connector_id}, profile_id={charging_profile.get('chargingProfileId')}")
            logger.info(f"Sending SetChargingProfile to {self.charge_point_id}: connector {connector_id}")
            
            request = call.SetChargingProfile(
                connector_id=int(connector_id),
                cs_charging_profiles=charging_profile
            )
            response = await self.call(request)
            
            # Log response and store profile if accepted
            charger_store.add_log(self.charge_point_id, f"SetChargingProfile response: {response}")
            
            if hasattr(response, 'status') and response.status == "Accepted":
                # Store charging profile in charger store
                charger_store.add_charging_profile(self.charge_point_id, connector_id, charging_profile)
                logger.info(f"✅ Charging profile {charging_profile.get('chargingProfileId')} set for {self.charge_point_id}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending SetChargingProfile to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"SetChargingProfile failed: {str(e)}")
            return None

    async def clear_charging_profile(self, profile_id: int = None, connector_id: int = None, charging_profile_purpose: str = None, stack_level: int = None):
        """Send ClearChargingProfile request to charger."""
        try:
            log_msg = f"Sending ClearChargingProfile request"
            request_params = {}
            
            # Only include parameters if they are provided and not None
            if profile_id is not None:
                request_params["id"] = int(profile_id)
                log_msg += f": profile_id={profile_id}"
            if connector_id is not None:
                request_params["connector_id"] = int(connector_id)
                log_msg += f", connector_id={connector_id}"
            if charging_profile_purpose:
                request_params["charging_profile_purpose"] = charging_profile_purpose
                log_msg += f", purpose={charging_profile_purpose}"
            if stack_level is not None:
                request_params["stack_level"] = int(stack_level)
                log_msg += f", stack_level={stack_level}"
            
            charger_store.add_log(self.charge_point_id, log_msg)
            logger.info(f"Sending ClearChargingProfile to {self.charge_point_id}")
            
            request = call.ClearChargingProfile(**request_params)
            response = await self.call(request)
            
            # Log response and clear profiles if accepted
            charger_store.add_log(self.charge_point_id, f"ClearChargingProfile response: {response}")
            
            if hasattr(response, 'status') and response.status == "Accepted":
                # Clear charging profiles from charger store
                charger_store.clear_charging_profiles(self.charge_point_id, profile_id, connector_id, charging_profile_purpose, stack_level)
                logger.info(f"✅ Charging profiles cleared for {self.charge_point_id}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending ClearChargingProfile to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"ClearChargingProfile failed: {str(e)}")
            return None

    async def get_composite_schedule(self, connector_id: int, duration: int, charging_rate_unit: str = None):
        """Send GetCompositeSchedule request to charger."""
        try:
            logger.info(f"Sending GetCompositeSchedule to {self.charge_point_id}: connector_id={connector_id}, duration={duration}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"Sending GetCompositeSchedule request: connector_id={connector_id}, duration={duration}")
            
            # Create request parameters
            request_params = {
                "connector_id": int(connector_id),
                "duration": int(duration)
            }
            
            if charging_rate_unit:
                request_params["charging_rate_unit"] = charging_rate_unit
            
            request = call.GetCompositeSchedule(**request_params)
            response = await self.call(request)
            
            # Add log entry for response
            charger_store.add_log(self.charge_point_id, f"GetCompositeSchedule response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending GetCompositeSchedule to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"GetCompositeSchedule failed: {str(e)}")
            return None

    async def update_firmware(self, location: str, retrieve_date: str, retries: int = None, retry_interval: int = None):
        """Send UpdateFirmware request to charger."""
        try:
            logger.info(f"Sending UpdateFirmware to {self.charge_point_id}: location={location}, retrieve_date={retrieve_date}")
            
            # Add log entry
            log_msg = f"Sending UpdateFirmware request: location={location}, retrieve_date={retrieve_date}"
            if retries is not None:
                log_msg += f", retries={retries}"
            if retry_interval is not None:
                log_msg += f", retry_interval={retry_interval}"
            charger_store.add_log(self.charge_point_id, log_msg)
            
            # Create request parameters
            request_params = {
                "location": location,
                "retrieve_date": retrieve_date
            }
            
            if retries is not None:
                request_params["retries"] = int(retries)
            if retry_interval is not None:
                request_params["retry_interval"] = int(retry_interval)
            
            request = call.UpdateFirmware(**request_params)
            response = await self.call(request)
            
            # Add log entry for response
            charger_store.add_log(self.charge_point_id, f"UpdateFirmware response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending UpdateFirmware to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"UpdateFirmware failed: {str(e)}")
            return None

    async def get_diagnostics(self, location: str, retries: int = None, retry_interval: int = None, start_time: str = None, stop_time: str = None):
        """Send GetDiagnostics request to charger."""
        try:
            logger.info(f"Sending GetDiagnostics to {self.charge_point_id}: location={location}")
            
            # Add log entry
            log_msg = f"Sending GetDiagnostics request: location={location}"
            if retries is not None:
                log_msg += f", retries={retries}"
            if retry_interval is not None:
                log_msg += f", retry_interval={retry_interval}"
            if start_time:
                log_msg += f", start_time={start_time}"
            if stop_time:
                log_msg += f", stop_time={stop_time}"
            charger_store.add_log(self.charge_point_id, log_msg)
            
            # Create request parameters
            request_params = {
                "location": location
            }
            
            if retries is not None:
                request_params["retries"] = int(retries)
            if retry_interval is not None:
                request_params["retry_interval"] = int(retry_interval)
            if start_time:
                request_params["start_time"] = start_time
            if stop_time:
                request_params["stop_time"] = stop_time
            
            request = call.GetDiagnostics(**request_params)
            response = await self.call(request)
            
            # Add log entry for response
            charger_store.add_log(self.charge_point_id, f"GetDiagnostics response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending GetDiagnostics to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"GetDiagnostics failed: {str(e)}")
            return None

    async def unlock_connector(self, connector_id: int):
        """Send UnlockConnector request to charger."""
        try:
            logger.info(f"Sending UnlockConnector to {self.charge_point_id}: connector_id={connector_id}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"Sending UnlockConnector request: connector_id={connector_id}")
            
            request = call.UnlockConnector(connector_id=int(connector_id))
            response = await self.call(request)
            
            # Add log entry for response
            status = getattr(response, 'status', 'Unknown')
            charger_store.add_log(self.charge_point_id, f"UnlockConnector response: status={status}")
            
            logger.info(f"✅ UnlockConnector response from {self.charge_point_id}: status={status}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending UnlockConnector to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"UnlockConnector failed: {str(e)}")
            return None

    async def send_raw_message(self, raw_message: str):
        """Send raw WebSocket message without any validation or processing."""
        try:
            logger.info(f"Sending raw message to {self.charge_point_id}: {raw_message}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"📤 Raw WebSocket Message (No Validation): {raw_message}")
            
            # Validate that it's valid JSON (but don't validate OCPP structure)
            try:
                import json
                json.loads(raw_message)  # Just check if it's valid JSON
                charger_store.add_log(self.charge_point_id, "✅ Raw message is valid JSON")
            except json.JSONDecodeError as json_error:
                charger_store.add_log(self.charge_point_id, f"⚠️ Warning: Raw message is not valid JSON: {json_error}")
                logger.warning(f"Raw message is not valid JSON: {json_error}")
            
            # Send the raw message directly through the WebSocket connection
            await self._connection.send(raw_message)
            
            logger.info(f"✅ Raw message sent successfully to {self.charge_point_id}")
            charger_store.add_log(self.charge_point_id, "✅ Raw WebSocket message sent successfully (bypassed all OCPP validation)")
            
            return {"status": "success", "message": "Raw message sent successfully"}
        except Exception as e:
            error_msg = f"Error sending raw message: {e}"
            logger.error(error_msg)
            charger_store.add_log(self.charge_point_id, f"❌ Raw message failed: {error_msg}")
            raise Exception(error_msg)

    # === JIO_BP DATA TRANSFER FUNCTIONALITY ===
    async def _send_jio_bp_data_transfer_after_delay(self):
        """Send Jio_BP data transfer packets after 500ms delay following StartTransaction response."""
        try:
            # Wait 500ms after StartTransaction response
            await asyncio.sleep(0.5)
            
            # Then send the configured Jio_BP packets
            await self._send_jio_bp_data_transfer_if_configured()
            
        except Exception as e:
            logger.error(f"Error in delayed Jio_BP data transfer: {e}")
            charger_store.add_log(self.charge_point_id, f"Delayed Jio_BP data transfer failed: {e}")

    async def _send_jio_bp_data_transfer_if_configured(self):
        """Send Jio_BP data transfer packets if configured for this charger."""
        try:
            # Get Jio_BP settings for this charger
            jio_bp_settings = charger_store.get_jio_bp_settings(self.charge_point_id)
            
            if not jio_bp_settings:
                logger.debug(f"No Jio_BP settings configured for {self.charge_point_id}")
                return
            
            # Get the current active transaction to use its ID
            active_transaction = charger_store.get_active_transaction(self.charge_point_id)
            if not active_transaction:
                logger.warning(f"No active transaction found for Jio_BP data transfer on {self.charge_point_id}")
                return
            
            transaction_id = active_transaction['transaction_id']
            
            # Send configured Jio_BP data transfer packets
            if jio_bp_settings.get('stop_energy_enabled', False):
                energy_value = jio_bp_settings.get('stop_energy_value', 10)
                data = f"{transaction_id}_{energy_value}"
                
                await self._send_jio_bp_packet("Stop_Energy", data)
                logger.info(f"Sent Jio_BP Stop_Energy packet for transaction {transaction_id}: {data}")
            
            if jio_bp_settings.get('stop_time_enabled', False):
                time_value = jio_bp_settings.get('stop_time_value', 10)
                data = f"{transaction_id}_{time_value}"
                
                await self._send_jio_bp_packet("Stop_Time", data)
                logger.info(f"Sent Jio_BP Stop_Time packet for transaction {transaction_id}: {data}")
                
        except Exception as e:
            logger.error(f"Error sending Jio_BP data transfer packets: {e}")
            charger_store.add_log(self.charge_point_id, f"Jio_BP data transfer failed: {e}")

    async def _send_jio_bp_packet(self, message_id: str, data: str):
        """Send a specific Jio_BP data transfer packet."""
        try:
            request_params = {"vendor_id": "Test_Server"}
            
            # Only include optional parameters if they are provided
            if message_id is not None:
                request_params["message_id"] = message_id
            if data is not None:
                request_params["data"] = data
                
            request = call.DataTransfer(**request_params)
            response = await self.call(request)
            
            charger_store.add_log(self.charge_point_id, f"Jio_BP DataTransfer sent: messageId={message_id}, data={data}, status={response.status}")
            
            return response.status == DataTransferStatus.accepted
        except Exception as e:
            logger.error(f"Error sending Jio_BP packet {message_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"Jio_BP packet {message_id} failed: {e}")
            return False

    async def _send_msil_data_transfer_after_delay(self):
        """Send MSIL data transfer packets after 500ms delay following StartTransaction response."""
        try:
            # Wait 500ms after StartTransaction response
            await asyncio.sleep(0.5)
            
            # Then send the configured MSIL packets
            await self._send_msil_data_transfer_if_configured()
            
        except Exception as e:
            logger.error(f"Error in delayed MSIL data transfer: {e}")
            charger_store.add_log(self.charge_point_id, f"Delayed MSIL data transfer failed: {e}")

    async def _send_msil_data_transfer_if_configured(self):
        """Send MSIL data transfer packets if configured for this charger."""
        try:
            # Get MSIL settings for this charger
            msil_settings = charger_store.get_msil_settings(self.charge_point_id)
            
            if not msil_settings:
                logger.debug(f"No MSIL settings configured for {self.charge_point_id}")
                return
            
            # Get the current active transaction to use its ID
            active_transaction = charger_store.get_active_transaction(self.charge_point_id)
            if not active_transaction:
                logger.warning(f"No active transaction found for MSIL data transfer on {self.charge_point_id}")
                return
            
            transaction_id = active_transaction['transaction_id']
            
            # Send configured MSIL data transfer packets
            if msil_settings.get('auto_stop_enabled', False):
                energy_value = msil_settings.get('stop_energy_value', 1000)
                
                # MSIL data is in object form
                data = {
                    "transactionId": transaction_id,
                    "parameter": "Stop_Energy",
                    "value": int(energy_value)
                }
                
                await self._send_msil_packet("AutoStop", data)
                logger.info(f"Sent MSIL AutoStop packet for transaction {transaction_id}: {data}")
                
        except Exception as e:
            logger.error(f"Error sending MSIL data transfer packets: {e}")
            charger_store.add_log(self.charge_point_id, f"MSIL data transfer failed: {e}")

    async def _send_msil_packet(self, message_id: str, data: dict):
        """Send a specific MSIL data transfer packet with JSON object data (OCPP violation)."""
        try:
            import json
            import uuid
            
            # Log the OCPP violation but proceed as per customer requirement
            charger_store.add_log(self.charge_point_id, f"⚠️ OCCP VIOLATION WARNING ⚠️ MSIL DataTransfer: data field sent as OBJECT instead of STRING (Customer Special Requirement)")
            charger_store.add_log(self.charge_point_id, f"MSIL Packet: vendorId=MSIL, messageId={message_id}, data={json.dumps(data)} [VIOLATES OCPP 1.6 STANDARD]")
            
            # Generate unique message ID for this request
            unique_id = str(uuid.uuid4())
            
            # Create MSIL DataTransfer frame manually with object data (OCPP violation)
            msil_frame = [
                2,  # MessageType: CALL
                unique_id,
                "DataTransfer",
                {
                    "vendorId": "MSIL",
                    "messageId": message_id,
                    "data": data  # Send as actual JSON object, not string (OCPP violation)
                }
            ]
            
            # Convert frame to JSON string for WebSocket transmission
            frame_json = json.dumps(msil_frame)
            
            # Log the outbound frame
            charger_store.add_log(self.charge_point_id, f"📤 WebSocket CMS→Charger Frame: {frame_json}")
            
            try:
                # Send raw WebSocket frame
                await self._connection.send(frame_json)
                
                charger_store.add_log(self.charge_point_id, f"✅ MSIL DataTransfer with OBJECT data sent successfully: messageId={message_id}")
                charger_store.add_log(self.charge_point_id, f"📤 MSIL packet transmitted: vendorId=MSIL, messageId={message_id}, data={json.dumps(data)} [OBJECT TYPE]")
                logger.info(f"MSIL packet sent to {self.charge_point_id} with intentional OCPP violation (object data)")
                
                # Note: We can't easily wait for response since we're bypassing the OCPP call mechanism
                # The charger may reject this with "TypeConstraintViolationError" which is expected
                return True  # Consider successful since packet was transmitted
                
            except Exception as send_error:
                logger.error(f"Error sending raw MSIL WebSocket frame: {send_error}")
                charger_store.add_log(self.charge_point_id, f"❌ Raw MSIL frame transmission failed: {send_error}")
                
                # Fallback: Try normal DataTransfer (will convert object to string)
                try:
                    request_params = {
                        "vendor_id": "MSIL",
                        "message_id": message_id,
                        "data": data  # This will be auto-converted to string by OCPP library
                    }
                    request = call.DataTransfer(**request_params)
                    response = await self.call(request)
                    
                    charger_store.add_log(self.charge_point_id, f"📝 Fallback: MSIL sent as string via OCPP library: status={response.status}")
                    return response.status == DataTransferStatus.accepted
                    
                except Exception as fallback_error:
                    if "TypeConstraintViolationError" in str(fallback_error):
                        charger_store.add_log(self.charge_point_id, f"⚠️ MSIL DataTransfer caused expected TypeConstraintViolationError (OCPP violation)")
                        return True  # Consider this successful as it's intentional
                    else:
                        raise fallback_error
                
        except Exception as e:
            logger.error(f"Error sending MSIL packet {message_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"❌ MSIL packet {message_id} failed: {e}")
            return False

    async def _send_cz_data_transfer_after_delay(self):
        """Send CZ data transfer packets after 500ms delay following StartTransaction response."""
        try:
            # Wait 500ms after StartTransaction response
            await asyncio.sleep(0.5)
            
            # Then send the configured CZ packets
            await self._send_cz_data_transfer_if_configured()
            
        except Exception as e:
            logger.error(f"Error in delayed CZ data transfer: {e}")
            charger_store.add_log(self.charge_point_id, f"Delayed CZ data transfer failed: {e}")

    async def _send_cz_data_transfer_if_configured(self):
        """Send CZ data transfer packets if configured for this charger."""
        try:
            # Get CZ settings for this charger
            cz_settings = charger_store.get_cz_settings(self.charge_point_id)
            
            if not cz_settings:
                logger.debug(f"No CZ settings configured for {self.charge_point_id}")
                return
            
            # Get the current active transaction to use its ID
            active_transaction = charger_store.get_active_transaction(self.charge_point_id)
            if not active_transaction:
                logger.warning(f"No active transaction found for CZ data transfer on {self.charge_point_id}")
                return
            
            transaction_id = active_transaction['transaction_id']
            
            # Send configured CZ data transfer packets
            if cz_settings.get('auto_stop_enabled', False):
                energy_value = cz_settings.get('stop_energy_value', 2000)
                
                # CZ data is in string form - create clean JSON string
                import json
                data_obj = {
                    "transactionId": transaction_id,
                    "parameter": "Stop_Energy",
                    "value": int(energy_value)
                }
                data = json.dumps(data_obj)
                
                await self._send_cz_packet("AutoStop", data)
                logger.info(f"Sent CZ AutoStop packet for transaction {transaction_id}: {data}")
                
        except Exception as e:
            logger.error(f"Error sending CZ data transfer packets: {e}")
            charger_store.add_log(self.charge_point_id, f"CZ data transfer failed: {e}")

    async def _send_cz_packet(self, message_id: str, data: str):
        """Send a specific CZ data transfer packet."""
        try:
            request_params = {"vendor_id": "CZ"}
            
            # Only include optional parameters if they are provided
            if message_id is not None:
                request_params["message_id"] = message_id
            if data is not None:
                # For CZ, data is sent as a string
                request_params["data"] = data
                
            request = call.DataTransfer(**request_params)
            response = await self.call(request)
            
            charger_store.add_log(self.charge_point_id, f"CZ DataTransfer sent: messageId={message_id}, data={data}, status={response.status}")
            
            return response.status == DataTransferStatus.accepted
        except Exception as e:
            logger.error(f"Error sending CZ packet {message_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"CZ packet {message_id} failed: {e}")
            return False 
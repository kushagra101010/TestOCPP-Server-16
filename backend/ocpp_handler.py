import logging
import json
from datetime import datetime
from ocpp.routing import on
from ocpp.v16.enums import (
    RegistrationStatus, AuthorizationStatus, ChargePointStatus,
    RemoteStartStopStatus, DataTransferStatus
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
            
            return call_result.StartTransaction(
                transaction_id=transaction_id,
                id_tag_info=IdTagInfo(
                    status=AuthorizationStatus.accepted
                )
            )
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
            logger.info(f"Data transfer from {self.charge_point_id}: vendor_id={vendor_id}")
            
            # Add log entry
            charger_store.add_log(self.charge_point_id, f"DataTransfer: vendor_id={vendor_id}")
            
            return call_result.DataTransfer(
                status=DataTransferStatus.accepted
            )
        except Exception as e:
            logger.error(f"Error in DataTransfer handler: {e}")
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
            # Ensure connector_id is an integer and handle None case
            if connector_id is None:
                connector_id = 1  # Default to connector 1
            connector_id = int(connector_id)  # Ensure it's an integer
            
            request = call.RemoteStartTransaction(
                connector_id=connector_id,
                id_tag=id_tag
            )
            response = await self.call(request)
            
            charger_store.add_log(self.charge_point_id, f"RemoteStartTransaction sent: connector={connector_id}, id_tag={id_tag}, status={response.status}")
            
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
            request = call.GetConfiguration(key=keys)
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
            request = call.DataTransfer(
                vendor_id=vendor_id,
                message_id=message_id,
                data=data
            )
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
            
            # Create TriggerMessage request - use string directly as OCPP 2.0.0 library expects
            if connector_id is not None:
                request = call.TriggerMessage(requested_message=requested_message, connector_id=int(connector_id))
            else:
                request = call.TriggerMessage(requested_message=requested_message)
            
            response = await self.call(request)
            
            # Add log entry for response
            charger_store.add_log(self.charge_point_id, f"TriggerMessage response: {response}")
            
            return response
        except Exception as e:
            logger.error(f"Error sending TriggerMessage to {self.charge_point_id}: {e}")
            charger_store.add_log(self.charge_point_id, f"TriggerMessage failed: {str(e)}")
            return None 
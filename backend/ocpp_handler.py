import logging
import json
from datetime import datetime
from ocpp.routing import on
from ocpp.v16.enums import (
    RegistrationStatus, AuthorizationStatus, ChargePointStatus,
    RemoteStartStopStatus, DataTransferStatus, Action
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
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.status = ChargePointStatus.available
            db.session.commit()
        logger.info(f"Charger {self.charge_point_id} connected")

    async def on_disconnect(self):
        """Handle charger disconnection."""
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.status = ChargePointStatus.unavailable
            db.session.commit()
        logger.info(f"Charger {self.charge_point_id} disconnected")

    @on(Action.BootNotification)
    async def on_boot_notification(self, charge_point_model, charge_point_vendor, **kwargs):
        print(f"DEBUG: BootNotification received for {self.charge_point_id}")
        logger.info(f"BootNotification from {self.charge_point_id}: vendor={charge_point_vendor}, model={charge_point_model}")
        
        # Add charger to store
        charger_store.add_charger(self.charge_point_id)
        
        # Add log entry
        print(f"DEBUG: About to add log for BootNotification")
        try:
            charger_store.add_log(self.charge_point_id, f"BootNotification: vendor={charge_point_vendor}, model={charge_point_model}")
            print(f"DEBUG: Successfully called add_log for BootNotification")
        except Exception as e:
            print(f"DEBUG: Error in add_log for BootNotification: {e}")
            import traceback
            traceback.print_exc()
        
        return call_result.BootNotificationPayload(
            current_time=datetime.utcnow().isoformat(),
            interval=30,
            status=RegistrationStatus.accepted
        )

    @on(Action.Authorize)
    async def on_authorize(self, id_tag: str, **kwargs):
        charger_store.add_log(self.charge_point_id, f"Authorize: id_tag={id_tag}")
        logger.info(f"Received authorize request for {id_tag} from {self.charge_point_id}")
        
        # Check if idTag exists in database
        id_tag_record = db.session.query(IdTag).filter_by(id_tag=id_tag).first()
        if id_tag_record:
            status = AuthorizationStatus.accepted
        else:
            status = AuthorizationStatus.invalid
            # Add the invalid tag to database
            id_tag_record = IdTag(id_tag=id_tag, status="Invalid")
            db.session.add(id_tag_record)
            db.session.commit()

        return call_result.AuthorizePayload(
            id_tag_info=IdTagInfo(
                status=status,
                expiry_date=None
            )
        )

    @on(Action.StartTransaction)
    async def on_start_transaction(self, connector_id: int, id_tag: str, meter_start: int, timestamp: str, **kwargs):
        """Handle StartTransaction request."""
        logger.info(f"Received start transaction request from {self.charge_point_id}")
        
        # Generate transaction ID (you might want to implement a better way)
        transaction_id = int(datetime.utcnow().timestamp())
        
        # Update charger status
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.current_transaction = transaction_id
            db.session.commit()

        return call_result.StartTransactionPayload(
            transaction_id=transaction_id,
            id_tag_info=IdTagInfo(
                status=AuthorizationStatus.accepted,
                expiry_date=None
            )
        )

    @on(Action.StopTransaction)
    async def on_stop_transaction(self, transaction_id: int, meter_stop: int, timestamp: str, **kwargs):
        """Handle StopTransaction request."""
        logger.info(f"Received stop transaction request from {self.charge_point_id}")
        
        # Update charger status
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.current_transaction = None
            db.session.commit()

        return call_result.StopTransactionPayload(
            id_tag_info=IdTagInfo(
                status=AuthorizationStatus.accepted,
                expiry_date=None
            )
        )

    @on(Action.Heartbeat)
    async def on_heartbeat(self, **kwargs):
        logger.debug(f"Processing heartbeat for {self.charge_point_id}")
        charger_store.add_log(self.charge_point_id, "Heartbeat received")
        logger.debug(f"Added heartbeat log for {self.charge_point_id}")
        
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.last_heartbeat = datetime.utcnow()
            db.session.commit()
            logger.debug(f"Updated last_heartbeat for {self.charge_point_id}")
            
        return call_result.HeartbeatPayload(
            current_time=datetime.utcnow().isoformat()
        )

    @on(Action.MeterValues)
    async def on_meter_values(self, connector_id: int, meter_value: list, transaction_id: int = None, **kwargs):
        try:
            charger_store.add_log(self.charge_point_id, f"MeterValues: connector={connector_id}, meter_value={meter_value}, transaction_id={transaction_id}")
            charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
            if charger:
                charger.meter_value = meter_value
                db.session.commit()
                
            return call_result.MeterValuesPayload()
        except Exception as e:
            logger.error(f"Error handling MeterValues from {self.charge_point_id}: {e}")
            import traceback
            traceback.print_exc()
            return call_result.MeterValuesPayload()

    @on(Action.StatusNotification)
    async def on_status_notification(self, connector_id: int, error_code: str, status: str, **kwargs):
        charger_store.add_log(self.charge_point_id, f"StatusNotification: connector={connector_id}, error_code={error_code}, status={status}")
        logger.info(f"Status notification from {self.charge_point_id}: connector {connector_id} - {status}")
        
        # Update charger status in database
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            charger.status = status
            db.session.commit()
            
        return call_result.StatusNotificationPayload()

    @on(Action.DataTransfer)
    async def on_data_transfer(self, vendor_id: str, message_id: str = None, data: str = None, **kwargs):
        charger_store.add_log(self.charge_point_id, f"DataTransfer: vendor_id={vendor_id}, message_id={message_id}, data={data}")
        logger.info(f"Data transfer from {self.charge_point_id}: {vendor_id} - {message_id}")
        
        # Store data transfer packet in database
        charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
        if charger:
            if not charger.data_transfer_packets:
                charger.data_transfer_packets = []
            charger.data_transfer_packets.append({
                "vendor_id": vendor_id,
                "message_id": message_id,
                "data": data,
                "timestamp": datetime.utcnow().isoformat()
            })
            db.session.commit()
            
        return call_result.DataTransferPayload(
            status=DataTransferStatus.accepted
        )

    async def remote_start_transaction(self, id_tag: str, connector_id: int = None):
        """Send RemoteStartTransaction request."""
        logger.info(f"Sending remote start transaction to {self.charge_point_id}")
        return await self.call(call.RemoteStartTransactionPayload(
            id_tag=id_tag,
            connector_id=connector_id
        ))

    async def remote_stop_transaction(self, transaction_id: int):
        """Send RemoteStopTransaction request."""
        logger.info(f"Sending remote stop transaction to {self.charge_point_id}")
        return await self.call(call.RemoteStopTransactionPayload(
            transaction_id=transaction_id
        ))

    async def get_configuration(self, keys: list = None):
        """Send GetConfiguration request."""
        logger.info(f"Sending get configuration to {self.charge_point_id}")
        return await self.call(call.GetConfigurationPayload(
            key=keys
        ))

    async def change_configuration(self, key: str, value: str):
        """Send ChangeConfiguration request."""
        logger.info(f"Sending change configuration to {self.charge_point_id}")
        return await self.call(call.ChangeConfigurationPayload(
            key=key,
            value=value
        ))

    async def clear_cache(self):
        """Send ClearCache request."""
        logger.info(f"Sending clear cache to {self.charge_point_id}")
        return await self.call(call.ClearCachePayload())

    async def send_local_list(self, list_version: int, update_type: str, local_authorization_list: list = None):
        """Send SendLocalList request."""
        logger.info(f"Sending local list to {self.charge_point_id}")
        return await self.call(call.SendLocalListPayload(
            list_version=list_version,
            update_type=update_type,
            local_authorization_list=local_authorization_list
        ))

    async def clear_local_list(self):
        """Clear the local authorization list on the charge point."""
        logger.info(f"Clearing local list for {self.charge_point_id}")
        # Clear local list by sending an empty list with version 0
        request = call.SendLocalListPayload(
            list_version=0,
            update_type="Full",
            local_authorization_list=[]
        )
        return await self.call(request)

    async def get_local_list_version(self):
        """Get the current local list version from the charge point."""
        logger.info(f"Getting local list version for {self.charge_point_id}")
        request = call.GetLocalListVersionPayload()
        return await self.call(request)

    async def data_transfer(self, vendor_id: str, message_id: str = None, data: str = None):
        """Send DataTransfer request."""
        logger.info(f"Sending data transfer to {self.charge_point_id}")
        return await self.call(call.DataTransferPayload(
            vendor_id=vendor_id,
            message_id=message_id,
            data=data
        ))

    async def reset(self, type: str):
        """Send Reset request to charger."""
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
        return await self.call(call.ResetPayload(type=reset_type)) 
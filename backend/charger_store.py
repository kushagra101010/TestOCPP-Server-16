import logging
from typing import Dict, List, Optional
from datetime import datetime
import random
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from .database import db, Charger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChargerStore:
    def __init__(self):
        self.transaction_ids: Dict[str, int] = {}  # charge_point_id -> last transaction_id
        self.local_auth_list_version: int = 0

    def add_charger(self, charge_point_id: str) -> None:
        """Add a new charger to the store."""
        existing_charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if not existing_charger:
            new_charger = Charger(
                charge_point_id=charge_point_id,
                status='Available',  # Default status - will be updated by StatusNotification
                last_heartbeat=datetime.utcnow(),
                data_transfer_packets={},
                logs=[]
                # logs_cleared_at will be None initially - no auto-clear for new chargers
            )
            db.session.add(new_charger)
            db.session.commit()
            logger.info(f"Added new charger: {charge_point_id}")
        else:
            # Update existing charger - preserve current status, only update heartbeat and initialize missing fields
            existing_charger.last_heartbeat = datetime.utcnow()
            if existing_charger.logs is None:
                existing_charger.logs = []
            if existing_charger.data_transfer_packets is None:
                existing_charger.data_transfer_packets = {}
            # Don't auto-clear logs on reconnection - preserve connection history
            # Don't change status - preserve the current status from StatusNotification
            db.session.commit()
            logger.info(f"Updated existing charger: {charge_point_id} - reconnected (logs preserved, status preserved: {existing_charger.status})")

    def remove_charger(self, charge_point_id: str) -> None:
        """Remove a charger from the store."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            db.session.delete(charger)
            db.session.commit()
            logger.info(f"Removed charger: {charge_point_id}")

    def add_log(self, charge_point_id: str, message: str) -> None:
        """Add a log message for a charger."""
        logger.debug(f"Adding log for {charge_point_id}: {message}")
        
        try:
            # Use the main database session instead of creating a new one
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                logs = charger.logs or []
                new_log = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'message': message
                }
                logs.append(new_log)
                # Keep only last 1000 logs
                logs = logs[-1000:]
                
                # Explicitly set the logs field to trigger SQLAlchemy change detection
                charger.logs = logs
                
                # Mark the field as modified to ensure SQLAlchemy saves it
                flag_modified(charger, 'logs')
                
                db.session.commit()
                logger.debug(f"Successfully added log for {charge_point_id}. Total logs: {len(charger.logs)}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when trying to add log")
                
        except Exception as e:
            logger.error(f"Error adding log for {charge_point_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()

    def get_logs(self, charge_point_id: str) -> List[dict]:
        """Get logs for a charger, filtered by clear timestamp."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if not charger or not charger.logs:
            return []
        
        # If logs were cleared, only return logs after the clear timestamp
        if charger.logs_cleared_at:
            clear_timestamp = charger.logs_cleared_at.isoformat()
            filtered_logs = []
            for log in charger.logs:
                if log.get('timestamp', '') > clear_timestamp:
                    filtered_logs.append(log)
            return filtered_logs
        
        return charger.logs

    def clear_logs(self, charge_point_id: str) -> None:
        """Clear logs for a charger by setting the clear timestamp."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charger.logs_cleared_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Cleared logs for charger: {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when trying to clear logs")
        except Exception as e:
            logger.error(f"Error clearing logs for {charge_point_id}: {e}")
            db.session.rollback()

    def add_id_tag(self, id_tag: str, status: str = "Accepted", expiry_date=None) -> None:
        """Add or update an idTag."""
        db.save_id_tag(id_tag, status, expiry_date)
        logger.info(f"Added/Updated idTag: {id_tag} with status: {status}")

    def get_id_tags(self) -> Dict[str, dict]:
        """Get all idTags."""
        return db.get_id_tags()

    def generate_transaction_id(self, charge_point_id: str) -> int:
        """Generate a new transaction ID for a charger."""
        transaction_id = random.randint(1, 999999)
        self.transaction_ids[charge_point_id] = transaction_id
        return transaction_id

    def update_connector_status(self, charge_point_id: str, connector_id: int, status: str) -> None:
        """Update the status of a connector for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            # Use the dedicated connector_status field
            connector_data = charger.connector_status or {}
            if not isinstance(connector_data, dict):
                connector_data = {}
            connector_data[f"connector_{connector_id}"] = {
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }
            charger.connector_status = connector_data
            db.session.commit()

    def get_connector_status(self, charge_point_id: str) -> Dict[int, dict]:
        """Get the status of all connectors for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.connector_status and isinstance(charger.connector_status, dict):
            # Extract connector status from connector_status field
            connector_status = {}
            for key, value in charger.connector_status.items():
                if key.startswith("connector_"):
                    connector_id = int(key.replace("connector_", ""))
                    connector_status[connector_id] = value
            return connector_status
        return {}

    def increment_local_auth_list_version(self) -> int:
        """Increment and return the local auth list version."""
        self.local_auth_list_version += 1
        return self.local_auth_list_version

    def get_local_auth_list_version(self) -> int:
        """Get the current local auth list version."""
        return self.local_auth_list_version

    def set_active_transaction(self, charge_point_id: str, transaction_id: int, connector_id: int, id_tag: str) -> None:
        """Store an active transaction for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charger.current_transaction = transaction_id
                # Don't set overall status here - let StatusNotification handle it
                
                # Store transaction details in connector_status for reference
                connector_data = charger.connector_status or {}
                if not isinstance(connector_data, dict):
                    connector_data = {}
                connector_data[f"connector_{connector_id}"] = {
                    'status': 'Preparing',  # Connector starts as preparing
                    'transaction_id': transaction_id,
                    'id_tag': id_tag,
                    'started_at': datetime.utcnow().isoformat()
                }
                charger.connector_status = connector_data
                flag_modified(charger, 'connector_status')
                
                db.session.commit()
                logger.info(f"Set active transaction {transaction_id} for {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when setting active transaction")
        except Exception as e:
            logger.error(f"Error setting active transaction for {charge_point_id}: {e}")
            db.session.rollback()

    def clear_active_transaction(self, charge_point_id: str, transaction_id: int) -> None:
        """Clear an active transaction for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.current_transaction == transaction_id:
                charger.current_transaction = None
                # Don't set overall status here - let StatusNotification handle it
                
                # Clear transaction details from connector_status
                connector_data = charger.connector_status or {}
                if isinstance(connector_data, dict):
                    for key, value in connector_data.items():
                        if key.startswith("connector_") and isinstance(value, dict):
                            if value.get('transaction_id') == transaction_id:
                                value['status'] = 'Finishing'  # Set to finishing until StatusNotification comes
                                value.pop('transaction_id', None)
                                value.pop('id_tag', None)
                                value.pop('started_at', None)
                                value['updated_at'] = datetime.utcnow().isoformat()
                    charger.connector_status = connector_data
                    flag_modified(charger, 'connector_status')
                
                db.session.commit()
                logger.info(f"Cleared active transaction {transaction_id} for {charge_point_id}")
            else:
                logger.warning(f"No matching active transaction {transaction_id} found for {charge_point_id}")
        except Exception as e:
            logger.error(f"Error clearing active transaction for {charge_point_id}: {e}")
            db.session.rollback()

    def get_active_transaction(self, charge_point_id: str) -> Optional[dict]:
        """Get active transaction for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.current_transaction:
            # Find transaction details from connector_status
            connector_data = charger.connector_status or {}
            transaction_details = None
            
            if isinstance(connector_data, dict):
                for key, value in connector_data.items():
                    if key.startswith("connector_") and isinstance(value, dict):
                        if value.get('transaction_id') == charger.current_transaction:
                            transaction_details = value
                            break
            
            return {
                'transaction_id': charger.current_transaction,
                'status': charger.status,
                'started_at': transaction_details.get('started_at') if transaction_details else None,
                'id_tag': transaction_details.get('id_tag') if transaction_details else None,
                'connector_id': int(key.replace('connector_', '')) if transaction_details and key.startswith('connector_') else 1
            }
        return None

    def update_charger_status(self, charge_point_id: str, status: str) -> None:
        """Update the overall status of a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charger.status = status
                charger.last_heartbeat = datetime.utcnow()
                db.session.commit()
                logger.debug(f"Updated charger {charge_point_id} status to {status}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when updating status")
        except Exception as e:
            logger.error(f"Error updating charger status for {charge_point_id}: {e}")
            db.session.rollback()

# Create a global instance
charger_store = ChargerStore() 
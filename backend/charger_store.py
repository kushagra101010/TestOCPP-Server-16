import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
import random
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from .database import db, Charger, SessionLocal

if TYPE_CHECKING:
    from .database import Charger

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

    def get_charger(self, charge_point_id: str) -> Optional['Charger']:
        """Get a charger by its charge point ID."""
        return db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()

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
                # Keep only last 5000 logs (increased from 1000)
                logs = logs[-5000:]
                
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
            if charger:
                charger.current_transaction = None
                # Don't change overall status here - let StatusNotification handle it
                
                # Find and clear transaction details from connector_status
                connector_data = charger.connector_status or {}
                if isinstance(connector_data, dict):
                    for key, value in list(connector_data.items()):
                        if key.startswith("connector_") and isinstance(value, dict):
                            if value.get('transaction_id') == transaction_id:
                                # Clear transaction details but keep connector status
                                value.pop('transaction_id', None)
                                value.pop('id_tag', None)
                                value.pop('started_at', None)
                                break
                
                charger.connector_status = connector_data
                flag_modified(charger, 'connector_status')
                
                db.session.commit()
                logger.info(f"Cleared active transaction {transaction_id} for {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when clearing active transaction")
        except Exception as e:
            logger.error(f"Error clearing active transaction for {charge_point_id}: {e}")
            db.session.rollback()

    def get_active_transaction(self, charge_point_id: str) -> Optional[dict]:
        """Get the active transaction for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.current_transaction:
            # Get transaction details from connector_status
            connector_data = charger.connector_status or {}
            if isinstance(connector_data, dict):
                for key, value in connector_data.items():
                    if key.startswith("connector_") and isinstance(value, dict):
                        if value.get('transaction_id') == charger.current_transaction:
                            # Use the overall charger status instead of outdated connector status
                            # The charger.status is updated by StatusNotification and reflects current state
                            current_status = charger.status if charger.status else value.get('status')
                            return {
                                'transaction_id': charger.current_transaction,
                                'connector_id': int(key.replace("connector_", "")),
                                'id_tag': value.get('id_tag'),
                                'started_at': value.get('started_at'),
                                'status': current_status
                            }
            
            # Fallback if no detailed info found - use overall charger status
            return {
                'transaction_id': charger.current_transaction,
                'connector_id': 1,  # Default
                'id_tag': None,
                'started_at': None,
                'status': charger.status if charger.status else None
            }
        return None

    def update_charger_status(self, charge_point_id: str, status: str) -> None:
        """Update the status of a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            charger.status = status
            db.session.commit()

    # === RESERVATION FUNCTIONALITY ===
    def add_reservation(self, charge_point_id: str, reservation_id: int, connector_id: int, id_tag: str, expiry_date: str, parent_id_tag: str = None) -> None:
        """Store a reservation for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                reservations = charger.reservations or {}
                if not isinstance(reservations, dict):
                    reservations = {}
                
                reservations[str(reservation_id)] = {
                    'reservation_id': reservation_id,
                    'connector_id': connector_id,
                    'id_tag': id_tag,
                    'expiry_date': expiry_date,
                    'parent_id_tag': parent_id_tag,
                    'created_at': datetime.utcnow().isoformat(),
                    'status': 'active'
                }
                
                charger.reservations = reservations
                flag_modified(charger, 'reservations')
                db.session.commit()
                logger.info(f"Added reservation {reservation_id} for {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when adding reservation")
        except Exception as e:
            logger.error(f"Error adding reservation for {charge_point_id}: {e}")
            db.session.rollback()

    def remove_reservation(self, charge_point_id: str, reservation_id: int) -> None:
        """Remove a reservation for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.reservations:
                reservations = charger.reservations or {}
                if isinstance(reservations, dict) and str(reservation_id) in reservations:
                    del reservations[str(reservation_id)]
                    charger.reservations = reservations
                    flag_modified(charger, 'reservations')
                    db.session.commit()
                    logger.info(f"Removed reservation {reservation_id} for {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} or reservation {reservation_id} not found when removing reservation")
        except Exception as e:
            logger.error(f"Error removing reservation for {charge_point_id}: {e}")
            db.session.rollback()

    def get_reservations(self, charge_point_id: str) -> Dict[str, dict]:
        """Get all reservations for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.reservations and isinstance(charger.reservations, dict):
            # Clean up expired reservations
            current_time = datetime.utcnow()
            active_reservations = {}
            
            for res_id, reservation in charger.reservations.items():
                try:
                    expiry_date = datetime.fromisoformat(reservation['expiry_date'].replace('Z', '+00:00'))
                    if expiry_date > current_time:
                        active_reservations[res_id] = reservation
                except Exception as e:
                    logger.warning(f"Error parsing expiry date for reservation {res_id}: {e}")
                    # Keep reservation if we can't parse expiry date
                    active_reservations[res_id] = reservation
            
            # Update database if reservations were cleaned up
            if len(active_reservations) != len(charger.reservations):
                charger.reservations = active_reservations
                flag_modified(charger, 'reservations')
                db.session.commit()
            
            return active_reservations
        return {}

    # === CHARGING PROFILE FUNCTIONALITY ===
    def add_charging_profile(self, charge_point_id: str, connector_id: int, charging_profile: dict) -> None:
        """Store a charging profile for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charging_profiles = charger.charging_profiles or {}
                if not isinstance(charging_profiles, dict):
                    charging_profiles = {}
                
                # Handle both snake_case (from API) and camelCase (from OCPP) field names
                profile_id = charging_profile.get('charging_profile_id') or charging_profile.get('chargingProfileId')
                connector_key = f"connector_{connector_id}"
                
                if connector_key not in charging_profiles:
                    charging_profiles[connector_key] = {}
                
                charging_profiles[connector_key][str(profile_id)] = {
                    **charging_profile,
                    'created_at': datetime.utcnow().isoformat(),
                    'connector_id': connector_id
                }
                
                charger.charging_profiles = charging_profiles
                flag_modified(charger, 'charging_profiles')
                db.session.commit()
                logger.info(f"Added charging profile {profile_id} for {charge_point_id} connector {connector_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when adding charging profile")
        except Exception as e:
            logger.error(f"Error adding charging profile for {charge_point_id}: {e}")
            db.session.rollback()

    def clear_charging_profiles(self, charge_point_id: str, profile_id: int = None, connector_id: int = None, charging_profile_purpose: str = None, stack_level: int = None) -> None:
        """Clear charging profiles for a charger based on criteria."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.charging_profiles:
                charging_profiles = charger.charging_profiles or {}
                if not isinstance(charging_profiles, dict):
                    return
                
                profiles_to_remove = []
                
                for connector_key, connector_profiles in charging_profiles.items():
                    if connector_id is not None and connector_key != f"connector_{connector_id}":
                        continue
                    
                    if isinstance(connector_profiles, dict):
                        for prof_id, profile in list(connector_profiles.items()):
                            should_remove = True
                            
                            # Check all criteria - handle both snake_case and camelCase field names
                            if profile_id is not None:
                                stored_profile_id = profile.get('charging_profile_id') or profile.get('chargingProfileId')
                                if stored_profile_id != profile_id:
                                    should_remove = False
                            if charging_profile_purpose:
                                stored_purpose = profile.get('charging_profile_purpose') or profile.get('chargingProfilePurpose')
                                if stored_purpose != charging_profile_purpose:
                                    should_remove = False
                            if stack_level is not None:
                                stored_stack_level = profile.get('stack_level') or profile.get('stackLevel')
                                if stored_stack_level != stack_level:
                                    should_remove = False
                            
                            if should_remove:
                                profiles_to_remove.append((connector_key, prof_id))
                
                # Remove profiles
                for connector_key, prof_id in profiles_to_remove:
                    if connector_key in charging_profiles and prof_id in charging_profiles[connector_key]:
                        del charging_profiles[connector_key][prof_id]
                        logger.info(f"Removed charging profile {prof_id} from {charge_point_id} {connector_key}")
                
                # Clean up empty connector entries
                for connector_key in list(charging_profiles.keys()):
                    if not charging_profiles[connector_key]:
                        del charging_profiles[connector_key]
                
                charger.charging_profiles = charging_profiles
                flag_modified(charger, 'charging_profiles')
                db.session.commit()
                logger.info(f"Cleared charging profiles for {charge_point_id}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when clearing charging profiles")
        except Exception as e:
            logger.error(f"Error clearing charging profiles for {charge_point_id}: {e}")
            db.session.rollback()

    def get_charging_profiles(self, charge_point_id: str, connector_id: int = None) -> Dict[str, dict]:
        """Get charging profiles for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.charging_profiles and isinstance(charger.charging_profiles, dict):
            if connector_id is not None:
                connector_key = f"connector_{connector_id}"
                return charger.charging_profiles.get(connector_key, {})
            return charger.charging_profiles
        return {}

    # === JIO_BP DATA TRANSFER FUNCTIONALITY ===
    def set_jio_bp_settings(self, charge_point_id: str, jio_bp_settings: dict) -> None:
        """Store Jio_BP data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                # Store in a new field or reuse existing JSON field
                # We'll use the data_transfer_packets field to store Jio_BP settings
                data_packets = charger.data_transfer_packets or []
                if not isinstance(data_packets, list):
                    data_packets = []
                
                # Remove any existing Jio_BP settings
                data_packets = [packet for packet in data_packets if not packet.get('is_jio_bp_setting', False)]
                
                # Add new Jio_BP settings
                jio_bp_packet = {
                    'is_jio_bp_setting': True,
                    'settings': jio_bp_settings,
                    'created_at': datetime.utcnow().isoformat()
                }
                data_packets.append(jio_bp_packet)
                
                charger.data_transfer_packets = data_packets
                flag_modified(charger, 'data_transfer_packets')
                db.session.commit()
                logger.info(f"Set Jio_BP settings for {charge_point_id}: {jio_bp_settings}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when setting Jio_BP settings")
        except Exception as e:
            logger.error(f"Error setting Jio_BP settings for {charge_point_id}: {e}")
            db.session.rollback()

    def get_jio_bp_settings(self, charge_point_id: str) -> Optional[dict]:
        """Get Jio_BP data transfer settings for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.data_transfer_packets:
            data_packets = charger.data_transfer_packets or []
            if isinstance(data_packets, list):
                for packet in data_packets:
                    if packet.get('is_jio_bp_setting', False):
                        return packet.get('settings', {})
        return None

    def clear_jio_bp_settings(self, charge_point_id: str) -> None:
        """Clear Jio_BP data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.data_transfer_packets:
                data_packets = charger.data_transfer_packets or []
                if isinstance(data_packets, list):
                    # Remove Jio_BP settings
                    data_packets = [packet for packet in data_packets if not packet.get('is_jio_bp_setting', False)]
                    charger.data_transfer_packets = data_packets
                    flag_modified(charger, 'data_transfer_packets')
                    db.session.commit()
                    logger.info(f"Cleared Jio_BP settings for {charge_point_id}")
        except Exception as e:
            logger.error(f"Error clearing Jio_BP settings for {charge_point_id}: {e}")
            db.session.rollback()

    # === MSIL DATA TRANSFER FUNCTIONALITY ===
    def set_msil_settings(self, charge_point_id: str, msil_settings: dict) -> None:
        """Store MSIL data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                data_packets = charger.data_transfer_packets or []
                if not isinstance(data_packets, list):
                    data_packets = []
                
                # Remove any existing MSIL settings
                data_packets = [packet for packet in data_packets if not packet.get('is_msil_setting', False)]
                
                # Add new MSIL settings
                msil_packet = {
                    'is_msil_setting': True,
                    'settings': msil_settings,
                    'created_at': datetime.utcnow().isoformat()
                }
                data_packets.append(msil_packet)
                
                charger.data_transfer_packets = data_packets
                flag_modified(charger, 'data_transfer_packets')
                db.session.commit()
                logger.info(f"Set MSIL settings for {charge_point_id}: {msil_settings}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when setting MSIL settings")
        except Exception as e:
            logger.error(f"Error setting MSIL settings for {charge_point_id}: {e}")
            db.session.rollback()

    def get_msil_settings(self, charge_point_id: str) -> Optional[dict]:
        """Get MSIL data transfer settings for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.data_transfer_packets:
            data_packets = charger.data_transfer_packets or []
            if isinstance(data_packets, list):
                for packet in data_packets:
                    if packet.get('is_msil_setting', False):
                        return packet.get('settings', {})
        return None

    def clear_msil_settings(self, charge_point_id: str) -> None:
        """Clear MSIL data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.data_transfer_packets:
                data_packets = charger.data_transfer_packets or []
                if isinstance(data_packets, list):
                    # Remove MSIL settings
                    data_packets = [packet for packet in data_packets if not packet.get('is_msil_setting', False)]
                    charger.data_transfer_packets = data_packets
                    flag_modified(charger, 'data_transfer_packets')
                    db.session.commit()
                    logger.info(f"Cleared MSIL settings for {charge_point_id}")
        except Exception as e:
            logger.error(f"Error clearing MSIL settings for {charge_point_id}: {e}")
            db.session.rollback()

    # === CZ DATA TRANSFER FUNCTIONALITY ===
    def set_cz_settings(self, charge_point_id: str, cz_settings: dict) -> None:
        """Store CZ data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                data_packets = charger.data_transfer_packets or []
                if not isinstance(data_packets, list):
                    data_packets = []
                
                # Remove any existing CZ settings
                data_packets = [packet for packet in data_packets if not packet.get('is_cz_setting', False)]
                
                # Add new CZ settings
                cz_packet = {
                    'is_cz_setting': True,
                    'settings': cz_settings,
                    'created_at': datetime.utcnow().isoformat()
                }
                data_packets.append(cz_packet)
                
                charger.data_transfer_packets = data_packets
                flag_modified(charger, 'data_transfer_packets')
                db.session.commit()
                logger.info(f"Set CZ settings for {charge_point_id}: {cz_settings}")
            else:
                logger.warning(f"Charger {charge_point_id} not found when setting CZ settings")
        except Exception as e:
            logger.error(f"Error setting CZ settings for {charge_point_id}: {e}")
            db.session.rollback()

    def get_cz_settings(self, charge_point_id: str) -> Optional[dict]:
        """Get CZ data transfer settings for a charger."""
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger and charger.data_transfer_packets:
            data_packets = charger.data_transfer_packets or []
            if isinstance(data_packets, list):
                for packet in data_packets:
                    if packet.get('is_cz_setting', False):
                        return packet.get('settings', {})
        return None

    def clear_cz_settings(self, charge_point_id: str) -> None:
        """Clear CZ data transfer settings for a charger."""
        try:
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger and charger.data_transfer_packets:
                data_packets = charger.data_transfer_packets or []
                if isinstance(data_packets, list):
                    # Remove CZ settings
                    data_packets = [packet for packet in data_packets if not packet.get('is_cz_setting', False)]
                    charger.data_transfer_packets = data_packets
                    flag_modified(charger, 'data_transfer_packets')
                    db.session.commit()
                    logger.info(f"Cleared CZ settings for {charge_point_id}")
        except Exception as e:
            logger.error(f"Error clearing CZ settings for {charge_point_id}: {e}")
            db.session.rollback()

    def delete_charger_completely(self, charge_point_id: str) -> bool:
        """Delete a charger and all its associated data from the database."""
        try:
            # Refresh the database session to ensure we see the latest data
            db.session.close()
            db.session = SessionLocal()
            
            # First, let's check what chargers exist in the database
            all_chargers = db.session.query(Charger).all()
            logger.info(f"Available chargers in database: {[c.charge_point_id for c in all_chargers]}")
            
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                logger.info(f"Found charger {charge_point_id} in database, proceeding with deletion")
                
                # Remove charger from memory store if connected
                if charge_point_id in self.chargers:
                    del self.chargers[charge_point_id]
                    logger.info(f"Removed {charge_point_id} from memory store")
                
                # Remove from transaction tracking
                if charge_point_id in self.transaction_ids:
                    del self.transaction_ids[charge_point_id]
                    logger.info(f"Removed {charge_point_id} from transaction tracking")
                
                # Delete from database (this will delete all associated data including logs)
                db.session.delete(charger)
                db.session.commit()
                
                logger.info(f"Charger {charge_point_id} and all its data deleted from database")
                return True
            else:
                logger.warning(f"Charger {charge_point_id} not found in database. Available chargers: {[c.charge_point_id for c in all_chargers]}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting charger {charge_point_id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            db.session.rollback()
            return False

# Create a global instance
charger_store = ChargerStore() 
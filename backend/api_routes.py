from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Response
from typing import List, Dict, Optional, Union
from pydantic import BaseModel
import json
import logging
from datetime import datetime
import traceback

from .charger_store import charger_store
from .ocpp_handler import ChargePoint
from .database import db
from .config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models for request/response validation
class IdTagRequest(BaseModel):
    id_tag: str
    status: str = "Accepted"
    expiry_date: Optional[str] = None

class RemoteStartRequest(BaseModel):
    id_tag: str
    connector_id: Optional[int] = None

class RemoteStopRequest(BaseModel):
    transaction_id: int

class DataTransferRequest(BaseModel):
    vendor_id: str
    message_id: Optional[str] = None
    data: Optional[Union[str, Dict]] = None  # Allow both string and object for MSIL

class DataTransferPacketRequest(BaseModel):
    name: str
    vendor_id: str
    message_id: Optional[str] = None
    data: Optional[str] = None

class LocalListRequest(BaseModel):
    update_type: str  # "Full" or "Differential"
    local_authorization_list: Optional[List[Dict]] = None
    force_store_locally: Optional[bool] = False

# Store active WebSocket connections
charge_points: Dict[str, ChargePoint] = {}

class WebSocketAdapter:
    """Adapter to make FastAPI WebSocket compatible with ocpp library's WebSocket interface."""
    def __init__(self, websocket: WebSocket, charge_point_id: str):
        self.websocket = websocket
        self.charge_point_id = charge_point_id
        self._closed = False

    async def send(self, message: str):
        """Send a message to the WebSocket."""
        if not self._closed:
            # Log complete WebSocket frame being sent
            try:
                parsed_msg = json.loads(message)
                charger_store.add_log(self.charge_point_id, f"WebSocket CMS→Charger Frame: {json.dumps(parsed_msg, indent=2)}")
            except:
                charger_store.add_log(self.charge_point_id, f"WebSocket CMS→Charger Frame: {message}")
            await self.websocket.send_text(message)

    async def recv(self) -> str:
        """Receive a message from the WebSocket."""
        if not self._closed:
            try:
                message = await self.websocket.receive_text()
                # Log complete WebSocket frame received
                try:
                    parsed_msg = json.loads(message)
                    charger_store.add_log(self.charge_point_id, f"WebSocket Charger→CMS Frame: {json.dumps(parsed_msg, indent=2)}")
                except:
                    charger_store.add_log(self.charge_point_id, f"WebSocket Charger→CMS Frame: {message}")
                
                # Update last_heartbeat on ANY WebSocket message received
                from .database import Charger
                charger = db.session.query(Charger).filter_by(charge_point_id=self.charge_point_id).first()
                if charger:
                    charger.last_heartbeat = datetime.utcnow()
                    db.session.commit()
                
                return message
            except WebSocketDisconnect:
                self._closed = True
                raise
        raise Exception("WebSocket is closed")

    async def close(self):
        """Close the WebSocket connection."""
        if not self._closed:
            self._closed = True
            await self.websocket.close()

    @property
    def closed(self) -> bool:
        """Check if the WebSocket is closed."""
        return self._closed

    @property
    def subprotocol(self) -> str:
        """Get the WebSocket subprotocol."""
        return "ocpp1.6"

@router.get("/ocpp16/{charge_point_id}")
async def ocpp_handshake(charge_point_id: str, request: Request):
    """Handle OCPP 1.6 handshake request."""
    logger.info(f"Received OCPP handshake request from {charge_point_id}")
    
    # Check if WebSocket upgrade is requested
    if "upgrade" in request.headers and request.headers["upgrade"].lower() == "websocket":
        # Return 101 Switching Protocols
        return Response(
            status_code=101,
            headers={
                "Upgrade": "websocket",
                "Connection": "Upgrade",
                "Sec-WebSocket-Accept": "accepted"
            }
        )
    else:
        raise HTTPException(status_code=400, detail="WebSocket upgrade required")

@router.websocket("/ws/{charge_point_id}")
async def websocket_endpoint(websocket: WebSocket, charge_point_id: str):
    """WebSocket endpoint for OCPP connections."""
    try:
        # Ensure charger exists in database FIRST
        from .database import Charger
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if not charger:
            # Add new charger to database if it doesn't exist
            charger_store.add_charger(charge_point_id)
        
        # Log HTTP handshake details BEFORE accepting
        headers = dict(websocket.headers)
        client_info = {
            "client_ip": websocket.client.host if websocket.client else "unknown",
            "client_port": websocket.client.port if websocket.client else "unknown",
            "headers": headers,
            "path": f"/ws/{charge_point_id}",
            "method": "GET",
            "protocol": "HTTP/1.1"
        }
        charger_store.add_log(charge_point_id, f"HTTP Charger→CMS WebSocket Handshake Request:\n{json.dumps(client_info, indent=2)}")
        logger.info(f"WebSocket handshake request from {charge_point_id}: {headers}")
        
        # Accept the WebSocket connection with OCPP subprotocol
        try:
            await websocket.accept(subprotocol="ocpp1.6")
        except Exception as e:
            logger.warning(f"Failed to accept with subprotocol, trying without: {e}")
            await websocket.accept()
        
        # Log handshake response
        response_info = {
            "status": "101 Switching Protocols",
            "upgrade": "websocket", 
            "connection": "Upgrade",
            "sec-websocket-protocol": "ocpp1.6",
            "server": "FastAPI-OCPP-CMS"
        }
        charger_store.add_log(charge_point_id, f"HTTP CMS→Charger WebSocket Handshake Response:\n{json.dumps(response_info, indent=2)}")
        logger.info(f"WebSocket connection accepted for {charge_point_id}")
        
        # Create adapter for the WebSocket
        ws_adapter = WebSocketAdapter(websocket, charge_point_id)
        
        # Create charge point instance
        charge_point = ChargePoint(charge_point_id, ws_adapter)
        charge_points[charge_point_id] = charge_point
        logger.info(f"Added {charge_point_id} to charge_points. Current connections: {list(charge_points.keys())}")
        
        # Update charger last_heartbeat in database (but not status - StatusNotification handles that)
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            charger.last_heartbeat = datetime.utcnow()
            db.session.commit()
            logger.info(f"Updated database last_heartbeat for {charge_point_id}")
        
        try:
            # Start the charge point
            await charge_point.start()
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for {charge_point_id}")
        except Exception as e:
            logger.error(f"Error in WebSocket connection for {charge_point_id}: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Clean up
            logger.info(f"WebSocket cleanup for {charge_point_id}. Before cleanup: {list(charge_points.keys())}")
            if charge_point_id in charge_points:
                del charge_points[charge_point_id]
                logger.info(f"Removed {charge_point_id} from charge_points. After cleanup: {list(charge_points.keys())}")
            
            # No need to update database status - the API will show "Disconnected" based on WebSocket connectivity
            # This preserves the last known status from StatusNotification
            logger.info(f"WebSocket disconnected for {charge_point_id} - API will show as Disconnected")
                
            await ws_adapter.close()
    except Exception as e:
        logger.error(f"Exception during WebSocket accept or setup for {charge_point_id}: {e}")
        logger.error(traceback.format_exc())
        raise

@router.get("/api/logs/{charge_point_id}")
async def get_logs(charge_point_id: str):
    """Get logs for a specific charger."""
    return charger_store.get_logs(charge_point_id)

@router.post("/api/logs/{charge_point_id}/clear")
async def clear_logs(charge_point_id: str):
    """Clear logs for a specific charger."""
    charger_store.clear_logs(charge_point_id)
    return {"message": f"Logs cleared for charger {charge_point_id}"}

@router.get("/api/chargers")
async def get_chargers():
    """Get list of chargers from the database."""
    from .database import Charger
    logger.debug("Getting chargers from database...")
    chargers = db.session.query(Charger).all()
    logger.debug(f"Found {len(chargers)} chargers in database")
    
    # Check active WebSocket connections - this is the primary indicator of connectivity
    result = []
    charger_ids_in_db = set()
    
    # Log current WebSocket connections for debugging
    logger.info(f"Current active WebSocket connections: {list(charge_points.keys())}")
    
    # Process chargers from database
    for charger in chargers:
        logger.debug(f"Processing charger: {charger.charge_point_id}, status: {charger.status}")
        charger_ids_in_db.add(charger.charge_point_id)
        is_ws_connected = charger.charge_point_id in charge_points
        
        # Enhanced connection detection: Check for recent activity if WebSocket tracking is missing
        is_recently_active = False
        if not is_ws_connected and charger.logs:
            # Check if there are recent logs (within last 60 seconds)
            from datetime import datetime, timedelta
            current_time = datetime.utcnow()
            recent_threshold = current_time - timedelta(seconds=60)
            
            for log in reversed(charger.logs[-10:]):  # Check last 10 logs
                try:
                    log_time_str = log.get('timestamp', '')
                    if log_time_str:
                        # Parse log timestamp (remove 'Z' if present)
                        log_time_str = log_time_str.replace('Z', '')
                        log_time = datetime.fromisoformat(log_time_str)
                        
                        if log_time > recent_threshold:
                            # Check if it's an OCPP message (not just system messages)
                            message = log.get('message', '')
                            if ('WebSocket' in message and 'Frame:' in message) or 'received' in message.lower():
                                is_recently_active = True
                                logger.info(f"Charger {charger.charge_point_id}: Found recent activity at {log_time_str}")
                                break
                except Exception as e:
                    logger.debug(f"Error parsing log timestamp: {e}")
                    continue
        
        # Final connection status: WebSocket connected OR recently active
        is_connected = is_ws_connected or is_recently_active
        
        logger.info(f"Charger {charger.charge_point_id}: WebSocket={is_ws_connected}, RecentActivity={is_recently_active}, Final={is_connected}")
        
        # Status logic: 
        # - If connected: show the actual status from StatusNotification (prefer recent logs if more current)
        # - If disconnected: show "Disconnected"
        display_status = charger.status if is_connected else "Disconnected"
        
        # If connected, find the latest StatusNotification in logs by timestamp
        if is_connected and charger.logs:
            latest_status = None
            latest_timestamp = None
            
            # Scan ALL logs to find the actual latest StatusNotification by timestamp
            for log in charger.logs:
                try:
                    message = log.get('message', '')
                    if 'StatusNotification:' in message and 'status=' in message:
                        # Extract status from StatusNotification log
                        import re
                        status_match = re.search(r'status=([^,\s]+)', message)
                        if status_match:
                            candidate_status = status_match.group(1)
                            valid_statuses = ['Available', 'Preparing', 'Charging', 'SuspendedEVSE', 
                                            'SuspendedEV', 'Finishing', 'Reserved', 'Unavailable', 'Faulted']
                            if candidate_status in valid_statuses:
                                log_timestamp = log.get('timestamp')
                                if log_timestamp:
                                    # Parse timestamp to compare (handle both with and without 'Z')
                                    from datetime import datetime
                                    try:
                                        if log_timestamp.endswith('Z'):
                                            parsed_time = datetime.fromisoformat(log_timestamp.replace('Z', '+00:00'))
                                        else:
                                            parsed_time = datetime.fromisoformat(log_timestamp)
                                        
                                        # Keep track of the latest StatusNotification
                                        if latest_timestamp is None or parsed_time > latest_timestamp:
                                            latest_status = candidate_status
                                            latest_timestamp = parsed_time
                                            logger.debug(f"Found StatusNotification for {charger.charge_point_id}: {candidate_status} at {log_timestamp}")
                                    except ValueError as ve:
                                        logger.debug(f"Could not parse timestamp {log_timestamp}: {ve}")
                                        continue
                except Exception as e:
                    logger.debug(f"Error parsing status from log: {e}")
                    continue
            
            # Use the latest status from logs as display status
            if latest_status:
                if latest_status != charger.status:
                    logger.info(f"Using latest StatusNotification '{latest_status}' for {charger.charge_point_id} (at {latest_timestamp}) instead of database status '{charger.status}'")
                    display_status = latest_status
                    
                    # Update database with the latest status for consistency
                    charger.status = latest_status
                    db.session.commit()
                else:
                    # Status matches, use it
                    display_status = latest_status
        
        charger_data = {
            "id": charger.charge_point_id,
            "status": display_status,
            "last_seen": charger.last_heartbeat.isoformat() if charger.last_heartbeat else None,
            "connected": is_connected,  # Enhanced: WebSocket connection OR recent activity
            "websocket_connected": is_ws_connected,  # True WebSocket connection status
            "recently_active": is_recently_active  # Recent activity indicator
        }
        result.append(charger_data)
        logger.info(f"Charger {charger.charge_point_id} data: {charger_data}")
    
    # Also include chargers with active WebSocket connections that aren't in database yet
    for charge_point_id in charge_points:
        if charge_point_id not in charger_ids_in_db:
            logger.debug(f"Found WebSocket-only charger: {charge_point_id}")
            charger_data = {
                "id": charge_point_id,
                "status": "Available",  # Default status for WebSocket-only chargers
                "last_seen": None,
                "connected": True,  # Has active WebSocket connection
                "websocket_connected": True,  # True WebSocket connection status
                "recently_active": False  # Not recently active, actively connected
            }
            result.append(charger_data)
    
    logger.debug(f"Returning {len(result)} chargers")
    return {"chargers": result}

@router.post("/api/send/{charge_point_id}/remote_start")
async def remote_start_transaction(charge_point_id: str, request: RemoteStartRequest):
    """Send RemoteStartTransaction request."""
    
    # First check if charger is in charge_points (preferred method)
    if charge_point_id in charge_points:
        try:
            logger.info(f"Sending remote start to {charge_point_id} with id_tag={request.id_tag}, connector_id={request.connector_id}")
            response = await charge_points[charge_point_id].remote_start_transaction(request.connector_id, request.id_tag)
            logger.info(f"Remote start response from {charge_point_id}: {response}")
            return {"status": "success", "response": response}
        except Exception as e:
            logger.error(f"Remote start error for {charge_point_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # If not in charge_points, check if charger has recent activity (heartbeats)
    # This handles the case where WebSocket is active but not properly tracked
    charger = charger_store.get_charger(charge_point_id)
    if charger:
        # Check for recent heartbeats (within last 60 seconds)
        from datetime import datetime, timedelta
        current_time = datetime.utcnow()
        recent_threshold = current_time - timedelta(seconds=60)
        
        has_recent_heartbeats = False
        if charger.logs:
            for log in reversed(charger.logs[-10:]):  # Check last 10 logs
                try:
                    log_time_str = log.get('timestamp', '')
                    if log_time_str and 'Heartbeat received' in log.get('message', ''):
                        log_time = datetime.fromisoformat(log_time_str.replace('Z', ''))
                        if log_time > recent_threshold:
                            has_recent_heartbeats = True
                            logger.info(f"Found recent heartbeat for {charge_point_id} at {log_time_str}")
                            break
                except Exception as e:
                    logger.debug(f"Error parsing log timestamp: {e}")
                    continue
        
        if has_recent_heartbeats:
            raise HTTPException(
                status_code=503, 
                detail=f"Charger '{charge_point_id}' is receiving heartbeats but not properly tracked in WebSocket connections. "
                       f"This indicates a server-side tracking issue. Please try again or restart the charger connection."
            )
        else:
            raise HTTPException(
                status_code=503, 
                detail=f"Charger '{charge_point_id}' is not actively connected via WebSocket. "
                       f"Current status: {charger.status}. Please ensure the charger is online and has an active connection."
            )
    else:
        raise HTTPException(status_code=404, detail="Charger not found")

@router.post("/api/send/{charge_point_id}/remote_stop")
async def remote_stop_transaction(charge_point_id: str, request: RemoteStopRequest):
    """Send RemoteStopTransaction request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        response = await charge_points[charge_point_id].remote_stop_transaction(request.transaction_id)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/send/{charge_point_id}/get_configuration")
async def get_configuration(charge_point_id: str, keys: Optional[List[str]] = None):
    """Send GetConfiguration request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        response = await charge_points[charge_point_id].get_configuration(keys)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class ChangeConfigurationRequest(BaseModel):
    key: str
    value: str

class ResetRequest(BaseModel):
    type: str  # "hard" or "soft"

class TriggerMessageRequest(BaseModel):
    requested_message: str  # Message type to trigger
    connector_id: Optional[int] = None  # Optional connector ID

@router.post("/api/send/{charge_point_id}/change_configuration")
async def change_configuration(charge_point_id: str, request: ChangeConfigurationRequest):
    """Send ChangeConfiguration request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        response = await charge_points[charge_point_id].change_configuration(request.key, request.value)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/clear_cache")
async def clear_cache(charge_point_id: str):
    """Send ClearCache request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        response = await charge_points[charge_point_id].clear_cache()
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/reset")
async def reset_charger(charge_point_id: str, request: ResetRequest):
    """Send Reset request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    # Validate reset type
    if request.type.lower() not in ["hard", "soft"]:
        raise HTTPException(status_code=400, detail="Reset type must be 'hard' or 'soft'")
    
    try:
        response = await charge_points[charge_point_id].reset(request.type)
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/trigger_message")
async def trigger_message(charge_point_id: str, request: TriggerMessageRequest):
    """Send TriggerMessage request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    # Validate requested message type
    valid_messages = [
        "BootNotification", "DiagnosticsStatusNotification", "FirmwareStatusNotification",
        "Heartbeat", "MeterValues", "StatusNotification"
    ]
    
    if request.requested_message not in valid_messages:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid message type. Must be one of: {', '.join(valid_messages)}"
        )
    
    try:
        response = await charge_points[charge_point_id].trigger_message(
            request.requested_message, 
            request.connector_id
        )
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/send_local_list")
async def send_local_list(charge_point_id: str, request: LocalListRequest):
    """Send SendLocalList request and store ID tags locally."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        list_version = charger_store.increment_local_auth_list_version()
        response = await charge_points[charge_point_id].send_local_list(
            list_version=list_version,
            update_type=request.update_type,
            local_authorization_list=request.local_authorization_list
        )
        
        # Store ID tags locally if charger accepted OR if force_store_locally is True
        charger_accepted = response and hasattr(response, 'status') and response.status == "Accepted"
        should_store_locally = charger_accepted or request.force_store_locally
        
        if should_store_locally and request.local_authorization_list:
            stored_count = 0
            for auth_item in request.local_authorization_list:
                if 'idTag' in auth_item:
                    id_tag = auth_item['idTag']
                    
                    # Validate ID tag length according to OCPP 1.6 specification (max 20 characters)
                    if len(id_tag) > 20:
                        logger.warning(f"Skipping ID tag '{id_tag}' - exceeds 20 character limit (length: {len(id_tag)})")
                        continue
                    
                    id_tag_info = auth_item.get('idTagInfo', {})
                    
                    # Extract status and expiry date
                    status = id_tag_info.get('status', 'Accepted')
                    expiry_date = None
                    
                    if 'expiryDate' in id_tag_info:
                        try:
                            from datetime import datetime
                            expiry_date = datetime.fromisoformat(id_tag_info['expiryDate'].replace('Z', '+00:00'))
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid expiry date format for {id_tag}: {id_tag_info['expiryDate']}")
                    
                    # Store the ID tag locally
                    charger_store.add_id_tag(id_tag, status, expiry_date)
                    stored_count += 1
            
            store_reason = "charger accepted" if charger_accepted else "force_store_locally enabled"
            logger.info(f"Successfully stored {stored_count} ID tags locally from local list ({store_reason})")
        
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Error in send_local_list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/clear_local_list")
async def clear_local_list(charge_point_id: str):
    """Send ClearLocalList request (implemented as SendLocalList with empty list)."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        logger.info(f"Clearing local list for {charge_point_id}")
        response = await charge_points[charge_point_id].clear_local_list()
        logger.info(f"Clear local list response from {charge_point_id}: {response}")
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Clear local list error for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/send/{charge_point_id}/get_local_list_version")
async def get_local_list_version(charge_point_id: str):
    """Send GetLocalListVersion request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        logger.info(f"Getting local list version for {charge_point_id}")
        response = await charge_points[charge_point_id].get_local_list_version()
        logger.info(f"Get local list version response from {charge_point_id}: {response}")
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Get local list version error for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/data_transfer")
async def data_transfer(charge_point_id: str, request: DataTransferRequest):
    """Send DataTransfer request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        # Special handling for MSIL - send as object (OCPP violation)
        if request.vendor_id == "MSIL" and isinstance(request.data, dict):
            logger.info(f"Sending MSIL DataTransfer with object data (OCPP violation)")
            response = await charge_points[charge_point_id]._send_msil_packet(
                message_id=request.message_id,
                data=request.data
            )
            return {"status": "success", "response": {"status": "Accepted" if response else "Rejected"}}
        else:
            # Standard OCPP-compliant DataTransfer (string data)
            response = await charge_points[charge_point_id].data_transfer(
                vendor_id=request.vendor_id,
                message_id=request.message_id,
                data=request.data
            )
            return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/idtags")
async def get_id_tags():
    """Get all idTags."""
    return charger_store.get_id_tags()

@router.post("/api/idtags")
async def add_id_tag(request: IdTagRequest):
    """Add or update an idTag."""
    # Validate ID tag length according to OCPP 1.6 specification (max 20 characters)
    if len(request.id_tag) > 20:
        raise HTTPException(
            status_code=400, 
            detail=f"ID tag is too long! Maximum length is 20 characters (OCPP 1.6 specification). Current length: {len(request.id_tag)} characters."
        )
    
    expiry_date = None
    if request.expiry_date:
        try:
            from datetime import datetime
            # Handle datetime-local format (YYYY-MM-DDTHH:MM)
            if 'T' in request.expiry_date:
                expiry_date = datetime.fromisoformat(request.expiry_date)
            else:
                # Handle date only format
                expiry_date = datetime.strptime(request.expiry_date, '%Y-%m-%d')
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid expiry date format: {str(e)}")
    
    charger_store.add_id_tag(request.id_tag, request.status, expiry_date)
    return {"status": "success", "message": f"Added/Updated idTag: {request.id_tag}"}

@router.delete("/api/idtags/{id_tag}")
async def delete_id_tag(id_tag: str):
    """Delete an idTag."""
    if db.delete_id_tag(id_tag):
        return {"status": "success", "message": f"Deleted idTag: {id_tag}"}
    raise HTTPException(status_code=404, detail="ID tag not found")

@router.get("/api/connector_status/{charge_point_id}")
async def get_connector_status(charge_point_id: str):
    """Get connector status for a charger."""
    return charger_store.get_connector_status(charge_point_id)

@router.get("/api/active_transactions/{charge_point_id}")
async def get_active_transactions(charge_point_id: str):
    """Get active transactions for a charger."""
    try:
        active_transactions = []
        
        # Get active transaction using the charger store method
        active_transaction = charger_store.get_active_transaction(charge_point_id)
        
        if active_transaction:
            active_transactions.append({
                "transaction_id": active_transaction['transaction_id'],
                "status": active_transaction['status'],
                "start_time": active_transaction['started_at'],
                "id_tag": active_transaction.get('id_tag'),
                "connector_id": active_transaction.get('connector_id', 1)
            })
        
        logger.debug(f"Found {len(active_transactions)} active transactions for {charge_point_id}")
        return {"active_transactions": active_transactions}
        
    except Exception as e:
        logger.error(f"Error getting active transactions for {charge_point_id}: {e}")
        return {"active_transactions": []}

# Data Transfer Packet endpoints
@router.get("/api/data_transfer_packets")
async def get_data_transfer_packets():
    try:
        return db.get_data_transfer_packets()
    except Exception as e:
        logger.error(f"Error getting data transfer packets: {e}")
        traceback.print_exc()
        return []

@router.post("/api/data_transfer_packets")
async def create_data_transfer_packet(request: DataTransferPacketRequest):
    """Create a new data transfer packet."""
    try:
        packet_id = db.save_data_transfer_packet(
            name=request.name,
            vendor_id=request.vendor_id,
            message_id=request.message_id,
            data=request.data
        )
        return {"status": "success", "id": packet_id}
    except Exception as e:
        logger.error(f"Error creating data transfer packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/data_transfer_packets/{packet_id}")
async def delete_data_transfer_packet(packet_id: int):
    """Delete a data transfer packet template."""
    try:
        success = db.delete_data_transfer_packet(packet_id)
        if success:
            return {"message": f"Data transfer packet {packet_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Data transfer packet not found")
    except Exception as e:
        logger.error(f"Error deleting data transfer packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === NEW REQUEST MODELS FOR ADVANCED FUNCTIONS ===
class ChangeAvailabilityRequest(BaseModel):
    connector_id: int
    availability_type: str  # "Operative" or "Inoperative"

class ReserveNowRequest(BaseModel):
    connector_id: int
    expiry_date: str  # ISO 8601 datetime
    id_tag: str
    reservation_id: int
    parent_id_tag: Optional[str] = None

class CancelReservationRequest(BaseModel):
    reservation_id: int

class ChargingSchedulePeriod(BaseModel):
    start_period: int  # Seconds from start of schedule
    limit: float  # Maximum charging rate limit
    number_phases: Optional[int] = None

class ChargingSchedule(BaseModel):
    duration: Optional[int] = None  # Duration in seconds
    start_schedule: Optional[str] = None  # ISO 8601 datetime
    charging_rate_unit: str  # "A" for Amperes or "W" for Watts
    charging_schedule_period: List[ChargingSchedulePeriod]
    min_charging_rate: Optional[float] = None

class ChargingProfile(BaseModel):
    charging_profile_id: int
    transaction_id: Optional[int] = None
    stack_level: int
    charging_profile_purpose: str  # "ChargePointMaxProfile", "TxDefaultProfile", "TxProfile"
    charging_profile_kind: str  # "Absolute", "Recurring", "Relative"
    recurrency_kind: Optional[str] = None  # "Daily", "Weekly" 
    valid_from: Optional[str] = None  # ISO 8601 datetime
    valid_to: Optional[str] = None  # ISO 8601 datetime
    charging_schedule: ChargingSchedule

class SetChargingProfileRequest(BaseModel):
    connector_id: int
    cs_charging_profiles: ChargingProfile

class ClearChargingProfileRequest(BaseModel):
    id: Optional[int] = None  # Charging profile ID
    connector_id: Optional[int] = None
    charging_profile_purpose: Optional[str] = None
    stack_level: Optional[int] = None

class GetCompositeScheduleRequest(BaseModel):
    connector_id: int
    duration: int  # Duration in seconds
    charging_rate_unit: Optional[str] = None  # "A" or "W"

# === CHANGE AVAILABILITY ENDPOINTS ===
@router.post("/api/send/{charge_point_id}/change_availability")
async def change_availability(charge_point_id: str, request: ChangeAvailabilityRequest):
    """Send ChangeAvailability command to charger."""
    try:
        logger.info(f"ChangeAvailability API called for {charge_point_id}: connector={request.connector_id}, type={request.availability_type}")
        
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            logger.error(f"Charger {charge_point_id} not found in charge_points: {list(charge_points.keys())}")
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        logger.info(f"Calling change_availability method for {charge_point_id}")
        response = await charge_point.change_availability(
            connector_id=request.connector_id,
            availability_type=request.availability_type
        )
        logger.info(f"ChangeAvailability response received: {response}")
        
        if response:
            return {
                "status": "success",
                "message": f"ChangeAvailability command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown')
                }
            }
        else:
            logger.error(f"ChangeAvailability returned None for {charge_point_id}")
            raise HTTPException(status_code=500, detail="Failed to send ChangeAvailability command")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception in ChangeAvailability API for {charge_point_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"500: Failed to send ChangeAvailability command")

# === RESERVATION ENDPOINTS ===
@router.post("/api/send/{charge_point_id}/reserve_now")
async def reserve_now(charge_point_id: str, request: ReserveNowRequest):
    """Send ReserveNow command to charger."""
    try:
        logger.info(f"ReserveNow API called for {charge_point_id}: connector={request.connector_id}, reservation_id={request.reservation_id}")
        
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            logger.error(f"Charger {charge_point_id} not found in charge_points: {list(charge_points.keys())}")
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        logger.info(f"Calling reserve_now method for {charge_point_id}")
        response = await charge_point.reserve_now(
            connector_id=request.connector_id,
            expiry_date=request.expiry_date,
            id_tag=request.id_tag,
            reservation_id=request.reservation_id,
            parent_id_tag=request.parent_id_tag
        )
        logger.info(f"ReserveNow response received: {response}")
        
        if response:
            return {
                "status": "success",
                "message": f"ReserveNow command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown')
                }
            }
        else:
            logger.error(f"ReserveNow returned None for {charge_point_id}")
            raise HTTPException(status_code=500, detail="Failed to send ReserveNow command")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Exception in ReserveNow API for {charge_point_id}: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"500: Failed to send ReserveNow command")

@router.post("/api/send/{charge_point_id}/cancel_reservation")
async def cancel_reservation(charge_point_id: str, request: CancelReservationRequest):
    """Send CancelReservation command to charger."""
    try:
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        response = await charge_point.cancel_reservation(reservation_id=request.reservation_id)
        
        if response:
            return {
                "status": "success",
                "message": f"CancelReservation command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown')
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send CancelReservation command")
    except Exception as e:
        logger.error(f"Error sending CancelReservation to {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/reservations/{charge_point_id}")
async def get_reservations(charge_point_id: str):
    """Get active reservations for a charger."""
    try:
        reservations = charger_store.get_reservations(charge_point_id)
        return {
            "charge_point_id": charge_point_id,
            "reservations": reservations
        }
    except Exception as e:
        logger.error(f"Error getting reservations for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === SMART CHARGING ENDPOINTS ===
@router.post("/api/send/{charge_point_id}/set_charging_profile")
async def set_charging_profile(charge_point_id: str, request: SetChargingProfileRequest):
    """Send SetChargingProfile command to charger."""
    try:
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        # Convert Pydantic model to dict for OCPP library
        charging_profile_dict = request.cs_charging_profiles.dict()
        
        response = await charge_point.set_charging_profile(
            connector_id=request.connector_id,
            charging_profile=charging_profile_dict
        )
        
        if response:
            return {
                "status": "success",
                "message": f"SetChargingProfile command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown')
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send SetChargingProfile command")
    except Exception as e:
        logger.error(f"Error sending SetChargingProfile to {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/clear_charging_profile")
async def clear_charging_profile(charge_point_id: str, request: ClearChargingProfileRequest):
    """Send ClearChargingProfile command to charger."""
    try:
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        response = await charge_point.clear_charging_profile(
            profile_id=request.id,
            connector_id=request.connector_id,
            charging_profile_purpose=request.charging_profile_purpose,
            stack_level=request.stack_level
        )
        
        if response:
            return {
                "status": "success",
                "message": f"ClearChargingProfile command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown')
                }
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send ClearChargingProfile command")
    except Exception as e:
        logger.error(f"Error sending ClearChargingProfile to {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/charging_profiles/{charge_point_id}")
async def get_charging_profiles(charge_point_id: str, connector_id: Optional[int] = None):
    """Get charging profiles for a charger."""
    try:
        profiles = charger_store.get_charging_profiles(charge_point_id, connector_id)
        return {
            "charge_point_id": charge_point_id,
            "connector_id": connector_id,
            "charging_profiles": profiles
        }
    except Exception as e:
        logger.error(f"Error getting charging profiles for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/get_composite_schedule")
async def get_composite_schedule(charge_point_id: str, request: GetCompositeScheduleRequest):
    """Send GetCompositeSchedule command to charger."""
    try:
        charge_point = charge_points.get(charge_point_id)
        if not charge_point:
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected")
        
        response = await charge_point.get_composite_schedule(
            connector_id=request.connector_id,
            duration=request.duration,
            charging_rate_unit=request.charging_rate_unit
        )
        
        if response:
            # Parse the response to provide more detailed information
            result = {
                "status": "success",
                "message": f"GetCompositeSchedule command sent to {charge_point_id}",
                "response": {
                    "status": getattr(response, 'status', 'Unknown'),
                    "connector_id": getattr(response, 'connector_id', None),
                    "schedule_start": getattr(response, 'schedule_start', None),
                    "charging_schedule": getattr(response, 'charging_schedule', None)
                }
            }
            return result
        else:
            raise HTTPException(status_code=500, detail="Failed to send GetCompositeSchedule command")
    except Exception as e:
        logger.error(f"Error sending GetCompositeSchedule to {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === JIO_BP DATA TRANSFER ENDPOINTS ===
class JioBpSettingsRequest(BaseModel):
    stop_energy_enabled: bool = False
    stop_energy_value: float = 10.0
    stop_time_enabled: bool = False
    stop_time_value: int = 10

# === MSIL DATA TRANSFER ENDPOINTS ===
class MsilSettingsRequest(BaseModel):
    auto_stop_enabled: bool = False
    stop_energy_value: float = 1000.0  # Energy in Wh

# === CZ DATA TRANSFER ENDPOINTS ===
class CzSettingsRequest(BaseModel):
    auto_stop_enabled: bool = False
    stop_energy_value: float = 2000.0  # Energy in Wh

class UpdateFirmwareRequest(BaseModel):
    location: str  # URL where firmware is located
    retrieve_date: str  # ISO 8601 datetime when to retrieve firmware
    retries: Optional[int] = None  # Number of retries
    retry_interval: Optional[int] = None  # Retry interval in seconds

class GetDiagnosticsRequest(BaseModel):
    location: str  # URL where to upload diagnostics
    retries: Optional[int] = None  # Number of retries
    retry_interval: Optional[int] = None  # Retry interval in seconds
    start_time: Optional[str] = None  # ISO 8601 datetime start of diagnostic period
    stop_time: Optional[str] = None  # ISO 8601 datetime end of diagnostic period

class UnlockConnectorRequest(BaseModel):
    connector_id: int  # Connector ID to unlock

@router.post("/api/jio_bp_settings/{charge_point_id}")
async def set_jio_bp_settings(charge_point_id: str, request: JioBpSettingsRequest):
    """Set Jio_BP data transfer settings for a charger."""
    try:
        settings = {
            'stop_energy_enabled': request.stop_energy_enabled,
            'stop_energy_value': request.stop_energy_value,
            'stop_time_enabled': request.stop_time_enabled,
            'stop_time_value': request.stop_time_value
        }
        
        charger_store.set_jio_bp_settings(charge_point_id, settings)
        
        return {
            "status": "success",
            "message": f"Jio_BP settings saved for {charge_point_id}",
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error setting Jio_BP settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/jio_bp_settings/{charge_point_id}")
async def get_jio_bp_settings(charge_point_id: str):
    """Get Jio_BP data transfer settings for a charger."""
    try:
        settings = charger_store.get_jio_bp_settings(charge_point_id)
        
        if settings is None:
            # Return default settings if none configured
            settings = {
                'stop_energy_enabled': False,
                'stop_energy_value': 10.0,
                'stop_time_enabled': False,
                'stop_time_value': 10
            }
        
        return {
            "charge_point_id": charge_point_id,
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error getting Jio_BP settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/jio_bp_settings/{charge_point_id}")
async def clear_jio_bp_settings(charge_point_id: str):
    """Clear Jio_BP data transfer settings for a charger."""
    try:
        charger_store.clear_jio_bp_settings(charge_point_id)
        
        return {
            "status": "success",
            "message": f"Jio_BP settings cleared for {charge_point_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing Jio_BP settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/msil_settings/{charge_point_id}")
async def set_msil_settings(charge_point_id: str, request: MsilSettingsRequest):
    """Set MSIL data transfer settings for a charger."""
    try:
        settings = {
            'auto_stop_enabled': request.auto_stop_enabled,
            'stop_energy_value': request.stop_energy_value
        }
        
        charger_store.set_msil_settings(charge_point_id, settings)
        
        return {
            "status": "success",
            "message": f"MSIL settings saved for {charge_point_id}",
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error setting MSIL settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/msil_settings/{charge_point_id}")
async def get_msil_settings(charge_point_id: str):
    """Get MSIL data transfer settings for a charger."""
    try:
        settings = charger_store.get_msil_settings(charge_point_id)
        
        if settings is None:
            # Return default settings if none configured
            settings = {
                'auto_stop_enabled': False,
                'stop_energy_value': 1000.0
            }
        
        return {
            "charge_point_id": charge_point_id,
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error getting MSIL settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/msil_settings/{charge_point_id}")
async def clear_msil_settings(charge_point_id: str):
    """Clear MSIL data transfer settings for a charger."""
    try:
        charger_store.clear_msil_settings(charge_point_id)
        
        return {
            "status": "success",
            "message": f"MSIL settings cleared for {charge_point_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing MSIL settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/cz_settings/{charge_point_id}")
async def set_cz_settings(charge_point_id: str, request: CzSettingsRequest):
    """Set CZ data transfer settings for a charger."""
    try:
        settings = {
            'auto_stop_enabled': request.auto_stop_enabled,
            'stop_energy_value': request.stop_energy_value
        }
        
        charger_store.set_cz_settings(charge_point_id, settings)
        
        return {
            "status": "success",
            "message": f"CZ settings saved for {charge_point_id}",
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error setting CZ settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/cz_settings/{charge_point_id}")
async def get_cz_settings(charge_point_id: str):
    """Get CZ data transfer settings for a charger."""
    try:
        settings = charger_store.get_cz_settings(charge_point_id)
        
        if settings is None:
            # Return default settings if none configured
            settings = {
                'auto_stop_enabled': False,
                'stop_energy_value': 2000.0
            }
        
        return {
            "charge_point_id": charge_point_id,
            "settings": settings
        }
    except Exception as e:
        logger.error(f"Error getting CZ settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/cz_settings/{charge_point_id}")
async def clear_cz_settings(charge_point_id: str):
    """Clear CZ data transfer settings for a charger."""
    try:
        charger_store.clear_cz_settings(charge_point_id)
        
        return {
            "status": "success",
            "message": f"CZ settings cleared for {charge_point_id}"
        }
    except Exception as e:
        logger.error(f"Error clearing CZ settings for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/update_firmware")
async def update_firmware(charge_point_id: str, request: UpdateFirmwareRequest):
    """Send UpdateFirmware command to charger."""
    try:
        if charge_point_id not in charge_points:
            raise HTTPException(status_code=404, detail="Charge point not connected")
        
        charge_point = charge_points[charge_point_id]
        
        # Validate retrieve_date format
        from datetime import datetime
        try:
            datetime.fromisoformat(request.retrieve_date.replace('Z', '+00:00'))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid retrieve_date format. Use ISO 8601 format (e.g., '2024-12-31T10:00:00Z')")
        
        response = await charge_point.update_firmware(
            location=request.location,
            retrieve_date=request.retrieve_date,
            retries=request.retries,
            retry_interval=request.retry_interval
        )
        
        if response:
            return {"status": "success", "message": "UpdateFirmware command sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send UpdateFirmware command")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in update_firmware API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/get_diagnostics")
async def get_diagnostics(charge_point_id: str, request: GetDiagnosticsRequest):
    """Send GetDiagnostics command to charger."""
    try:
        if charge_point_id not in charge_points:
            raise HTTPException(status_code=404, detail="Charge point not connected")
        
        charge_point = charge_points[charge_point_id]
        
        # Validate datetime formats if provided
        from datetime import datetime
        if request.start_time:
            try:
                datetime.fromisoformat(request.start_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO 8601 format (e.g., '2024-12-31T10:00:00Z')")
        
        if request.stop_time:
            try:
                datetime.fromisoformat(request.stop_time.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid stop_time format. Use ISO 8601 format (e.g., '2024-12-31T10:00:00Z')")
        
        response = await charge_point.get_diagnostics(
            location=request.location,
            retries=request.retries,
            retry_interval=request.retry_interval,
            start_time=request.start_time,
            stop_time=request.stop_time
        )
        
        if response:
            return {"status": "success", "message": "GetDiagnostics command sent successfully", "response": response}
        else:
            raise HTTPException(status_code=500, detail="Failed to send GetDiagnostics command")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_diagnostics API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/unlock_connector")
async def unlock_connector(charge_point_id: str, request: UnlockConnectorRequest):
    """Send UnlockConnector command to charger."""
    try:
        if charge_point_id not in charge_points:
            raise HTTPException(status_code=404, detail="Charge point not connected")
        
        charge_point = charge_points[charge_point_id]
        
        # Validate connector_id
        if request.connector_id < 1 or request.connector_id > 10:
            raise HTTPException(status_code=400, detail="Connector ID must be between 1 and 10")
        
        response = await charge_point.unlock_connector(connector_id=request.connector_id)
        
        if response:
            status = getattr(response, 'status', 'Unknown')
            return {
                "status": "success", 
                "message": f"UnlockConnector command sent successfully",
                "response": {"status": status}
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to send UnlockConnector command")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unlock_connector API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# UI Configuration endpoints
@router.get("/api/config/ui-features")
async def get_ui_features():
    """Get current UI feature configuration."""
    try:
        ui_features = config.get_ui_features()
        return {"status": "success", "data": ui_features}
    except Exception as e:
        logger.error(f"Error getting UI features: {e}")
        return {"status": "error", "message": str(e)}

class UIFeaturesRequest(BaseModel):
    show_jio_bp_data_transfer: Optional[bool] = None
    show_msil_data_transfer: Optional[bool] = None
    show_cz_data_transfer: Optional[bool] = None

@router.post("/api/config/ui-features")
async def update_ui_features(request: UIFeaturesRequest):
    """Update UI feature configuration."""
    try:
        import configparser
        
        # Read current config
        current_config = configparser.ConfigParser()
        current_config.read("config.ini")
        
        # Ensure UI_FEATURES section exists
        if 'UI_FEATURES' not in current_config:
            current_config.add_section('UI_FEATURES')
        
        # Update values that were provided
        if request.show_jio_bp_data_transfer is not None:
            current_config.set('UI_FEATURES', 'show_jio_bp_data_transfer', str(request.show_jio_bp_data_transfer).lower())
        
        if request.show_msil_data_transfer is not None:
            current_config.set('UI_FEATURES', 'show_msil_data_transfer', str(request.show_msil_data_transfer).lower())
        
        if request.show_cz_data_transfer is not None:
            current_config.set('UI_FEATURES', 'show_cz_data_transfer', str(request.show_cz_data_transfer).lower())
        
        # Save config
        with open("config.ini", 'w') as f:
            current_config.write(f)
        
        # Reload config
        config.load_config()
        
        return {"status": "success", "message": "UI features updated successfully. Please refresh the page to see changes."}
    
    except Exception as e:
        logger.error(f"Error updating UI features: {e}")
        return {"status": "error", "message": str(e)}

class RawMessageRequest(BaseModel):
    raw_message: str

@router.post("/api/send/{charge_point_id}/raw_message")
async def send_raw_message(charge_point_id: str, request: RawMessageRequest):
    """Send raw WebSocket message without any validation."""
    try:
        if charge_point_id not in charge_points:
            raise HTTPException(status_code=404, detail="Charge point not found or not connected")
        
        charge_point = charge_points[charge_point_id]
        
        # Send raw message (bypasses all OCPP validation)
        result = await charge_point.send_raw_message(request.raw_message)
        
        return {"status": "success", "data": result}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in send_raw_message API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/api/chargers/{charge_point_id}")
async def delete_charger(charge_point_id: str):
    """Delete a charger and all its associated data from the database."""
    try:
        from .charger_store import charger_store
        from .database import SessionLocal, Charger
        
        logger.info(f"Attempting to delete charger: {charge_point_id}")
        
        # Create a fresh database session to avoid session isolation issues
        fresh_session = SessionLocal()
        
        try:
            # First, check what chargers exist in the database using the fresh session
            all_chargers = fresh_session.query(Charger).all()
            logger.info(f"Available chargers in database: {[c.charge_point_id for c in all_chargers]}")
            
            # Find the specific charger
            charger = fresh_session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            
            if charger:
                logger.info(f"Found charger {charge_point_id} in database, proceeding with deletion")
                
                # Remove from active connections if connected
                if charge_point_id in charge_points:
                    del charge_points[charge_point_id]
                    logger.info(f"Removed {charge_point_id} from active WebSocket connections")
                
                # Remove from transaction tracking if it exists
                if charge_point_id in charger_store.transaction_ids:
                    del charger_store.transaction_ids[charge_point_id]
                    logger.info(f"Removed {charge_point_id} from transaction tracking")
                
                # Delete from database
                fresh_session.delete(charger)
                fresh_session.commit()
                
                logger.info(f"Successfully deleted charger: {charge_point_id}")
                return {"status": "success", "message": f"Charger {charge_point_id} and all its data deleted successfully"}
            else:
                logger.warning(f"Charger {charge_point_id} not found in database. Available chargers: {[c.charge_point_id for c in all_chargers]}")
                raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not found in database")
                
        finally:
            fresh_session.close()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting charger {charge_point_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e)) 
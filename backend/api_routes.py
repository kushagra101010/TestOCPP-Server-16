from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Request, Response
from typing import List, Dict, Optional
from pydantic import BaseModel
import json
import logging
from datetime import datetime
import traceback

from .charger_store import charger_store
from .ocpp_handler import ChargePoint
from .database import db

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
    data: Optional[str] = None

class DataTransferPacketRequest(BaseModel):
    name: str
    vendor_id: str
    message_id: Optional[str] = None
    data: Optional[str] = None

class LocalListRequest(BaseModel):
    update_type: str  # "Full" or "Differential"
    local_authorization_list: Optional[List[Dict]] = None

# Store active WebSocket connections
charge_points: Dict[str, ChargePoint] = {}

# Connection health tracking
connection_health: Dict[str, dict] = {}

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
        
        # Update charger status in database
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            charger.status = "Connected"
            charger.last_heartbeat = datetime.utcnow()
            db.session.commit()
        
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
            if charge_point_id in charge_points:
                del charge_points[charge_point_id]
            
            # Update charger status in database
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charger.status = "Disconnected"
                db.session.commit()
                
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

@router.post("/api/logs/{charge_point_id}/clear-on-load")
async def clear_logs_on_page_load(charge_point_id: str):
    """Clear logs for a specific charger when page loads."""
    charger_store.clear_logs(charge_point_id)
    return {"message": f"Logs cleared on page load for charger {charge_point_id}"}

@router.get("/api/chargers")
async def get_chargers():
    """Get list of chargers from the database."""
    from .database import Charger
    logger.debug("Getting chargers from database...")
    
    # Automatically cleanup stale connections first
    stale_count = await cleanup_stale_connections()
    if stale_count > 0:
        logger.info(f"Auto-cleaned {stale_count} stale connections")
    
    chargers = db.session.query(Charger).all()
    logger.debug(f"Found {len(chargers)} chargers in database")
    
    def is_connected(status):
        # Consider charger connected if status is 'Available', 'Charging', 'Preparing', or 'Connected'
        return str(status).lower() in ["available", "charging", "preparing", "connected"]
    
    # Also check active WebSocket connections
    result = []
    for charger in chargers:
        logger.debug(f"Processing charger: {charger.charge_point_id}, status: {charger.status}")
        is_ws_connected = charger.charge_point_id in charge_points
        
        # Double-check WebSocket health
        websocket_healthy = False
        if is_ws_connected:
            try:
                charge_point = charge_points[charger.charge_point_id]
                websocket_healthy = hasattr(charge_point, '_connection') and not charge_point._connection.closed
            except Exception:
                websocket_healthy = False
        
        logger.debug(f"WebSocket connected: {is_ws_connected}, healthy: {websocket_healthy}, charge_points: {list(charge_points.keys())}")
        
        # More accurate connection status
        truly_connected = is_ws_connected and websocket_healthy
        
        charger_data = {
            "id": charger.charge_point_id,
            "status": charger.status,
            "last_seen": charger.last_heartbeat.isoformat() if charger.last_heartbeat else None,
            "connected": truly_connected or is_connected(charger.status),
            "websocket_active": truly_connected,
            "can_send_commands": truly_connected  # Only allow commands if WebSocket is truly active
        }
        result.append(charger_data)
    
    logger.debug(f"Returning {len(result)} chargers")
    return {"chargers": result}

@router.post("/api/send/{charge_point_id}/remote_start")
async def remote_start_transaction(charge_point_id: str, request: RemoteStartRequest):
    """Send RemoteStartTransaction request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        logger.info(f"Sending remote start to {charge_point_id} with id_tag={request.id_tag}, connector_id={request.connector_id}")
        response = await charge_points[charge_point_id].remote_start_transaction(request.id_tag, request.connector_id)
        logger.info(f"Remote start response from {charge_point_id}: {response}")
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Remote start error for {charge_point_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
    # First check if charger exists in charge_points
    if charge_point_id not in charge_points:
        # Try cleanup and recheck
        stale_count = await cleanup_stale_connections()
        if stale_count > 0:
            logger.info(f"Cleaned up {stale_count} stale connections before reset attempt")
        
        if charge_point_id not in charge_points:
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not connected. Please ensure the charger is connected and try again.")
    
    # Validate WebSocket health
    try:
        charge_point = charge_points[charge_point_id]
        if hasattr(charge_point, '_connection') and charge_point._connection.closed:
            # Connection is stale, remove it
            del charge_points[charge_point_id]
            raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} connection is stale. Please reconnect the charger and try again.")
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Charger {charge_point_id} not found in active connections.")
    
    # Validate reset type
    if request.type.lower() not in ["hard", "soft"]:
        raise HTTPException(status_code=400, detail="Reset type must be 'hard' or 'soft'")
    
    try:
        logger.info(f"Sending {request.type} reset to {charge_point_id}")
        response = await charge_points[charge_point_id].reset(request.type)
        logger.info(f"Reset response from {charge_point_id}: {response}")
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"Reset error for {charge_point_id}: {e}")
        # If the connection failed, clean it up
        if charge_point_id in charge_points:
            try:
                del charge_points[charge_point_id]
                # Update database status
                from .database import Charger
                charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
                if charger:
                    charger.status = "Disconnected"
                    db.session.commit()
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=f"Failed to send reset command: {str(e)}")

@router.post("/api/send/{charge_point_id}/send_local_list")
async def send_local_list(charge_point_id: str, request: LocalListRequest):
    """Send SendLocalList request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
        list_version = charger_store.increment_local_auth_list_version()
        response = await charge_points[charge_point_id].send_local_list(
            list_version=list_version,
            update_type=request.update_type,
            local_authorization_list=request.local_authorization_list
        )
        return {"status": "success", "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/send/{charge_point_id}/data_transfer")
async def data_transfer(charge_point_id: str, request: DataTransferRequest):
    """Send DataTransfer request."""
    if charge_point_id not in charge_points:
        raise HTTPException(status_code=404, detail="Charger not connected")
    
    try:
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
    from .database import Charger
    charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
    
    active_transactions = []
    if charger and charger.current_transaction:
        # Check if charger is actively charging
        if str(charger.status).lower() in ["charging", "preparing"]:
            active_transactions.append({
                "transaction_id": charger.current_transaction,
                "status": charger.status,
                "start_time": charger.last_heartbeat.isoformat() if charger.last_heartbeat else None
            })
    
    return {"active_transactions": active_transactions}

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
    """Delete a data transfer packet."""
    try:
        if db.delete_data_transfer_packet(packet_id):
            return {"status": "success", "message": f"Deleted packet: {packet_id}"}
        raise HTTPException(status_code=404, detail="Packet not found")
    except Exception as e:
        logger.error(f"Error deleting data transfer packet: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/debug/active_connections")
async def get_active_connections():
    """Debug endpoint to see active WebSocket connections."""
    return {
        "active_charge_points": list(charge_points.keys()),
        "count": len(charge_points)
    }

@router.post("/api/debug/cleanup_stale_connections")
async def cleanup_stale_connections_endpoint():
    """Manually trigger cleanup of stale connections."""
    cleaned_count = await cleanup_stale_connections()
    return {
        "message": f"Cleaned up {cleaned_count} stale connections",
        "cleaned_count": cleaned_count,
        "remaining_connections": list(charge_points.keys())
    }

@router.get("/api/debug/connection_health/{charge_point_id}")
async def check_connection_health(charge_point_id: str):
    """Check the health of a specific connection."""
    if charge_point_id not in charge_points:
        return {
            "charge_point_id": charge_point_id,
            "connected": False,
            "error": "Not in active connections"
        }
    
    try:
        charge_point = charge_points[charge_point_id]
        is_alive = hasattr(charge_point, '_connection') and not charge_point._connection.closed
        
        return {
            "charge_point_id": charge_point_id,
            "connected": True,
            "websocket_alive": is_alive,
            "connection_object": str(type(charge_point._connection)) if hasattr(charge_point, '_connection') else "No connection object"
        }
    except Exception as e:
        return {
            "charge_point_id": charge_point_id,
            "connected": False,
            "error": str(e)
        }

@router.post("/api/debug/force_disconnect/{charge_point_id}")
async def force_disconnect_charger(charge_point_id: str):
    """Force disconnect a charger to allow clean reconnection."""
    if charge_point_id in charge_points:
        try:
            charge_point = charge_points[charge_point_id]
            if hasattr(charge_point, '_connection'):
                await charge_point._connection.close()
            del charge_points[charge_point_id]
            
            # Update database status
            from .database import Charger
            charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
            if charger:
                charger.status = "Disconnected"
                db.session.commit()
            
            return {
                "message": f"Successfully force disconnected {charge_point_id}",
                "success": True
            }
        except Exception as e:
            return {
                "message": f"Error during force disconnect: {str(e)}",
                "success": False
            }
    else:
        return {
            "message": f"Charger {charge_point_id} not found in active connections",
            "success": False
        }

async def cleanup_stale_connections():
    """Clean up stale connections that are no longer active."""
    stale_connections = []
    
    for charge_point_id, charge_point in charge_points.items():
        try:
            # Check if WebSocket is still active
            if hasattr(charge_point, '_connection') and charge_point._connection.closed:
                stale_connections.append(charge_point_id)
        except Exception:
            stale_connections.append(charge_point_id)
    
    # Remove stale connections
    for charge_point_id in stale_connections:
        logger.warning(f"Cleaning up stale connection for {charge_point_id}")
        if charge_point_id in charge_points:
            del charge_points[charge_point_id]
        
        # Update database status
        from .database import Charger
        charger = db.session.query(Charger).filter_by(charge_point_id=charge_point_id).first()
        if charger:
            charger.status = "Disconnected"
            db.session.commit()
    
    return len(stale_connections) 
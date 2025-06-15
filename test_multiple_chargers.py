import asyncio
import logging
import websockets
from datetime import datetime
from ocpp.v16 import ChargePoint as cp
from ocpp.v16 import call
from ocpp.v16.enums import RegistrationStatus, ChargePointStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('MultiChargerTest')

class ChargePoint(cp):
    def __init__(self, id, connection):
        super().__init__(id, connection)
        self.charger_id = id

    async def send_boot_notification(self):
        request = call.BootNotification(
            charge_point_model=f"Model_{self.charger_id[-3:]}",  # Keep it short
            charge_point_vendor=f"Vendor_{self.charger_id[-3:]}"  # Keep it short
        )
        response = await self.call(request)
        logger.info(f"{self.charger_id}: BootNotification response: {response}")
        
        # Extract heartbeat interval from response
        self.heartbeat_interval = getattr(response, 'interval', 300)  # Default to 300 seconds if not provided
        logger.info(f"{self.charger_id}: Heartbeat interval set to {self.heartbeat_interval} seconds")
        return response

    async def send_heartbeat(self):
        request = call.Heartbeat()
        response = await self.call(request)
        logger.info(f"{self.charger_id}: Heartbeat response: {response}")
        return response

    async def send_status_notification(self):
        request = call.StatusNotification(
            connector_id=1,
            error_code="NoError",
            status=ChargePointStatus.available
        )
        response = await self.call(request)
        logger.info(f"{self.charger_id}: StatusNotification response: {response}")

async def run_charger(charger_id):
    """Run a single charger continuously."""
    uri = f"ws://localhost:8000/ws/{charger_id}"
    
    try:
        async with websockets.connect(
            uri,
            subprotocols=["ocpp1.6"],
            ping_interval=None
        ) as websocket:
            
            charge_point = ChargePoint(charger_id, websocket)
            
            # Start the charge point
            await asyncio.gather(
                charge_point.start(),
                run_charger_operations(charge_point)
            )
            
    except Exception as e:
        logger.error(f"{charger_id}: Connection failed: {e}")

async def run_charger_operations(charge_point):
    """Run charger operations (boot, status, heartbeats)."""
    try:
        # Send boot notification and get heartbeat interval
        await charge_point.send_boot_notification()
        
        # Send status notification
        await charge_point.send_status_notification()
        
        # Send heartbeats continuously using the interval from boot notification response
        while True:
            await asyncio.sleep(charge_point.heartbeat_interval)
            await charge_point.send_heartbeat()
            
    except Exception as e:
        logger.error(f"{charge_point.charger_id}: Operations failed: {e}")

async def test_multiple_chargers():
    """Test multiple chargers connecting simultaneously."""
    charger_ids = [f"CHARGER_{i:03d}" for i in range(1, 21)]  # 20 chargers
    
    logger.info(f"Starting {len(charger_ids)} chargers simultaneously...")
    
    # Start all chargers concurrently
    tasks = [run_charger(charger_id) for charger_id in charger_ids]  # Run continuously
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error in concurrent test: {e}")
    
    logger.info("Multiple charger test completed")

if __name__ == "__main__":
    asyncio.run(test_multiple_chargers()) 
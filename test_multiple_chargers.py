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

    async def send_heartbeat(self):
        request = call.Heartbeat()
        response = await self.call(request)
        logger.info(f"{self.charger_id}: Heartbeat response: {response}")

    async def send_status_notification(self):
        request = call.StatusNotification(
            connector_id=1,
            error_code="NoError",
            status=ChargePointStatus.available
        )
        response = await self.call(request)
        logger.info(f"{self.charger_id}: StatusNotification response: {response}")

async def run_charger(charger_id, duration=60):
    """Run a single charger for the specified duration."""
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
                run_charger_operations(charge_point, duration)
            )
            
    except Exception as e:
        logger.error(f"{charger_id}: Connection failed: {e}")

async def run_charger_operations(charge_point, duration):
    """Run charger operations (boot, status, heartbeats)."""
    try:
        # Send boot notification
        await charge_point.send_boot_notification()
        
        # Send status notification
        await charge_point.send_status_notification()
        
        # Send heartbeats every 10 seconds for the duration
        end_time = asyncio.get_event_loop().time() + duration
        while asyncio.get_event_loop().time() < end_time:
            await charge_point.send_heartbeat()
            await asyncio.sleep(10)
            
    except Exception as e:
        logger.error(f"{charge_point.charger_id}: Operations failed: {e}")

async def test_multiple_chargers():
    """Test multiple chargers connecting simultaneously."""
    charger_ids = [f"CHARGER_{i:03d}" for i in range(1, 6)]  # 5 chargers
    
    logger.info(f"Starting {len(charger_ids)} chargers simultaneously...")
    
    # Start all chargers concurrently
    tasks = [run_charger(charger_id, 30) for charger_id in charger_ids]  # Run for 30 seconds
    
    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except Exception as e:
        logger.error(f"Error in concurrent test: {e}")
    
    logger.info("Multiple charger test completed")

if __name__ == "__main__":
    asyncio.run(test_multiple_chargers()) 
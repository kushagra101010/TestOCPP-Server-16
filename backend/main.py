import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

from backend.api_routes import router as api_router
from backend.config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce logging for specific modules that are too verbose
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
logging.getLogger('ocpp').setLevel(logging.WARNING)
logging.getLogger('websockets').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="OCPP 1.6J CMS",
    description="A development CMS for OCPP 1.6J EV chargers",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="frontend/templates")

# Include API routes with prefix
app.include_router(api_router, prefix="")  # No prefix for OCPP endpoints

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Serve the main dashboard page."""
    ui_features = config.get_ui_features()
    return templates.TemplateResponse("index.html", {
        "request": request,
        "ui_features": ui_features
    })

def start():
    """Start the FastAPI server."""
    server_config = config.get_server_config()
    uvicorn.run(
        "backend.main:app",
        host=server_config['host'],
        port=server_config['port'],
        reload=server_config['reload']
    )

if __name__ == "__main__":
    start() 
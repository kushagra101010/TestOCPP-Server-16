#!/usr/bin/env python3
"""
OCPP Server Startup Script
This script properly sets up the Python path and starts the OCPP server.
"""

import sys
import os

# Add the current directory to Python path so backend module can be imported
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Now import and start the server
from backend.main import start

if __name__ == "__main__":
    print("Starting OCPP 1.6J Server...")
    start() 
#!/usr/bin/env python3
"""
Hub E-Commerce Platform - Main Startup Script
Runs the Flask server from the backend module
"""

import sys
import os
import importlib.util

# Get paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, 'backend')
RUN_SERVER_PATH = os.path.join(BACKEND_DIR, 'run_server.py')

if __name__ == '__main__':
    # Load run_server module explicitly
    spec = importlib.util.spec_from_file_location("run_server", RUN_SERVER_PATH)
    run_server = importlib.util.module_from_spec(spec)
    sys.modules["run_server"] = run_server
    spec.loader.exec_module(run_server)
    
    # Call main function
    run_server.main()

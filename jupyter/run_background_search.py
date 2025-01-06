#!/usr/bin/env python3
import subprocess
import logging
from datetime import datetime
import os
import argparse

# Setup logging
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"search_flow_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def run_search_flow(reset=False):
    try:
        logging.info("Starting search flow background process")
        
        if reset:
            logging.warning("Resetting research data as requested")
            subprocess.run(["python", "jupyter/reset_research.py"], check=True)
        
        # Run the search flow script
        process = subprocess.Popen(
            ["python", "jupyter/search_flow.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        logging.info(f"Search flow process started with PID: {process.pid}")
        return process.pid
        
    except Exception as e:
        logging.error(f"Error starting search flow: {str(e)}")
        raise

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--reset', action='store_true', help='Reset research data before running')
    args = parser.parse_args()
    
    pid = run_search_flow(reset=args.reset)
    print(f"Search flow started in background. PID: {pid}")
    print(f"Logs available at: {log_file}")

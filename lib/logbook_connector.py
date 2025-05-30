import requests
import logging
from PySide6.QtCore import *

def send_to_cloudlog(sat, tx_freq, rx_freq, tx_mode, rx_mode, sat_name,CLOUDLOG_URL,CLOUDLOG_API_KEY):
    # Convert FMN to FM for Cloudlog
    tx_mode_send = 'FM' if tx_mode == 'FMN' else tx_mode
    rx_mode_send = 'FM' if rx_mode == 'FMN' else rx_mode
    url = CLOUDLOG_URL.rstrip('/') + '/index.php/api/radio'
    payload = {
        "key": CLOUDLOG_API_KEY,
        "radio": "QTRigDoppler",
        "frequency": str(int(tx_freq)),
        "mode": tx_mode_send,
        "frequency_rx": str(int(rx_freq)),
        "mode_rx": rx_mode_send,
        "prop_mode": "SAT",
        "sat_name": sat_name,
    }
    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info("Cloudlog API: Success")
        else:
            logging.error(f"Cloudlog API: Failed with status {response.status_code}: {response.text}")
    except Exception as e:
        logging.error(f"Cloudlog API: Exception occurred: {e}")

# CloudlogWorker for background posting
class CloudlogWorker(QRunnable):
    def __init__(self, sat, tx_freq, rx_freq, tx_mode, rx_mode, sat_name, log_url, log_api_key):
        super().__init__()
        self.sat = sat
        self.tx_freq = tx_freq
        self.rx_freq = rx_freq
        self.tx_mode = tx_mode
        self.rx_mode = rx_mode
        self.sat_name = sat_name
        self.url = log_url
        self.api_key = log_api_key
    def run(self):
        send_to_cloudlog(self.sat, self.tx_freq, self.rx_freq, self.tx_mode, self.rx_mode, self.sat_name, self.url, self.api_key)

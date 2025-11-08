"""
Remote client for QTrigdoppler to connect to the remote server
"""

import threading
import time
import json
import traceback
import socketio
import os
import sys
import configparser
import logging

class RemoteClient:
    """Client to connect QTrigdoppler to the remote server"""
    
    def __init__(self, server_url="http://localhost:5001"):
        self.server_url = server_url
        self.sio = socketio.Client(reconnection=True, reconnection_attempts=0,
                                  reconnection_delay=1, reconnection_delay_max=5)
        self.connected = False
        self.main_window = None
        self.audio_streamer = None  # Reference to AudioStreamer instance
        self.heartbeat_thread = None
        self.should_run_heartbeat = False
        self.reconnecting = False
        
        # Set up event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('registration_success', self.on_registration_success)
        
        # Command handlers
        self.sio.on('cmd_start_tracking', self.on_cmd_start_tracking)
        self.sio.on('cmd_stop_tracking', self.on_cmd_stop_tracking)
        self.sio.on('cmd_select_satellite', self.on_cmd_select_satellite)
        self.sio.on('cmd_select_transponder', self.on_cmd_select_transponder)
        self.sio.on('cmd_set_subtone', self.on_cmd_set_subtone)
        self.sio.on('cmd_set_rx_offset', self.on_cmd_set_rx_offset)
        self.sio.on('cmd_park_rotator', self.on_cmd_park_rotator)
        self.sio.on('cmd_stop_rotator', self.on_cmd_stop_rotator)
        self.sio.on('cmd_get_transponder_list', self.on_cmd_get_transponder_list)
        
        # Audio stream handlers
        self.sio.on('cmd_start_audio_tx', self.on_cmd_start_audio_tx)
        self.sio.on('cmd_stop_audio_tx', self.on_cmd_stop_audio_tx)
        self.sio.on('cmd_audio_data', self.on_cmd_audio_data)
        self.sio.on('cmd_mute_tx', self.on_cmd_mute_tx)
        self.sio.on('cmd_unmute_tx', self.on_cmd_unmute_tx)
    
    def register_window(self, window):
        """Register the main application window"""
        self.main_window = window
        # Set audio_streamer reference if available
        if hasattr(window, 'audio_streamer'):
            self.audio_streamer = window.audio_streamer
            # Start RX streaming if remote audio is enabled
            if self.audio_streamer and self.audio_streamer.enabled:
                try:
                    self.audio_streamer.start_rx_streaming(rx_callback=self.send_rx_audio_data)
                    logging.info("RX audio streaming started automatically")
                except Exception as e:
                    logging.warning(f"Failed to start RX audio streaming: {e}")
        # Send initial data if already connected
        if self.connected:
            self.send_satellite_list()
            self.send_full_status()
    
    def connect(self):
        """Connect to the remote server"""
        if not self.connected and not self.reconnecting:
            try:
                logging.info(f"Connecting to remote server at {self.server_url}")
                self.reconnecting = True
                self.sio.connect(self.server_url)
                self.reconnecting = False
            except Exception as e:
                self.reconnecting = False
                logging.error(f"Failed to connect to remote server: {e}")
                # Start a reconnection attempt in the background
                threading.Timer(5.0, self.connect).start()
    
    def disconnect(self):
        """Disconnect from the remote server"""
        self.stop_heartbeat()
        # Clear main window reference to prevent Qt object access after shutdown
        self.main_window = None
        if self.connected:
            try:
                self.sio.disconnect()
            except:
                pass
            self.connected = False
    
    def on_connect(self):
        """Handler for successful connection"""
        logging.info("Connected to remote server")
        self.connected = True
        # Register as QTrigdoppler client
        self.sio.emit('register_qtrig_client')
        # Start heartbeat
        self.start_heartbeat()
    
    def on_disconnect(self):
        """Handler for disconnection"""
        logging.info("Disconnected from remote server")
        self.connected = False
        self.stop_heartbeat()
        # Attempt to reconnect after a delay if not already reconnecting
        if not self.reconnecting:
            threading.Timer(5.0, self.connect).start()
    
    def on_registration_success(self, data):
        """Handler for successful registration as QTrigdoppler client"""
        logging.info("Registered as QTrigdoppler client")
        # Send initial data
        if self.main_window:
            self.send_satellite_list()
            self.send_full_status()
    
    def start_heartbeat(self):
        """Start the heartbeat thread"""
        self.should_run_heartbeat = True
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
    
    def stop_heartbeat(self):
        """Stop the heartbeat thread"""
        self.should_run_heartbeat = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=1.0)
            self.heartbeat_thread = None
    
    def heartbeat_worker(self):
        """Worker thread for sending heartbeats"""
        while self.should_run_heartbeat and self.connected:
            try:                # Send heartbeat with current status
                if self.main_window:
                    self.sio.emit('heartbeat', {'state': self.get_current_state()})
                else:
                    self.sio.emit('heartbeat', {})
            except Exception as e:
                logging.error(f"Error in heartbeat: {e}")
            
            # Wait before next heartbeat
            time.sleep(10)
    
    def get_current_state(self):
        """Get the current state of the application"""
        if not self.main_window:
            return {}
        
        try:
            # Check if Stopbutton exists and is valid to determine tracking state
            tracking_active = False
            if hasattr(self.main_window, 'Stopbutton'):
                try:
                    tracking_active = self.main_window.Stopbutton.isEnabled()
                except RuntimeError:
                    # Qt object has been deleted, stop heartbeat to prevent further errors
                    logging.debug("Qt objects deleted, stopping heartbeat")
                    self.should_run_heartbeat = False
                    return {}
            
            state = {
                'tracking': tracking_active,
                'satellite': None,
                'transponder': None,
                'rx_offset': 0
            }
            
            # Safely get satellite name
            try:
                if hasattr(self.main_window, 'my_satellite') and hasattr(self.main_window.my_satellite, 'name'):
                    state['satellite'] = self.main_window.my_satellite.name
            except (RuntimeError, AttributeError):
                pass
            
            # Safely get transponder name
            try:
                if hasattr(self.main_window, 'my_transponder_name'):
                    state['transponder'] = getattr(self.main_window, 'my_transponder_name', None)
            except (RuntimeError, AttributeError):
                pass
            
            # Safely get rx offset
            try:
                if hasattr(self.main_window, 'rxoffsetbox'):
                    state['rx_offset'] = self.main_window.rxoffsetbox.value()
            except (RuntimeError, AttributeError):
                pass
            
            # Safely add subtone if available
            try:
                if hasattr(self.main_window, 'combo3'):
                    state['subtone'] = self.main_window.combo3.currentText()
            except (RuntimeError, AttributeError):
                pass
            
            # Safely add satellite info if available
            try:
                if hasattr(self.main_window, 'my_satellite') and hasattr(self.main_window.my_satellite, 'name') and self.main_window.my_satellite.name:
                    sat = self.main_window.my_satellite
                    state['satellite_info'] = {
                        'name': sat.name,
                        'downlink_freq': sat.F if hasattr(sat, 'F') else None,
                        'uplink_freq': sat.I if hasattr(sat, 'I') else None,
                        'downlink_mode': sat.downmode if hasattr(sat, 'downmode') else None,
                        'uplink_mode': sat.upmode if hasattr(sat, 'upmode') else None,
                        'tle_age': sat.tle_age if hasattr(sat, 'tle_age') else None
                    }
            except (RuntimeError, AttributeError):
                pass
            
            # Safely add satellite position if available
            try:
                if hasattr(self.main_window, 'log_sat_status_ele_val') and hasattr(self.main_window, 'log_sat_status_azi_val'):
                    state['satellite_position'] = {
                        'elevation': self.main_window.log_sat_status_ele_val.text() if hasattr(self.main_window.log_sat_status_ele_val, 'text') else str(self.main_window.log_sat_status_ele_val),
                        'azimuth': self.main_window.log_sat_status_azi_val.text() if hasattr(self.main_window.log_sat_status_azi_val, 'text') else str(self.main_window.log_sat_status_azi_val)
                    }
            except (RuntimeError, AttributeError):
                pass
            
            # Safely add doppler if available
            try:
                if hasattr(self.main_window, 'rxdoppler_val') and hasattr(self.main_window, 'txdoppler_val'):
                    state['doppler'] = {
                        'downlink': self.main_window.rxdoppler_val.text() if hasattr(self.main_window.rxdoppler_val, 'text') else str(self.main_window.rxdoppler_val),
                        'uplink': self.main_window.txdoppler_val.text() if hasattr(self.main_window.txdoppler_val, 'text') else str(self.main_window.txdoppler_val)
                    }
            except (RuntimeError, AttributeError):
                pass
                
            # Safely add rotator enabled flag
            try:
                state['rotator_enabled'] = getattr(self.main_window, 'ROTATOR_ENABLED', False)
            except (RuntimeError, AttributeError):
                state['rotator_enabled'] = False
            
            # Safely add rotator info
            try:
                if state['rotator_enabled'] and hasattr(self.main_window, 'rotator'):
                    # Get actual rotator position from the rotator device
                    if self.main_window.rotator:
                        az, el = self.main_window.rotator.get_position()
                        if az is not None and el is not None:
                            az = f"{float(az):.1f}"
                            el = f"{float(el):.1f}"
                        else:
                            az = "error"
                            el = "error"
                    else:
                        az = "error"
                        el = "error"
                    
                    state['rotator'] = {
                        'azimuth': az,
                        'elevation': el
                    }
            except (RuntimeError, AttributeError):
                pass
                
        except Exception as e:
            # Catch any other unexpected errors and stop heartbeat
            logging.error(f"Error in get_current_state: {e}")
            self.should_run_heartbeat = False
            return {}
        
        return state
    
    def send_full_status(self):
        """Send full status update to the server"""
        if self.connected and self.main_window:
            try:
                self.sio.emit('heartbeat', {'state': self.get_current_state()})
            except Exception as e:
                logging.error(f"Error sending full status: {e}")
    
    def send_satellite_list(self):
        """Send satellite list to the server"""
        if not self.connected or not self.main_window:
            return
        
        try:
            # Try to load satellite list from main window
            satellite_list = []
            
            # Try to get SQF file path
            sqffile = None
            if hasattr(self.main_window, 'SQFILE'):
                sqffile = self.main_window.SQFILE
            elif hasattr(self.main_window, 'configur') and hasattr(self.main_window.configur, 'get'):
                sqffile = self.main_window.configur.get('satellite', 'sqffile', fallback=None)
            
            if not sqffile:
                import sys
                import os
                # Try finding it in the module                
                if hasattr(self.main_window, '__module__') and self.main_window.__module__ in sys.modules:
                    module = sys.modules[self.main_window.__module__]
                    if hasattr(module, 'SQFILE'):
                        sqffile = module.SQFILE
                  # Default fallback
                if not sqffile:
                    sqffile = 'doppler.sqf'
                # Read the file
            try:
                with open(sqffile, 'r') as f:
                    sqfdata = f.readlines()
                    for line in sqfdata:
                        # Skip comment lines
                        if line.strip().startswith(';'):
                            continue
                            
                        parts = line.strip().split(',')
                        if len(parts) > 0:
                            sat_name = parts[0].strip()
                            if sat_name and sat_name not in satellite_list:
                                satellite_list.append(sat_name)
                
                # Send the list to the server
                self.sio.emit('update_satellite_list', {'satellites': satellite_list})
                logging.info(f"Sent satellite list: {len(satellite_list)} satellites")
                
            except Exception as e:
                logging.error(f"Error reading satellite list: {e}")
        
        except Exception as e:
            logging.error(f"Error sending satellite list: {e}")
    
    def send_transponder_list(self, satellite_name):
        """Send transponder list for a specific satellite to the server"""
        if not self.connected or not self.main_window:
            return
        
        try:
            # Try to get SQF file path
            sqffile = None
            if hasattr(self.main_window, 'SQFILE'):
                sqffile = self.main_window.SQFILE
            elif hasattr(self.main_window, 'configur') and hasattr(self.main_window.configur, 'get'):
                sqffile = self.main_window.configur.get('satellite', 'sqffile', fallback=None)
            
            if not sqffile:
                import sys
                import os
                # Try finding it in the module
                if hasattr(self.main_window, '__module__') and self.main_window.__module__ in sys.modules:
                    module = sys.modules[self.main_window.__module__]
                    if hasattr(module, 'SQFILE'):
                        sqffile = module.SQFILE
                  # Default fallback
                if not sqffile:
                    sqffile = 'doppler.sqf'
            
            # Read the file and extract transponders for the requested satellite
            tpxlist = []
            with open(sqffile, 'r') as f:
                sqfdata = f.readlines()
                for line in sqfdata:
                    # Skip comment lines
                    if line.strip().startswith(';'):
                        continue
                        
                    parts = line.strip().split(',')
                    if len(parts) > 8 and parts[0].strip() == satellite_name:  # Ensure we have enough parts including the mode name
                        mode_name = parts[8].strip()  # Last field is the mode name
                        if mode_name and mode_name not in tpxlist:
                            tpxlist.append(mode_name)
            
            # Send the list to the server
            self.sio.emit('update_transponder_list', {
                'satellite': satellite_name,
                'transponders': tpxlist
            })
            logging.info(f"Sent transponder list: {len(tpxlist)} transponders for {satellite_name}")
            
        except Exception as e:
            logging.error(f"Error sending transponder list: {e}")
      # Command handlers
    def on_cmd_start_tracking(self, data=None):
        """Handle start tracking command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            self.main_window.web_api_proxy.start_tracking.emit()
            # Send updated status back
            self.send_full_status()
    
    def on_cmd_stop_tracking(self, data=None):
        """Handle stop tracking command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            self.main_window.web_api_proxy.stop_tracking.emit()
            # Send updated status back
            self.send_full_status()
    
    def on_cmd_select_satellite(self, data):
        """Handle select satellite command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            sat_name = data.get('satellite')
            if sat_name:
                self.main_window.web_api_proxy.select_satellite.emit(sat_name)
                # After selection, send the transponder list for this satellite
                self.send_transponder_list(sat_name)
                # Send updated status back
                self.send_full_status()
    
    def on_cmd_select_transponder(self, data):
        """Handle select transponder command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            tpx_name = data.get('transponder')
            if tpx_name:
                self.main_window.web_api_proxy.select_transponder.emit(tpx_name)
                # Send updated status back
                self.send_full_status()
    
    def on_cmd_set_subtone(self, data):
        """Handle set subtone command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            tone = data.get('subtone')
            if tone is not None:
                self.main_window.web_api_proxy.set_subtone.emit(tone)
                # Send updated status back
                self.send_full_status()
    
    def on_cmd_set_rx_offset(self, data):
        """Handle set RX offset command from server"""
        if self.main_window and hasattr(self.main_window, 'web_api_proxy'):
            try:
                offset = int(data.get('offset', 0))
                self.main_window.web_api_proxy.set_rx_offset.emit(offset)
                # Send updated status back
                self.send_full_status()
            except (ValueError, TypeError):
                logging.warning(f"Invalid RX offset value: {data.get('offset')}")
    def on_cmd_park_rotator(self, data=None):
        """Handle park rotator command from server"""
        if self.main_window and hasattr(self.main_window, 'park_rotators'):
            self.main_window.park_rotators()
            # Send updated status back
            self.send_full_status()
    
    def on_cmd_stop_rotator(self, data=None):
        """Handle stop rotator command from server"""
        if self.main_window and hasattr(self.main_window, 'stop_rotators'):
            self.main_window.stop_rotators()
            # Send updated status back
            self.send_full_status()
    
    def on_cmd_get_transponder_list(self, data):
        """Handle get transponder list command from server"""
        satellite_name = data.get('satellite')
        if satellite_name:
            self.send_transponder_list(satellite_name)
    
    # Audio stream handlers
    def on_cmd_start_audio_tx(self, data=None):
        """Handle start audio transmission command from server"""
        if not self.audio_streamer:
            logging.warning("Audio streamer not available")
            self.send_audio_error("Audio streamer not initialized")
            return
        
        try:
            if self.audio_streamer.start_streaming():
                # Ensure RX streaming is also active (start if not already)
                if self.audio_streamer.enabled and not self.audio_streamer.is_rx_active():
                    self.audio_streamer.start_rx_streaming(rx_callback=self.send_rx_audio_data)
                self.send_audio_tx_status(active=True, muted=self.audio_streamer.is_muted())
            else:
                self.send_audio_error("Failed to start audio streaming")
        except Exception as e:
            logging.error(f"Error starting audio TX: {e}")
            self.send_audio_error(f"Error starting audio TX: {str(e)}")
    
    def on_cmd_stop_audio_tx(self, data=None):
        """Handle stop audio transmission command from server"""
        if not self.audio_streamer:
            return
        
        try:
            self.audio_streamer.stop_streaming()
            # Note: We keep RX streaming active even when TX stops
            # This allows users to continue listening to the radio
            # RX streaming will stop when remote audio is disabled
            self.send_audio_tx_status(active=False, muted=False)
        except Exception as e:
            logging.error(f"Error stopping audio TX: {e}")
            self.send_audio_error(f"Error stopping audio TX: {str(e)}")
    
    def on_cmd_audio_data(self, data):
        """Handle audio data from server"""
        if not self.audio_streamer or not self.audio_streamer.is_active():
            return
        
        try:
            import numpy as np
            # Data should be binary PCM 16-bit signed integer
            # Socket.IO may send it as bytes, list, or array
            if isinstance(data, bytes):
                # Convert bytes to numpy array
                audio_array = np.frombuffer(data, dtype=np.int16)
            elif isinstance(data, bytearray):
                # Convert bytearray to numpy array
                audio_array = np.frombuffer(bytes(data), dtype=np.int16)
            elif isinstance(data, (list, tuple)):
                # Convert list/tuple to numpy array
                audio_array = np.array(data, dtype=np.int16)
            elif hasattr(data, '__array__'):
                # Handle numpy arrays or array-like objects
                audio_array = np.asarray(data, dtype=np.int16)
            else:
                logging.warning(f"Unexpected audio data type: {type(data)}")
                return
            
            self.audio_streamer.add_audio_data(audio_array)
        except Exception as e:
            logging.error(f"Error processing audio data: {e}")
    
    def on_cmd_mute_tx(self, data=None):
        """Handle mute TX command from server"""
        if not self.audio_streamer:
            return
        
        try:
            self.audio_streamer.mute()
            self.send_audio_tx_status(active=self.audio_streamer.is_active(), muted=True)
        except Exception as e:
            logging.error(f"Error muting audio TX: {e}")
            self.send_audio_error(f"Error muting audio TX: {str(e)}")
    
    def on_cmd_unmute_tx(self, data=None):
        """Handle unmute TX command from server"""
        if not self.audio_streamer:
            return
        
        try:
            self.audio_streamer.unmute()
            self.send_audio_tx_status(active=self.audio_streamer.is_active(), muted=False)
        except Exception as e:
            logging.error(f"Error unmuting audio TX: {e}")
            self.send_audio_error(f"Error unmuting audio TX: {str(e)}")
    
    def send_audio_tx_status(self, active=False, muted=False):
        """Send audio TX status update to server"""
        if self.connected:
            try:
                self.sio.emit('audio_tx_status', {
                    'active': active,
                    'muted': muted
                })
            except Exception as e:
                logging.error(f"Error sending audio TX status: {e}")
    
    def send_audio_error(self, error_message):
        """Send audio error notification to server"""
        if self.connected:
            try:
                self.sio.emit('audio_error', {
                    'error': error_message
                })
            except Exception as e:
                logging.error(f"Error sending audio error: {e}")
    
    def send_rx_audio_data(self, audio_data):
        """Send RX audio data to server"""
        if self.connected:
            try:
                # Convert numpy array to bytes (PCM 16-bit signed integer)
                if hasattr(audio_data, 'tobytes'):
                    audio_bytes = audio_data.tobytes()
                else:
                    audio_bytes = bytes(audio_data)
                
                # Send to server
                self.sio.emit('rx_audio_data', audio_bytes)
            except Exception as e:
                logging.error(f"Error sending RX audio data: {e}")

# Create a singleton instance
remote_client = RemoteClient()

# Functions to be called from the main application
def register_window(window):
    """Register the main application window with the remote client"""
    # Read config to get the remote server URL
    config = configparser.ConfigParser()
    try:
        config.read('config.ini')
        enable_remote = config.getboolean('remote_server', 'enable', fallback=False)
        remote_url = config.get('remote_server', 'url', fallback='http://localhost:5001')
        
        if enable_remote:
            # Update the remote client URL
            remote_client.server_url = remote_url
            # Register the window
            remote_client.register_window(window)
            # Connect to the remote server
            remote_client.connect()
            logging.info(f"Remote client enabled, connecting to {remote_url}")
        else:
            logging.info("Remote client disabled in config")
    except Exception as e:
        logging.error(f"Error initializing remote client: {e}")

def broadcast_satellite_change(satellite_name):
    """Broadcast satellite changes"""
    if remote_client.connected and satellite_name:
        remote_client.send_full_status()
        # Also send updated transponder list
        remote_client.send_transponder_list(satellite_name)

def broadcast_transponder_change(transponder_name):
    """Broadcast transponder changes"""
    if remote_client.connected and transponder_name:
        remote_client.send_full_status()

def broadcast_subtone_change(subtone):
    """Broadcast subtone changes"""
    if remote_client.connected and subtone is not None:
        remote_client.send_full_status()

def broadcast_tracking_state(is_tracking):
    """Broadcast tracking state changes"""
    if remote_client.connected:
        remote_client.send_full_status()

def broadcast_full_status():
    """Broadcast full status update"""
    if remote_client.connected:
        remote_client.send_full_status()

def disconnect():
    """Disconnect from the remote server"""
    remote_client.disconnect()
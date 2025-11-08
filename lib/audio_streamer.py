"""
Audio streaming module for remote audio transmission
Handles audio I/O for browser-based remote audio transmission
"""

import threading
import sounddevice as sd
import numpy as np
import logging
import queue
import time


class AudioStreamer:
    """Manages audio streaming for remote transmission"""
    
    def __init__(self, config, pass_recorder=None):
        """
        Initialize audio streamer
        
        Args:
            config: ConfigParser object with remote_audio section
            pass_recorder: Optional PassRecorder instance to check for device conflicts
        """
        self.config = config
        self.pass_recorder = pass_recorder
        self.load_config(config)
        
        self.stream = None  # TX output stream
        self.rx_stream = None  # RX input stream
        self.stream_thread = None
        self.audio_queue = queue.Queue(maxsize=10)  # Buffer for incoming audio chunks
        self._stop_event = threading.Event()
        self.muted = False
        self.volume = 1.0  # Normal volume
        self.active = False
        self.rx_active = False
        self.device_info = None
        self.rx_device_info = None
        self.rx_callback = None  # Callback function for RX audio data
        
        # Check audio devices at startup
        try:
            devices = sd.query_devices()
            output_devices = [dev for dev in devices if dev.get('max_output_channels', 0) > 0]
            logging.info(f"Audio streamer initialized: Found {len(output_devices)} audio output devices")
        except Exception as e:
            logging.error(f"Error checking audio devices at startup: {e}")
    
    def load_config(self, config):
        """Load configuration from config parser"""
        self.enabled = config.getboolean('remote_audio', 'enabled', fallback=False)
        self.tx_soundcard = config.get('remote_audio', 'tx_soundcard', fallback='default')
        self.rx_soundcard = config.get('remote_audio', 'rx_soundcard', fallback='default')
        self.sample_rate = config.getint('remote_audio', 'sample_rate', fallback=44100)
        self.channels = config.getint('remote_audio', 'channels', fallback=1)
    
    def update_config(self, config):
        """Update configuration"""
        old_enabled = self.enabled
        self.load_config(config)
        
        # If disabled, stop streaming
        if not self.enabled and old_enabled:
            self.stop_streaming()
            self.stop_rx_streaming()
    
    def find_tx_device(self):
        """Find the appropriate TX audio output device"""
        try:
            device = None
            device_name = None
            device_info = None
            
            devices = sd.query_devices()
            
            # Try to use the configured device
            if self.tx_soundcard != 'default':
                # First try to find by exact name
                for i, dev in enumerate(devices):
                    if dev['name'] == self.tx_soundcard and dev.get('max_output_channels', 0) > 0:
                        try:
                            # Quick test
                            with sd.OutputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = i
                            device_name = dev['name']
                            device_info = dev
                            logging.info(f"Selected TX device '{dev['name']}' (index {i})")
                            break
                        except Exception as e:
                            logging.warning(f"TX device {i} ({dev['name']}) not available: {e}")
                
                # Try partial name matches
                if device is None:
                    for i, dev in enumerate(devices):
                        if (self.tx_soundcard in dev['name'] or dev['name'] in self.tx_soundcard) and dev.get('max_output_channels', 0) > 0:
                            try:
                                with sd.OutputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                    pass
                                device = i
                                device_name = dev['name']
                                device_info = dev
                                logging.info(f"Selected similar TX device '{dev['name']}' (index {i})")
                                break
                            except Exception as e:
                                logging.warning(f"Similar TX device {i} ({dev['name']}) not available: {e}")
                
                # Try as index
                if device is None:
                    try:
                        index = int(self.tx_soundcard)
                        if 0 <= index < len(devices) and devices[index].get('max_output_channels', 0) > 0:
                            try:
                                with sd.OutputStream(device=index, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                    pass
                                device = index
                                device_name = devices[index]['name']
                                device_info = devices[index]
                                logging.info(f"Selected TX device by index {index} ({device_name})")
                            except Exception as e:
                                logging.warning(f"Indexed TX device {index} not available: {e}")
                    except ValueError:
                        pass
            
            # Try default device
            if device is None:
                try:
                    default_device = sd.default.device[1]  # Output device
                    if default_device is not None and 0 <= default_device < len(devices):
                        try:
                            with sd.OutputStream(device=default_device, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = default_device
                            device_name = devices[default_device]['name']
                            device_info = devices[default_device]
                            logging.info(f"Selected default TX device {device_name} (index {device})")
                        except Exception as e:
                            logging.warning(f"Default TX device not available: {e}")
                except Exception as e:
                    logging.warning(f"Error getting default TX device: {e}")
            
            # Last resort: try all output devices
            if device is None:
                for i, dev in enumerate(devices):
                    if dev.get('max_output_channels', 0) > 0:
                        try:
                            with sd.OutputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = i
                            device_name = dev['name']
                            device_info = dev
                            logging.info(f"Found working TX device: {device_name} (index {i})")
                            break
                        except Exception as e:
                            logging.debug(f"TX device {i} ({dev['name']}) not available: {e}")
            
            if device is None:
                logging.error("No working TX audio output device found")
                return None, None
            
            self.device_info = device_info
            return device, device_name
            
        except Exception as e:
            logging.error(f"Error finding TX audio device: {e}", exc_info=True)
            return None, None
    
    def start_streaming(self):
        """Start audio streaming"""
        if self.active or not self.enabled:
            return
        
        device, device_name = self.find_tx_device()
        if device is None:
            logging.error("Cannot start audio streaming: no TX device available")
            return False
        
        self.active = True
        self._stop_event.clear()
        self.audio_queue = queue.Queue(maxsize=10)
        
        try:
            def audio_callback(outdata, frames, time_info, status):
                """Callback for audio output stream"""
                if status:
                    logging.warning(f"Audio output status: {status}")
                
                try:
                    # Get audio data from queue
                    try:
                        audio_chunk = self.audio_queue.get_nowait()
                        # Apply volume (mute if muted)
                        if self.muted:
                            outdata[:] = np.zeros((frames, self.channels), dtype='float32')
                        else:
                            # Ensure correct shape and apply volume
                            if len(audio_chunk.shape) == 1:
                                audio_chunk = audio_chunk.reshape(-1, 1)
                            if audio_chunk.shape[0] < frames:
                                # Pad with zeros if chunk is smaller
                                padding = np.zeros((frames - audio_chunk.shape[0], self.channels), dtype='float32')
                                audio_chunk = np.vstack([audio_chunk, padding])
                            elif audio_chunk.shape[0] > frames:
                                # Truncate if chunk is larger
                                audio_chunk = audio_chunk[:frames]
                            outdata[:] = (audio_chunk * self.volume).astype('float32')
                    except queue.Empty:
                        # No data available, output silence
                        outdata[:] = np.zeros((frames, self.channels), dtype='float32')
                except Exception as e:
                    logging.error(f"Error in audio callback: {e}")
                    outdata[:] = np.zeros((frames, self.channels), dtype='float32')
            
            self.stream = sd.OutputStream(
                device=device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='float32',
                callback=audio_callback,
                blocksize=1024
            )
            
            self.stream.start()
            logging.info(f"Audio streaming started on device {device_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error starting audio stream: {e}", exc_info=True)
            self.active = False
            return False
    
    def stop_streaming(self):
        """Stop audio streaming"""
        if not self.active:
            return
        
        self.active = False
        self._stop_event.set()
        
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception as e:
                logging.error(f"Error stopping audio stream: {e}")
            finally:
                self.stream = None
        
        # Clear queue
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logging.info("Audio streaming stopped")
    
    def add_audio_data(self, audio_data):
        """
        Add audio data to the output stream
        
        Args:
            audio_data: numpy array of audio samples (PCM 16-bit signed integer)
        """
        if not self.active or self.stream is None:
            return
        
        try:
            # Convert from PCM 16-bit signed integer to float32 (-1.0 to 1.0)
            if audio_data.dtype != np.float32:
                if audio_data.dtype == np.int16:
                    audio_data = audio_data.astype(np.float32) / 32768.0
                elif audio_data.dtype == np.int32:
                    audio_data = audio_data.astype(np.float32) / 2147483648.0
                else:
                    audio_data = audio_data.astype(np.float32)
            
            # Ensure correct shape
            if len(audio_data.shape) == 1:
                audio_data = audio_data.reshape(-1, 1)
            
            # Add to queue (non-blocking, drop if queue is full)
            try:
                self.audio_queue.put_nowait(audio_data)
            except queue.Full:
                logging.warning("Audio queue full, dropping audio chunk")
                
        except Exception as e:
            logging.error(f"Error adding audio data: {e}")
    
    def mute(self):
        """Mute audio output"""
        self.muted = True
        logging.info("Audio output muted")
    
    def unmute(self):
        """Unmute audio output"""
        self.muted = False
        logging.info("Audio output unmuted")
    
    def is_active(self):
        """Check if streaming is active"""
        return self.active
    
    def is_muted(self):
        """Check if audio is muted"""
        return self.muted
    
    def find_rx_device(self):
        """Find the appropriate RX audio input device"""
        try:
            device = None
            device_name = None
            device_info = None
            
            devices = sd.query_devices()
            
            # Try to use the configured device
            if self.rx_soundcard != 'default':
                # First try to find by exact name
                for i, dev in enumerate(devices):
                    if dev['name'] == self.rx_soundcard and dev.get('max_input_channels', 0) > 0:
                        try:
                            # Quick test
                            with sd.InputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = i
                            device_name = dev['name']
                            device_info = dev
                            logging.info(f"Selected RX device '{dev['name']}' (index {i})")
                            break
                        except Exception as e:
                            logging.warning(f"RX device {i} ({dev['name']}) not available: {e}")
                
                # Try partial name matches
                if device is None:
                    for i, dev in enumerate(devices):
                        if (self.rx_soundcard in dev['name'] or dev['name'] in self.rx_soundcard) and dev.get('max_input_channels', 0) > 0:
                            try:
                                with sd.InputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                    pass
                                device = i
                                device_name = dev['name']
                                device_info = dev
                                logging.info(f"Selected similar RX device '{dev['name']}' (index {i})")
                                break
                            except Exception as e:
                                logging.warning(f"Similar RX device {i} ({dev['name']}) not available: {e}")
                
                # Try as index
                if device is None:
                    try:
                        index = int(self.rx_soundcard)
                        if 0 <= index < len(devices) and devices[index].get('max_input_channels', 0) > 0:
                            try:
                                with sd.InputStream(device=index, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                    pass
                                device = index
                                device_name = devices[index]['name']
                                device_info = devices[index]
                                logging.info(f"Selected RX device by index {index} ({device_name})")
                            except Exception as e:
                                logging.warning(f"Indexed RX device {index} not available: {e}")
                    except ValueError:
                        pass
            
            # Try default device
            if device is None:
                try:
                    default_device = sd.default.device[0]  # Input device
                    if default_device is not None and 0 <= default_device < len(devices):
                        try:
                            with sd.InputStream(device=default_device, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = default_device
                            device_name = devices[default_device]['name']
                            device_info = devices[default_device]
                            logging.info(f"Selected default RX device {device_name} (index {device})")
                        except Exception as e:
                            logging.warning(f"Default RX device not available: {e}")
                except Exception as e:
                    logging.warning(f"Error getting default RX device: {e}")
            
            # Last resort: try all input devices
            if device is None:
                for i, dev in enumerate(devices):
                    if dev.get('max_input_channels', 0) > 0:
                        try:
                            with sd.InputStream(device=i, channels=1, samplerate=44100, blocksize=1024, callback=lambda *args: None):
                                pass
                            device = i
                            device_name = dev['name']
                            device_info = dev
                            logging.info(f"Found working RX device: {device_name} (index {i})")
                            break
                        except Exception as e:
                            logging.debug(f"RX device {i} ({dev['name']}) not available: {e}")
            
            if device is None:
                logging.warning("No working RX audio input device found")
                return None, None
            
            self.rx_device_info = device_info
            return device, device_name
            
        except Exception as e:
            logging.error(f"Error finding RX audio device: {e}", exc_info=True)
            return None, None
    
    def start_rx_streaming(self, rx_callback=None):
        """Start RX audio streaming (capture from radio)"""
        if self.rx_active or not self.enabled:
            return False
        
        device, device_name = self.find_rx_device()
        if device is None:
            logging.warning("Cannot start RX audio streaming: no RX device available")
            return False
        
        self.rx_callback = rx_callback
        self.rx_active = True
        
        try:
            def rx_audio_callback(indata, frames, time_info, status):
                """Callback for RX audio input stream"""
                if status:
                    if status.input_overflow:
                        logging.debug("RX audio input overflow")
                    else:
                        logging.warning(f"RX audio input status: {status}")
                
                try:
                    # Convert float32 to int16 PCM for transmission
                    if indata.dtype == np.float32:
                        # Clip to valid range and convert to int16
                        indata_clipped = np.clip(indata, -1.0, 1.0)
                        audio_int16 = (indata_clipped * 32767.0).astype(np.int16)
                    else:
                        audio_int16 = indata.astype(np.int16)
                    
                    # Flatten if multi-channel
                    if len(audio_int16.shape) > 1:
                        audio_int16 = audio_int16.flatten()
                    
                    # Call the callback if registered
                    if self.rx_callback:
                        try:
                            self.rx_callback(audio_int16)
                        except Exception as e:
                            logging.error(f"Error in RX audio callback: {e}")
                            
                except Exception as e:
                    logging.error(f"Error processing RX audio: {e}")
            
            self.rx_stream = sd.InputStream(
                device=device,
                channels=self.channels,
                samplerate=self.sample_rate,
                dtype='float32',
                callback=rx_audio_callback,
                blocksize=4096  # Larger blocksize for RX to reduce overhead
            )
            
            self.rx_stream.start()
            logging.info(f"RX audio streaming started on device {device_name}")
            return True
            
        except Exception as e:
            logging.error(f"Error starting RX audio stream: {e}", exc_info=True)
            self.rx_active = False
            return False
    
    def stop_rx_streaming(self):
        """Stop RX audio streaming"""
        if not self.rx_active:
            return
        
        self.rx_active = False
        self.rx_callback = None
        
        if self.rx_stream:
            try:
                self.rx_stream.stop()
                self.rx_stream.close()
            except Exception as e:
                logging.error(f"Error stopping RX audio stream: {e}")
            finally:
                self.rx_stream = None
        
        logging.info("RX audio streaming stopped")
    
    def is_rx_active(self):
        """Check if RX streaming is active"""
        return self.rx_active

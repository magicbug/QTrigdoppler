import serial
import threading
import time

class YaesuRotator:
    def __init__(self, port, baudrate=4800, az_min=0, az_max=450, el_min=0, el_max=180, timeout=1):
        self.ser = serial.Serial(
            port,
            baudrate,
            timeout=timeout,
            rtscts=False,   # Hardware flow control OFF
            xonxoff=False   # Software flow control OFF
        )
        self.az_min = az_min
        self.az_max = az_max
        self.el_min = el_min
        self.el_max = el_max
        self.lock = threading.Lock()
        
        # Add position caching to reduce serial communication
        self._cached_position = (None, None)
        self._last_position_time = 0
        self._position_cache_timeout = 0.5  # Cache position for 500ms

    def set_position(self, az, el):
        try:
            az = float(az)
            el = float(el)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid az/el values: az={az}, el={el}")
        az = max(self.az_min, min(self.az_max, int(round(az))))
        el = max(self.el_min, min(self.el_max, int(round(el))))
        cmd = f"W{az:03d} {el:03d}\r"
        print(f"YaesuRotator: Sending command '{cmd.strip()}' to hardware")
        with self.lock:
            self.ser.write(cmd.encode())
            time.sleep(0.05)  # Reduced from 0.1 to 0.05
        
        # Update cache with commanded position
        self._cached_position = (az, el)
        self._last_position_time = time.time()

    def park(self, az_park, el_park):
        self.set_position(az_park, el_park)

    def stop(self):
        with self.lock:
            self.ser.write(b'S\r')

    def get_position(self, use_cache=True):
        """
        Get rotator position with optional caching to reduce serial communication
        
        Args:
            use_cache: If True, return cached position if recent enough
            
        Returns:
            Tuple of (azimuth, elevation) or (None, None) if error
        """
        current_time = time.time()
        
        # Use cache if available and recent
        if use_cache and self._cached_position[0] is not None:
            if current_time - self._last_position_time < self._position_cache_timeout:
                return self._cached_position
        
        # Get fresh position from rotator
        with self.lock:
            try:
                self.ser.reset_input_buffer()
                self.ser.write(b'C2\r')
                time.sleep(0.05)  # Reduced from 0.1 to 0.05
                response = self.ser.readline().decode(errors='ignore').strip()
                
                az = None
                el = None
                parts = response.split()
                for part in parts:
                    if part.startswith('AZ='):
                        az = int(part[3:])
                    elif part.startswith('EL='):
                        el = int(part[3:])
                
                if az is not None and el is not None:
                    # Update cache
                    self._cached_position = (az, el)
                    self._last_position_time = current_time
                    return az, el
                
                # Fallback: try single queries if C2 didn't work
                if az is None:
                    self.ser.write(b'C\r')
                    time.sleep(0.05)  # Reduced from 0.1 to 0.05
                    az_response = self.ser.readline().decode(errors='ignore').strip()
                    if az_response.startswith('AZ='):
                        az = int(az_response[3:])
                
                if el is None:
                    self.ser.write(b'B\r')
                    time.sleep(0.05)  # Reduced from 0.1 to 0.05
                    el_response = self.ser.readline().decode(errors='ignore').strip()
                    if el_response.startswith('EL='):
                        el = int(el_response[3:])
                
                if az is not None and el is not None:
                    # Update cache
                    self._cached_position = (az, el)
                    self._last_position_time = current_time
                    return az, el
                    
            except Exception as e:
                print(f"Error parsing rotator position: {e}, response: {response}")
            
            return None, None

    def close(self):
        with self.lock:
            self.ser.close()

class RotatorThread(threading.Thread):
    def __init__(self, rotator, get_az_el_func, min_elevation, az_park, el_park, poll_interval=1.0, on_park_callback=None, best_az_func=None, az_max=450):
        super().__init__()
        self.rotator = rotator
        self.get_az_el = get_az_el_func  # function returning (az, el)
        self.min_elevation = min_elevation
        self.az_park = az_park
        self.el_park = el_park
        self.poll_interval = poll_interval
        self.on_park_callback = on_park_callback  # callback when rotator parks
        self.best_az_func = best_az_func  # function(current_az, target_az, az_max)
        self.az_max = az_max
        self.running = threading.Event()
        self.running.set()
        self.parked = False
        self.last_az = None
        self.last_el = None
        
        # Intelligent position checking based on state
        self._last_position_check = 0
        self._position_check_interval = 2.0  # Default: check every 2 seconds
        self._last_movement_time = 0
        self._movement_timeout = 5.0  # Consider rotator stopped after 5 seconds of no movement
        self._is_moving = False
        self._consecutive_no_movement = 0
        self._max_no_movement_count = 3  # After 3 consecutive checks with no movement, reduce polling

    def run(self):
        while self.running.is_set():
            try:
                az, el = self.get_az_el()
                current_time = time.time()
                
                # Intelligent position checking frequency
                should_check_position = False
                
                if el >= self.min_elevation:
                    # Satellite is visible - check position more frequently
                    if current_time - self._last_position_check >= self._position_check_interval:
                        should_check_position = True
                        # Reduce interval when actively tracking
                        self._position_check_interval = 1.0
                elif el >= -10:
                    # Satellite approaching horizon - check position moderately
                    if current_time - self._last_position_check >= self._position_check_interval:
                        should_check_position = True
                        # Moderate interval when approaching horizon
                        self._position_check_interval = 3.0
                else:
                    # Satellite well below horizon - check position less frequently
                    if current_time - self._last_position_check >= self._position_check_interval:
                        should_check_position = True
                        # Increase interval when well below horizon
                        self._position_check_interval = 10.0
                
                current_az = None
                if should_check_position:
                    current_az, _ = self.rotator.get_position(use_cache=True)  # Use cache
                    self._last_position_check = current_time
                    # Only log position checks when elevation changes significantly or when moving
                    if (not hasattr(self, '_last_logged_el') or 
                        abs(el - self._last_logged_el) > 5 or 
                        self._is_moving or 
                        el >= -5):
                        print(f"RotatorThread: Position check (interval={self._position_check_interval:.1f}s, moving={self._is_moving}, el={el:.1f}°)")
                        self._last_logged_el = el
                    
                    # Check if rotator is moving
                    if self.last_az is not None and current_az is not None:
                        az_diff = abs(current_az - self.last_az)
                        if az_diff > 0.5:  # Significant movement
                            self._is_moving = True
                            self._last_movement_time = current_time
                            self._consecutive_no_movement = 0
                            # When moving, check position more frequently
                            self._position_check_interval = 0.5
                        else:
                            self._consecutive_no_movement += 1
                            if self._consecutive_no_movement >= self._max_no_movement_count:
                                self._is_moving = False
                                # When not moving, check position less frequently
                                self._position_check_interval = 2.0
                
                if el >= self.min_elevation:
                    # The azimuth from get_az_el should already be optimized if route optimization is active
                    # Only apply best_az_func if the azimuth is in the 0-360 range (indicating no optimization)
                    if self.best_az_func and current_az is not None and az <= 360:
                        az_to_send = self.best_az_func(current_az, az, self.az_max)
                    else:
                        az_to_send = az
                    send = False
                    if self.last_az is None or self.last_el is None:
                        send = True
                    elif abs(az_to_send - self.last_az) >= 1 or abs(el - self.last_el) >= 1:
                        send = True
                    if send:
                        print(f"RotatorThread: Moving to az={az_to_send:.1f}° el={el:.1f}° (original az={az:.1f}°)")
                        print(f"RotatorThread: Sending command W{int(round(az_to_send)):03d} {int(round(el)):03d}")
                        self.rotator.set_position(az_to_send, el)
                        self.last_az = az_to_send
                        self.last_el = el
                        # Reset movement tracking when we send a command
                        self._is_moving = True
                        self._last_movement_time = current_time
                        self._consecutive_no_movement = 0
                    self.parked = False
                else:
                    if not self.parked:
                        # Use best azimuth logic for parking too
                        if self.best_az_func and current_az is not None:
                            park_az = self.best_az_func(current_az, self.az_park, self.az_max)
                        else:
                            park_az = self.az_park
                        self.rotator.park(park_az, self.el_park)
                        self.parked = True
                        self.last_az = park_az
                        self.last_el = self.el_park
                        # Notify main application that rotator has parked
                        if self.on_park_callback:
                            try:
                                self.on_park_callback()
                            except Exception as e:
                                print(f"Error in park callback: {e}")
            except Exception as e:
                # Log or handle error as needed
                print(f"RotatorThread error: {e}")
            time.sleep(self.poll_interval)

    def stop(self):
        self.running.clear()
        try:
            self.rotator.stop()
        except Exception as e:
            print(f"Error stopping rotator: {e}")
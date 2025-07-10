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

    def set_position(self, az, el):
        try:
            az = float(az)
            el = float(el)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid az/el values: az={az}, el={el}")
        az = max(self.az_min, min(self.az_max, int(round(az))))
        el = max(self.el_min, min(self.el_max, int(round(el))))
        cmd = f"W{az:03d} {el:03d}\r"
        with self.lock:
            self.ser.write(cmd.encode())
            time.sleep(0.1)

    def park(self, az_park, el_park):
        self.set_position(az_park, el_park)

    def stop(self):
        with self.lock:
            self.ser.write(b'S\r')

    def get_position(self):
        with self.lock:
            self.ser.reset_input_buffer()
            self.ser.write(b'C2\r')
            time.sleep(0.1)
            response = self.ser.readline().decode(errors='ignore').strip()
            try:
                # Expected: 'AZ=aaa EL=eee' or just 'AZ=aaa' or 'EL=eee'
                az = None
                el = None
                parts = response.split()
                for part in parts:
                    if part.startswith('AZ='):
                        az = int(part[3:])
                    elif part.startswith('EL='):
                        el = int(part[3:])
                if az is not None and el is not None:
                    return az, el
                # fallback: try single queries if C2 didn't work
                if az is None:
                    self.ser.write(b'C\r')
                    time.sleep(0.1)
                    az_response = self.ser.readline().decode(errors='ignore').strip()
                    if az_response.startswith('AZ='):
                        az = int(az_response[3:])
                if el is None:
                    self.ser.write(b'B\r')
                    time.sleep(0.1)
                    el_response = self.ser.readline().decode(errors='ignore').strip()
                    if el_response.startswith('EL='):
                        el = int(el_response[3:])
                if az is not None and el is not None:
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

    def run(self):
        while self.running.is_set():
            try:
                az, el = self.get_az_el()
                current_az, _ = self.rotator.get_position()
                if el >= self.min_elevation:
                    # Always use best azimuth logic if available
                    if self.best_az_func and current_az is not None:
                        az_to_send = self.best_az_func(current_az, az, self.az_max)
                    else:
                        az_to_send = az
                    send = False
                    if self.last_az is None or self.last_el is None:
                        send = True
                    elif abs(az_to_send - self.last_az) >= 1 or abs(el - self.last_el) >= 1:
                        send = True
                    if send:
                        self.rotator.set_position(az_to_send, el)
                        self.last_az = az_to_send
                        self.last_el = el
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
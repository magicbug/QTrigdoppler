import serial
import threading
import time

class YaesuRotator:
    def __init__(self, port, baudrate=4800, az_min=0, az_max=450, el_min=0, el_max=180, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.az_min = az_min
        self.az_max = az_max
        self.el_min = el_min
        self.el_max = el_max
        self.lock = threading.Lock()

    def set_position(self, az, el):
        az = max(self.az_min, min(self.az_max, int(round(az))))
        el = max(self.el_min, min(self.el_max, int(round(el))))
        # Try lowercase with \n (old code style)
        cmd1 = f"az{az:03d} el{el:03d}\n"
        # Try uppercase with \r (GS-232 style)
        cmd2 = f"AZ{az:03d} EL{el:03d}\r"
        # Try uppercase with \n
        cmd3 = f"AZ{az:03d} EL{el:03d}\n"
        # Try lowercase with \r
        cmd4 = f"az{az:03d} el{el:03d}\r"
        for cmd in [cmd1, cmd2, cmd3, cmd4]:
            with self.lock:
                print(f"[Rotator] Sending position command: {repr(cmd)}")
                self.ser.write(cmd.encode())
                time.sleep(0.1)  # Give the controller a moment

    def park(self, az_park, el_park):
        self.set_position(az_park, el_park)

    def stop(self):
        with self.lock:
            print("[Rotator] Sending stop command: 'S'\n and 'S'\r")
            self.ser.write(b'S\n')
            time.sleep(0.05)
            self.ser.write(b'S\r')

    def close(self):
        with self.lock:
            self.ser.close()

    def get_position(self):
        responses = []
        # Try lowercase 'c' with \n, uppercase 'C' with \r, and both with both endings
        cmds = [b'c\n', b'C\n', b'c\r', b'C\r']
        for cmd in cmds:
            with self.lock:
                self.ser.reset_input_buffer()
                print(f"[Rotator] Sending get_position command: {repr(cmd)}")
                self.ser.write(cmd)
                time.sleep(0.1)
                response = self.ser.readline().decode(errors='ignore').strip()
                print(f"[Rotator] Raw response: {repr(response)}")
                responses.append(response)
                # Try to parse response
                try:
                    parts = response.split()
                    if len(parts) >= 2:
                        # Try both uppercase and lowercase prefixes
                        if parts[0].lower().startswith('az') and parts[1].lower().startswith('el'):
                            az = int(parts[0][2:])
                            el = int(parts[1][2:])
                            return az, el
                except Exception as e:
                    print(f"Error parsing rotator position: {e}, response: {response}")
        print(f"[Rotator] All responses tried, none parsed: {responses}")
        return None, None

class RotatorThread(threading.Thread):
    def __init__(self, rotator, get_az_el_func, min_elevation, az_park, el_park, poll_interval=1.0):
        super().__init__()
        self.rotator = rotator
        self.get_az_el = get_az_el_func  # function returning (az, el)
        self.min_elevation = min_elevation
        self.az_park = az_park
        self.el_park = el_park
        self.poll_interval = poll_interval
        self.running = threading.Event()
        self.running.set()
        self.parked = False
        self.last_az = None
        self.last_el = None

    def run(self):
        while self.running.is_set():
            try:
                az, el = self.get_az_el()
                if el >= self.min_elevation:
                    # Only send if az or el changed by at least 1 degree
                    send = False
                    if self.last_az is None or self.last_el is None:
                        send = True
                    elif abs(az - self.last_az) >= 1 or abs(el - self.last_el) >= 1:
                        send = True
                    if send:
                        self.rotator.set_position(az, el)
                        self.last_az = round(az)
                        self.last_el = round(el)
                    self.parked = False
                else:
                    if not self.parked:
                        self.rotator.park(self.az_park, self.el_park)
                        self.parked = True
                        self.last_az = self.az_park
                        self.last_el = self.el_park
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
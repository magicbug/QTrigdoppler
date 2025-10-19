"""
Original code: https://github.com/dl7oap/gp2icom
Created: by Andreas Puschendorf, DL7OAP
Date    : 09/2020

Modified: by Alex Krist, KR1ST from original by Andreas Puschendorf, DL7OAP
Date    : 11/2020
Comments: The original script has been adapted for use with the Icom IC-9100. The IC-9100 does 
          not support CAT control for RIT. I added some code to reject the echoed frames from
          the CI-V bus when "remote" jack is used on the radio rather than the USB port.

Modified: by Andreas Puschendorf, DL7OAP
Date    : 11/2020
Comments: to bring ic9100 and ic9700 together in one class the CI-V adress has to be given
          162 - default for IC9700 (162 = hex A2)
          124 - default for IC9100 (124 = hex 7C)
          
Modified: by Joshua Petry, DL3JOP
Date    : 09/2024
Comments: changed to IC-910 support, 9700/9100 deprecated     
"""

import serial
import time
import logging


class icom:

    def __init__(self, serialDevice, serialBaud, icomTrxCivAdress, radio_model='9700'):
        self.connected = False
        self.icomTrxCivAdress = icomTrxCivAdress
        self.serialDevice = serialDevice
        self.serialBaud = serialBaud
        self.radio_model = radio_model
        self.ser = serial.Serial()
        self.ser.baudrate = serialBaud
        self.ser.port = serialDevice
        self.ser.timeout = 1.0  # 1 second timeout for read operations
        self.ser.write_timeout = 1.0  # 1 second timeout for write operations
        self.ser.inter_byte_timeout = 0.1  # 100ms timeout between bytes
        self.ser.setDTR(0)
        self.ser.setRTS(0)
        try:
            self.ser.open()
            self.connected = True
            logging.info(f"Successfully connected to ICOM {radio_model} on {serialDevice} at {serialBaud} baud")
        except serial.SerialException as e:
            self.connected = False
            logging.error(f"Failed to connect to ICOM radio on {serialDevice}: {e}")
            print("Rig not connected, switching to dummy mode")
            self.last_set_frequency_a = 0 # per VFO
            self.last_set_frequency_b = 0
            self.current_vfo = "A"
        except Exception as e:
            self.connected = False
            logging.error(f"Unexpected error connecting to ICOM radio: {e}")
            print("Rig not connected, switching to dummy mode")
            self.last_set_frequency_a = 0 # per VFO
            self.last_set_frequency_b = 0
            self.current_vfo = "A"
    
            
    # gives a empty bytearray when data crc is not valid
    def __readFromIcom(self):
        if self.connected == True:
            time.sleep(0.05)
            b = bytearray()
            try:
                data = self.ser.read(1)
                if data:  # Only process if we got data
                    b = b + data
                    while self.ser.in_waiting:
                        b = b + self.ser.read(1)
            except serial.SerialTimeoutException:
                # Timeout occurred, return empty bytearray
                return bytearray()
            except serial.SerialException as e:
                logging.warning(f"Serial read error: {e}")
                self.connected = False
                return bytearray()
            # drop all but the last frame
            while b.count(b'\xfd') > 1:
                del b[0:b.find(b'\xfd') + 1]
            if len(b) > 0:
                # valid message
                validMsg = bytes([254, 254, 0, self.icomTrxCivAdress, 251, 253])
                if len(b) >= 6 and b[0:6] == validMsg:
                    b = b[6:len(b)]
                    if len(b) > 0:  # read answer from icom trx
                        if len(b) >= 2 and b[0] == 254 and b[1] == 254 and b[-1] == 253:  # check for valid data CRC
                            return b
                        else:
                            b = bytearray()
                    else:
                        b = bytearray()
                else:
                    if len(b) >= 2 and b[0] == 254 and b[1] == 254 and b[-1] == 253:  # check for valid data CRC
                        b = b
                    else:
                        b = bytearray()
            #print('   * readFromIcom return value: ', b)
            return b
        else:
            return bytearray()
        
    # gives a empty bytearray when data crc is not valid
    def __writeToIcom(self, b):
        """Single-attempt write - no retry. Used for frequency updates."""
        if self.connected == True:
            try:
                s = self.ser.write(bytes([254, 254, self.icomTrxCivAdress, 0]) + b + bytes([253]))
                self.ser.reset_input_buffer()
                #print('   * writeToIcom value: ', b)
                return self.__readFromIcom()
            except serial.SerialTimeoutException:
                logging.warning("Serial write timeout - radio may not be responding")
                return bytearray()
            except serial.SerialException as e:
                logging.warning(f"Serial write error: {e}")
                self.connected = False
                return bytearray()
        else:
            return bytearray()

    def __writeToIcomWithRetry(self, b, max_retries=2, retry_delay=0.1):
        """Write with retry logic. Used for setup commands that are less frequent."""
        if not self.connected:
            return bytearray()
            
        for attempt in range(max_retries + 1):
            try:
                s = self.ser.write(bytes([254, 254, self.icomTrxCivAdress, 0]) + b + bytes([253]))
                self.ser.reset_input_buffer()
                response = self.__readFromIcom()
                
                # Check if we got a valid response
                if len(response) > 0:
                    return response
                    
                # If no response and this isn't the last attempt, retry
                if attempt < max_retries:
                    logging.debug(f"CI-V command failed, retrying ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logging.warning(f"CI-V command failed after {max_retries + 1} attempts")
                    return bytearray()
                    
            except serial.SerialTimeoutException:
                if attempt < max_retries:
                    logging.debug(f"CI-V command timeout, retrying ({attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    logging.warning(f"CI-V command timeout after {max_retries + 1} attempts")
                    return bytearray()
            except serial.SerialException as e:
                logging.warning(f"Serial write error: {e}")
                self.connected = False
                return bytearray()
        
        return bytearray()

    def is_connected(self):
        return self.connected

    
    def close(self):
        try:
            if hasattr(self, 'ser') and self.ser.is_open:
                self.ser.close()
                logging.info("ICOM connection closed")
        except Exception as e:
            logging.warning(f"Error closing ICOM connection: {e}")

    def _validateFrequency(self, freq):
        """Validate frequency before sending to radio."""
        try:
            # Convert to integer, handling both string and numeric inputs
            freq_int = int(float(str(freq)))
            
            # Check if positive
            if freq_int <= 0:
                logging.warning(f"Invalid frequency: {freq} (must be positive)")
                return False
                
            # Check IC-910H frequency ranges for satellite operation
            # VHF: 144-148 MHz (amateur satellite band)
            # UHF: 430-450 MHz (amateur satellite band)  
            # SHF: 1.2-1.3 GHz (amateur satellite band)
            valid_ranges = [
                (144_000_000, 148_000_000),    # VHF amateur satellite
                (430_000_000, 450_000_000),    # UHF amateur satellite
                (1_200_000_000, 1_300_000_000) # SHF amateur satellite
            ]
            
            for min_freq, max_freq in valid_ranges:
                if min_freq <= freq_int <= max_freq:
                    return True
                    
            logging.warning(f"Frequency {freq} Hz ({freq_int/1_000_000:.3f} MHz) outside IC-910H satellite bands")
            return False
            
        except (ValueError, TypeError) as e:
            logging.warning(f"Invalid frequency format '{freq}': {e}")
            return False

    def _validateFrequencyString(self, freq_str):
        """Validate that frequency string can be converted to proper CI-V format."""
        try:
            # Test conversion to CI-V format
            freq = '0000000000' + str(freq_str)
            freq = freq[-10:]
            
            # Test each byte conversion
            int(freq[8:10], 16)  # Test last 2 digits
            int(freq[6:8], 16)   # Test next 2 digits
            int(freq[4:6], 16)   # Test next 2 digits
            int(freq[2:4], 16)   # Test next 2 digits
            int(freq[0:2], 16)   # Test first 2 digits
            
            return True
        except (ValueError, TypeError):
            return False

    def setMode(self, mode):
        """Set radio mode with retry logic - this is a setup command."""
        mode = mode.upper()
        if mode == 'FM':
            self.__writeToIcomWithRetry(b'\x06\x04')
            self.__writeToIcomWithRetry(b'\x06\x05')
        if mode == 'USB':
            self.__writeToIcomWithRetry(b'\x06\x01')
        if mode == 'LSB':
            self.__writeToIcomWithRetry(b'\x06\x00')
        if mode == 'CW':
            self.__writeToIcomWithRetry(b'\x06\x03')

    def setVFO(self, vfo):
        """Set VFO with retry logic - this is a setup command."""
        vfo = vfo.upper()
        if vfo == 'VFOA':
            self.current_vfo = "A"
            self.__writeToIcomWithRetry(b'\x07\x00')
        if vfo == 'VFOB':
            self.current_vfo = "B"
            self.__writeToIcomWithRetry(b'\x07\x01')
        if vfo == 'MAIN':
            self.current_vfo = "A"
            self.__writeToIcomWithRetry(b'\x07\xd0')  # select MAIN
        if vfo == 'SUB':
            self.current_vfo = "B"
            self.__writeToIcomWithRetry(b'\x07\xd1')  # select SUB

    # change main and sub
    def setExchange(self):
        """Exchange VFOs with retry logic - this is a setup command."""
        if self.current_vfo == "A":
            self.current_vfo = "B"
        else:
            self.current_vfo = "A"
        self.__writeToIcomWithRetry(b'\x07\xB0')

    # change main and sub
    def setSatelliteMode(self, on):
        """Set satellite mode with retry logic - this is a setup command."""
        if on:
            self.__writeToIcomWithRetry(b'\x1A\x07\x01')
        else:
            self.__writeToIcomWithRetry(b'\x1A\x07\x00')


    # Parameter: hertz string with 3 numbers
    def setToneHz(self, hertz):
        if int(hertz) >= 1000:
            b = b'\x1b\x00' + bytes([int('1' + hertz[1], 16), int(hertz[2] + hertz[3], 16)])
        else:
            b = b'\x1b\x00' + bytes([int('0' + hertz[0], 16), int(hertz[1] + hertz[2], 16)])
        self.__writeToIcom(b)
    def setToneSQLHz(self, hertz):
        if int(hertz) >= 1000:
            b = b'\x1b\x01' + bytes([int('1' + hertz[1], 16), int(hertz[2] + hertz[3], 16)])
        else:
            b = b'\x1b\x01' + bytes([int('0' + hertz[0], 16), int(hertz[1] + hertz[2], 16)])
        self.__writeToIcom(b)

    # Caution: RIT CI-V Command only for IC-9700, the IC-9100 has no RIT CI-V command
    # Parameter: Integer
    def setRitFrequency(self, value):
        hertz = '0000' + str(abs(value))
        if value >= 0:
            b = b'\x21\x00' + bytes([int(hertz[-2] + hertz[-1], 16),  int(hertz[-4] + hertz[-3], 16)]) + b'\x00'
        else:
            b = b'\x21\x00' + bytes([int(hertz[-2] + hertz[-1], 16),  int(hertz[-4] + hertz[-3], 16)]) + b'\x01'
        self.__writeToIcom(b)

    # Parameter as string in hertz
    def setFrequency(self, freq):
        """Set frequency - NO RETRY to avoid doppler update feedback loops."""
        try:
            # Validate frequency before processing
            if not self._validateFrequency(freq):
                logging.warning(f"Invalid frequency '{freq}' - skipping frequency update")
                return False
                
            if not self._validateFrequencyString(freq):
                logging.warning(f"Frequency '{freq}' cannot be converted to CI-V format - skipping")
                return False
            
            if self.current_vfo == "A":
                self.last_set_frequency_a = freq
            else:
                self.last_set_frequency_b = freq
            freq = '0000000000' + str(freq)
            freq = freq[-10:]
            b = bytes([5, int(freq[8:10], 16), int(freq[6:8], 16), int(freq[4:6], 16),
                       int(freq[2:4], 16), int(freq[0:2], 16)])
            returnMsg = self.__writeToIcom(b)  # Single attempt only
            back = False
            if len(returnMsg) > 0:
                if returnMsg.count(b'\xfb') > 0:
                    back = True
            return back
        except ValueError as e:
            logging.error(f"Invalid frequency format '{freq}': {e}")
            return False
        except Exception as e:
            logging.error(f"Error setting frequency {freq}: {e}")
            return False


    def setToneSquelchOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x43\x01')
        else:
            self.__writeToIcom(b'\x16\x43\x00')

    def setToneOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x42\x01')
        else:
            self.__writeToIcom(b'\x16\x42\x00')

    def setAfcOn(self, on):
        if on:
            self.__writeToIcom(b'\x16\x4A\x01')
        else:
            self.__writeToIcom(b'\x16\x4A\x00')

    # Parameter b: True = set SPLIT ON, False = set SPLIT OFF
    def setSplitOn(self, on):
        if on:
            self.__writeToIcom(b'\x0F\x01')
        else:
            self.__writeToIcom(b'\x0F\x00')

    # Parameter b: True = set RIT ON, False = set RIT OFF
    def setRitOn(self, on):
        if on:
            self.__writeToIcom(b'\x1A\x06\x01')
        else:
            self.__writeToIcom(b'\x1A\x06\x00')

    def setDuplex(self, value):
        value = value.upper()
        if value == 'OFF':
            self.__writeToIcom(b'\x0F\x10')
        if value == 'DUP-':
            self.__writeToIcom(b'\x0F\x11')
        if value == 'DUP+':
            self.__writeToIcom(b'\x0F\x12')

    def getFrequency(self):
        if self.connected == True:
            b = self.__writeToIcom(b'\x03')  # ask for used frequency
            c = ''
            if len(b) >= 10:
                for a in reversed(b[5:10]):
                    c = c + '%0.2X' % a
            if len(c) > 0: 
                if c[0] == '0':
                    c = c[1:len(c)]
            return c
        else:
            if self.current_vfo == "A":
                return self.last_set_frequency_a
            else:
                return self.last_set_frequency_b

    def setFrequencyOffUnselectVFO(self, freq):
        """Set frequency without selecting VFO - with validation."""
        try:
            # Validate frequency before processing
            if not self._validateFrequency(freq):
                logging.warning(f"Invalid frequency '{freq}' - skipping frequency update")
                return False
                
            if not self._validateFrequencyString(freq):
                logging.warning(f"Frequency '{freq}' cannot be converted to CI-V format - skipping")
                return False
                
            freq = '0000000000' + str(freq)
            freq = freq[-10:]
            b = b'\x25\x01' + bytes([int(freq[8:10], 16), int(freq[6:8], 16), int(freq[4:6], 16),
                       int(freq[2:4], 16), int(freq[0:2], 16)])
            returnMsg = self.__writeToIcom(b)
            back = False
            if len(returnMsg) > 0:
                if returnMsg.count(b'\xfb') > 0:
                    back = True
            return back
        except ValueError as e:
            logging.error(f"Invalid frequency format '{freq}': {e}")
            return False
        except Exception as e:
            logging.error(f"Error setting frequency {freq}: {e}")
            return False

    # CI-V TRANSCEIVE have to be ON
    # function extract last frequency which is send to us when a user is dailing
    def getWhatFrequencyIcomSendUs(self):
        c = ''
        b = self.__readFromIcom()
        # find last CI-V message by searching from behind
        position = b.rfind(bytearray(b'\xfe\xfe'))
        if position >= 0:
            # extract answer
            answer = b[position:len(b)]
            # proof if CI-V frequence message from icom
            if len(answer) == 11 and answer[4] == 0:
                if len(answer) > 0:
                    for a in reversed(answer[5:10]):
                        c = c + '%0.2X' % a
                if c[0] == '0':
                    c = c[1:len(c)]
        return c

    def isPttOff(self):
        # IC-910/IC-910H does not support PTT status queries via CAT commands
        if self.radio_model == '910':
            return True
        
        ret = True
        b = self.__writeToIcom(b'\x1C\x00')  # ask for PTT status
        if len(b) < 3:
            return ret
        #print(b)
        if len(b) >= 2 and b[-2] == 1:
            ret = False
        return ret
        
    def setup_vfos(self, satmode, downmode, upmode, doppler_thres_fm, doppler_thres_linear):
        doppler_thres = 100
        interactive = True
        if satmode == 1:
            self.setVFO("Main")
        else:
            self.setVFO("VFOA")
        if downmode == "FM":
            self.setMode("FM")
            doppler_thres = doppler_thres_fm
            interactive = False
        elif downmode == "FMN":
            self.setMode("FM")
            doppler_thres = doppler_thres_fm
            interactive = False
        elif downmode ==  "LSB":
            interactive = True
            self.setMode("LSB")
            doppler_thres = doppler_thres_linear
        elif downmode ==  "USB":
            interactive = True
            self.setMode("USB")
            doppler_thres = doppler_thres_linear
        elif downmode ==  "DATA-LSB":
            interactive = False
            self.setMode("LSB")
            doppler_thres = 0
        elif downmode ==  "DATA-USB":
            interactive = False
            self.setMode("USB")
            doppler_thres = 0      
        elif downmode == "CW":
            interactive = True
            self.setMode("CW") 
            doppler_thres = doppler_thres_linear
        else:
            logging.warning("*** Downlink mode not implemented yet: {bad}".format(bad=self.my_satellite.downmode))
            sys.exit()
        
        if satmode == 1:
            self.setVFO("SUB")
        else:
            self.setVFO("VFOB")
        if upmode == "FM":
            self.setMode("FM")
        elif upmode == "FMN":
            self.setMode("FM")
        elif upmode == "LSB" or downmode ==  "DATA-LSB":
            self.setMode("LSB")
        elif upmode == "USB" or downmode ==  "DATA-USB":
            self.setMode("USB")
        elif upmode == "CW":
            self.setMode("CW") 
        else:
            logging.warning("*** Uplink mode not implemented yet: {bad}".format(bad=self.my_satellite.upmode))
            sys.exit()
            
        return int(doppler_thres), interactive


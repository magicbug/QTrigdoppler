# IC-910 rig class


# uses serial port to communicate
import serial as s

class ic910:
    
    def __init__(self, serial_port, baudrate,civ_addr):
        self.port_id = serial_port
        self.civ_addr = civ_addr
        self.radio_baudrate = baudrate
        self.radio_con = s.Serial(self.port_id, self.radio_baudrate)
        
    def quit(self):
        self.s.close()
        
    def process_radio_data(self):
        # OK MESSAGE TO CONTROLLER
        ack_msg = bytes([254, 254, 226, self.civ_addr, 251, 253])
        rx_buf = bytearray()
        while self.radio_con.inWaiting():
            rx_buf += self.radio_con.read()
        # Only one command in buffer, skep the rest
        while rx_buf.count(b'\xfd') > 1:
            del rx_buf[0:rx_buf.find(b'\xfd') + 1]
        if len(rx_buf) > 0:
            if rx_buf[0:5] == ack_msg:
                #cut rx buffer to data msg
                rx_buf = rx_buf[6:len(rx_buf)]
                if len(rx_buf)>0:
                    #check for data msg begin
                    if rx_buf[0:1] == [254, 254] and  rx_buf[-1] == [253]:
                        return rx_buf
            else:
                if rx_buf[0:1] == [254, 254] and  rx_buf[-1] == [253]:
                    return rx_buf
        return rx_buf
                    
            
        
    def send_cmd(self, data):
        # page 78 on user manual describes frame format
        self.radio_con.write(bytes([254, 254, int(self.civ_addr), 226]) + data + bytes([253]))
        return self.process_radio_data()
    
    def setMode(self, mode):
        mode = mode.upper()
        if mode == 'FM':
            self.send_cmd(b'\x06\x04')
        if mode == 'FMN':
            self.send_cmd(b'\x06\x05')
        if mode == 'USB':
            self.send_cmd(b'\x06\x01')
        if mode == 'LSB':
            self.send_cmd(b'\x06\x00')
        if mode == 'CW':
            self.send_cmd(b'\x06\x03')
            
    def setVFO(self, vfo):
        vfo = vfo.upper()
        if vfo == 'VFOA':
            self.send_cmd(b'\x07\x00')  # select VFO A
        if vfo == 'VFOB':
            self.send_cmd(b'\x07\x01')  # select VFO B
        if vfo == 'MAIN':
            self.send_cmd(b'\x07\xd0')  # select MAIN
        if vfo == 'SUB':
            self.send_cmd(b'\x07\xd1')  # select SUB
        
    def setExchange(self):
        self.send_cmd(b'\x07\xB0')

    def setSatelliteMode(self, on):
        if on:
            self.send_cmd(b'\x1A\x07\x01')
        else:
            self.send_cmd(b'\x1A\x07\x00')
            
    def setToneHz(self, hertz):
        b = b'\x1b\x00' + bytes([int('0' + hertz[0], 16), int(hertz[1] + hertz[2], 16)])
        self.send_cmd(b)
        
    def setFrequency(self, freq):
        freq = '0000000000' + freq
        freq = freq[-10:]
        b = bytes([5, int(freq[8:10], 16), int(freq[6:8], 16), int(freq[4:6], 16),
                   int(freq[2:4], 16), int(freq[0:2], 16)])
        returnMsg = self.send_cmd(b)
        back = False
        if len(returnMsg) > 0:
            if returnMsg.count(b'\xfb') > 0:
                back = True
        return back


    def setToneSquelchOn(self, on):
        if on:
            self.send_cmd(b'\x16\x43\x01')
        else:
            self.send_cmd(b'\x16\x43\x00')

    def setToneOn(self, on):
        if on:
            self.send_cmd(b'\x16\x42\x01')
        else:
            self.send_cmd(b'\x16\x42\x00')

    def setAfcOn(self, on):
        if on:
            self.send_cmd(b'\x16\x4A\x01')
        else:
            self.send_cmd(b'\x16\x4A\x00')

    # Parameter b: True = set SPLIT ON, False = set SPLIT OFF
    def setSplitOn(self, on):
        if on:
            self.send_cmd(b'\x0F\x01')
        else:
            self.send_cmd(b'\x0F\x00')

    # Parameter b: True = set RIT ON, False = set RIT OFF
    def setRitOn(self, on):
        if on:
            self.send_cmd(b'\x1A\x06\x01')
        else:
            self.send_cmd(b'\x1A\x06\x00')

    def setDuplex(self, value):
        value = value.upper()
        if value == 'OFF':
            self.send_cmd(b'\x0F\x10')
        if value == 'DUP-':
            self.send_cmd(b'\x0F\x11')
        if value == 'DUP+':
            self.send_cmd(b'\x0F\x12')

    def getFrequency(self):
        b = self.send_cmd(b'\x03')  # ask for used frequency
        c = ''
        if len(b) > 0:
            for a in reversed(b[5:10]):
                c = c + '%0.2X' % a
        if len(c) > 0: 
            if c[0] == '0':
                c = c[1:len(c)]
        return c

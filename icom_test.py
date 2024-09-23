import icom
icomTrx = icom.icom('/dev/ttyUSB0', '19200', 96)
icomTrx.setVFO("MAIN")
print(icomTrx.getFrequency())
icomTrx.setVFO("SUB")
print(icomTrx.getFrequency())

# Autor:
#   Original from K8DP Doug Papay (v0.1)
#
#   Adapted v0.3 by EA4HCF Pedro Cabrera
#
#   v0.4 and beyond: Extended, partly rewritten and adapted from hamlib to direct radio control by DL3JOP Joshua Petry


import ephem
import socket
import sys
import math
import time
import re
import urllib.request
import traceback
import icom

from time import gmtime, strftime
from datetime import datetime, timedelta, timezone

from configparser import ConfigParser

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from qt_material import apply_stylesheet

C = 299792458.


### Calculates the tx doppler frequency
def tx_dopplercalc(ephemdata, freq_at_sat):
    ephemdata.compute(myloc)
    doppler = int(freq_at_sat + ephemdata.range_velocity * freq_at_sat / C)
    return doppler
### Calculates the rx doppler frequency
def rx_dopplercalc(ephemdata, freq_at_sat):
    ephemdata.compute(myloc)
    doppler = int(freq_at_sat - ephemdata.range_velocity * freq_at_sat / C)
    return doppler
### Calculates the tx doppler error   
def tx_doppler_val_calc(ephemdata, freq_at_sat):
    ephemdata.compute(myloc)
    doppler = format(float(ephemdata.range_velocity * freq_at_sat / C), '.2f')
    return doppler
### Calculates the rx doppler error   
def rx_doppler_val_calc(ephemdata, freq_at_sat):
    ephemdata.compute(myloc)
    doppler = format(float(-ephemdata.range_velocity * freq_at_sat / C),'.2f')
    return doppler
    
def MyError():
    print("Failed to find required file!")
    sys.exit()

print("QT Rigdoppler v0.4")


### parsing config file
try:
    with open('config.ini') as f:
        f.close()
        configur = ConfigParser()
        configur.read('config.ini')
except IOError:
    raise MyError()

### config file to global vars

LATITUDE = configur.get('qth','latitude')
LONGITUDE = configur.get('qth','longitude')
ALTITUDE = configur.getfloat('qth','altitude')
STEP_RX = configur.getint('qth','step_rx')
STEP_TX = configur.getint('qth','step_tx')
MAX_OFFSET_RX = configur.getint('qth','max_offset_rx')
MAX_OFFSET_TX = configur.getint('qth','max_offset_tx')
TLEFILE = configur.get('satellite','tle_file')
TLEURL = configur.get('satellite','tle_url')
SATNAMES = configur.get('satellite','amsatnames')
DOPPLER_THRES_FM = configur.get('satellite', 'doppler_threshold_fm')
DOPPLER_THRES_LINEAR = configur.get('satellite', 'doppler_threshold_linear')
SQFILE = configur.get('satellite','sqffile')
RADIO = configur.get('icom','radio')
CVIADDR = configur.get('icom','cviaddress')
SERIALPORT = configur.get('icom', 'serialport')
if configur.get('icom', 'fullmode') == "True":
    OPMODE = True
elif configur.get('icom', 'fullmode') == "False":
    OPMODE = False
    
useroffsets = []

subtone_list = ["None", "67 Hz", "71.9 Hz"]

i = 0
for (each_key, each_val) in configur.items('offset_profiles'):
    # Format SATNAME:RXoffset,TXoffset
    useroffsets += [each_val.split(',')]
    i+=1

# radio frequencies
F0=0.0
I0=0.0
f_cal = 0
i_cal = 0
doppler_thres = 0

myloc = ephem.Observer()
myloc.lon = LONGITUDE
myloc.lat = LATITUDE
myloc.elevation = ALTITUDE

TRACKING_ACTIVE = True # tracking on/off
INTERACTIVE = False # read user vfo/dial input - disable for inband packet
if configur['icom']['radio'] == '9700':
    icomTrx = icom.icom(SERIALPORT, '19200', 96)
elif configur['icom']['radio'] == '910':
    icomTrx = icom.icom(SERIALPORT, '19200', 96)
           


class Satellite:
    name = ""
    noradid = 0
    amsatname= ""
    downmode = ""
    upmode = ""
    mode = ""
    F = 0
    F_init = 0
    F_cal = 0
    I = 0
    I_init = 0
    I_cal = 0
    new_cal = 0
    down_doppler = 0
    down_doppler_old = 0
    down_doppler_rate = 0
    up_doppler = 0
    up_doppler_old = 0
    up_doppler_rate = 0
    tledata = ""
    rig_satmode = 0

class ConfigWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("QTRigDoppler configuration")
        self.setGeometry(0, 0, 800, 350)

        # QTH
        global LATITUDE
        global LONGITUDE
        global ALTITUDE
        global STEP_RX
        global STEP_TX
        global MAX_OFFSET_RX
        global MAX_OFFSET_TX
        global DOPPLER_THRES_FM
        global DOPPLER_THRES_LINEAR

        # satellite
        global TLEFILE
        global TLEURL
        global SATNAMES
        global SQFILE

        # Radio
        global RADIO
        global CVIADDR
        global OPMODE

        myFont=QFont()
        myFont.setBold(True)

        pagelayout = QVBoxLayout()

        uplayout = QHBoxLayout()
        mediumlayout = QHBoxLayout()
        downlayout = QHBoxLayout()

        pagelayout.addLayout(uplayout)
        pagelayout.addLayout(mediumlayout)
        pagelayout.addLayout(downlayout)
        
        qth_layout = QVBoxLayout()
        satellite_layout = QVBoxLayout()
        radio_layout = QVBoxLayout()
        offset_layout = QVBoxLayout()
        buttons_layout = QVBoxLayout()

        uplayout.addLayout(qth_layout)
        uplayout.addLayout(satellite_layout)

        mediumlayout.addLayout(radio_layout)

        downlayout.addLayout(offset_layout)
        downlayout.addLayout(buttons_layout)

        ### QTH
        self.qth = QLabel("QTH Parameters")
        self.qth.setFont(myFont)
        qth_layout.addWidget(self.qth)
        
        # 1x Label latitude
        self.qthlat_lbl = QLabel("QTH latitude:")
        qth_layout.addWidget(self.qthlat_lbl)

        self.qthlat = QLineEdit()
        self.qthlat.setMaxLength(10)
        self.qthlat.setText(str(LATITUDE))
        qth_layout.addWidget(self.qthlat)

        # 1x Label Longitude
        self.qthlong_lbl = QLabel("QTH longitude:")
        qth_layout.addWidget(self.qthlong_lbl)

        self.qthlong = QLineEdit()
        self.qthlong.setMaxLength(10)
        self.qthlong.setEchoMode(QLineEdit.Normal)
        self.qthlong.setText(str(LONGITUDE))
        qth_layout.addWidget(self.qthlong)

        # 1x Label altitude
        self.qthalt_lbl = QLabel("QTH altitude:")
        qth_layout.addWidget(self.qthalt_lbl)

        self.qthalt = QLineEdit()
        self.qthalt.setMaxLength(10)
        self.qthalt.setText(str(ALTITUDE))
        qth_layout.addWidget(self.qthalt)

        # 1x Label step RX
        self.qthsteprx_lbl = QLabel("Step (Hz) for RX:")
        qth_layout.addWidget(self.qthsteprx_lbl)

        self.qthsteprx = QLineEdit()
        self.qthsteprx.setMaxLength(10)
        self.qthsteprx.setText(str(STEP_RX))
        qth_layout.addWidget(self.qthsteprx)

        # 1x Label step TX
        self.qthsteptx_lbl = QLabel("Step (Hz) for TX:")
        qth_layout.addWidget(self.qthsteptx_lbl)

        self.qthsteptx = QLineEdit()
        self.qthsteptx.setMaxLength(10)
        self.qthsteptx.setText(str(STEP_TX))
        qth_layout.addWidget(self.qthsteptx)

        # 1x Label Max Offset RX
        self.qthmaxoffrx_lbl = QLabel("Max Offset (Hz) for RX:")
        qth_layout.addWidget(self.qthmaxoffrx_lbl)

        self.qthmaxoffrx = QLineEdit()
        self.qthmaxoffrx.setMaxLength(6)
        self.qthmaxoffrx.setText(str(MAX_OFFSET_RX))
        qth_layout.addWidget(self.qthmaxoffrx)

        # 1x Label Max Offset TX
        self.qthmaxofftx_lbl = QLabel("Max Offset (Hz) for TX:")
        qth_layout.addWidget(self.qthmaxofftx_lbl)

        self.qthmaxofftx = QLineEdit()
        self.qthmaxofftx.setMaxLength(6)
        self.qthmaxofftx.setText(str(MAX_OFFSET_TX))
        qth_layout.addWidget(self.qthmaxofftx)
        
        # 1x Label doppler fm threshold
        self.doppler_fm_threshold_lbl = QLabel("Doppler threshold for FM")
        qth_layout.addWidget(self.doppler_fm_threshold_lbl)

        self.doppler_fm_threshold = QLineEdit()
        self.doppler_fm_threshold.setMaxLength(6)
        self.doppler_fm_threshold.setText(str(DOPPLER_THRES_FM))
        qth_layout.addWidget(self.doppler_fm_threshold)
        
        # 1x Label doppler linear threshold
        self.doppler_linear_threshold_lbl = QLabel("Doppler threshold for Linear")
        qth_layout.addWidget(self.doppler_linear_threshold_lbl)

        self.doppler_linear_threshold = QLineEdit()
        self.doppler_linear_threshold.setMaxLength(6)
        self.doppler_linear_threshold.setText(str(DOPPLER_THRES_LINEAR))
        qth_layout.addWidget(self.doppler_linear_threshold)

        ### Satellite
        self.sat = QLabel("Satellite Parameters")
        self.sat.setFont(myFont)
        satellite_layout.addWidget(self.sat)
        # 1x Label TLE file
        self.sattle_lbl = QLabel("TLE filename:")
        satellite_layout.addWidget(self.sattle_lbl)

        self.sattle = QLineEdit()
        self.sattle.setMaxLength(30)
        self.sattle.setText(TLEFILE)
        satellite_layout.addWidget(self.sattle)

        # 1x Label TLE URL
        self.sattleurl_lbl = QLabel("TLE URL:")
        satellite_layout.addWidget(self.sattleurl_lbl)

        self.sattleurl = QLineEdit()
        self.sattleurl.setMaxLength(70)
        self.sattleurl.setText(TLEURL)
        satellite_layout.addWidget(self.sattleurl)

        # 1x Label SATNAMES file
        self.satsatnames_lbl = QLabel("AmsatNames filename:")
        satellite_layout.addWidget(self.satsatnames_lbl)

        self.satsatnames = QLineEdit()
        self.satsatnames.setMaxLength(30)
        self.satsatnames.setText(SATNAMES)
        satellite_layout.addWidget(self.satsatnames)

        # 1x Label SQF file
        self.satsqf_lbl = QLabel("SQF filename:")
        satellite_layout.addWidget(self.satsqf_lbl)

        self.satsqf = QLineEdit()
        self.satsqf.setMaxLength(30)
        self.satsqf.setText(SQFILE)
        satellite_layout.addWidget(self.satsqf)

        ### RADIO
        self.radio = QLabel("Radio Parameters")
        self.radio.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.radio.setFont(myFont)
        radio_layout.addWidget(self.radio)

        # 1x Label CVI address
        self.radiolist_lbl = QLabel("Select radio:")
        self.radiolist_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        radio_layout.addWidget(self.radiolist_lbl)

        # 1x Select manufacturer
        self.radiolistcomb = QComboBox()
        self.radiolistcomb.addItems(['Icom 9700'])
        #self.radiolistcomb.addItems(['Icom 705'])
        #self.radiolistcomb.addItems(['Yaesu 818'])
        self.radiolistcomb.addItems(['Icom 910H'])
        if configur['icom']['radio'] == '9700':
            self.radiolistcomb.setCurrentText('Icom 9700')
        #elif configur['icom']['radio'] == '705':
        #    self.radiolistcomb.setCurrentText('Icom 705')
        #elif configur['icom']['radio'] == '818':
        #    self.radiolistcomb.setCurrentText('Yaesu 818')
        elif configur['icom']['radio'] == '910':
            self.radiolistcomb.setCurrentText('Icom 910H')
        radio_layout.addWidget(self.radiolistcomb)

        # 1x Label CVI address
        self.radicvi_lbl = QLabel("CVI address:")
        self.radicvi_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        radio_layout.addWidget(self.radicvi_lbl)

        self.radicvi = QLineEdit()
        self.radicvi.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.radicvi.setMaxLength(2)
        self.radicvi.setText(CVIADDR)
        radio_layout.addWidget(self.radicvi)

        # 1x Label Duplex mode
        self.radidplx_lbl = QLabel("Duplex mode:")
        self.radidplx_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        radio_layout.addWidget(self.radidplx_lbl)

        self.radidplx = QCheckBox()
        if OPMODE == False:
            self.radidplx.setChecked(False)
        elif OPMODE == True:
            self.radidplx.setChecked(True)
        self.radidplx.setText("Full Duplex Operation for 705/818")
        self.radidplx.stateChanged.connect(self.opmode_change)
        radio_layout.addWidget(self.radidplx)

        ### Offset profiles
        self.offsets = QLabel("Offsets Profiles")
        self.offsets.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.offsets.setFont(myFont)
        offset_layout.addWidget(self.offsets)

        self.offsetText = QTextEdit()
        self.offsetText.setReadOnly(False)
        self.offsetText.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.offsetText.setStyleSheet("background-color: black; color: white;")
        offset_layout.addWidget(self.offsetText)

        for (each_key, each_val) in configur.items('offset_profiles'):
            self.offsetText.append(each_val)

        # Save Label
        self.savebutontitle = QLabel("Save configuration")
        self.savebutontitle.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        buttons_layout.addWidget(self.savebutontitle)

        # 1x QPushButton (Save)
        self.Savebutton = QPushButton("Save")
        self.Savebutton.clicked.connect(self.save_config)
        buttons_layout.addWidget(self.Savebutton)

        # Exit Label
        self.exitbutontitle = QLabel("Exit configuration")
        self.exitbutontitle.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        buttons_layout.addWidget(self.exitbutontitle)

        # 1x QPushButton (Save)
        self.Exitbutton = QPushButton("Exit")
        self.Exitbutton.clicked.connect(self.exit_config)
        buttons_layout.addWidget(self.Exitbutton)

        ##########################################
        container = QWidget()
        container.setLayout(pagelayout)
        self.setCentralWidget(container)
    
    def save_config(self):
        # QTH
        global LATITUDE
        global LONGITUDE
        global ALTITUDE
        global STEP_RX
        global STEP_TX
        global MAX_OFFSET_TX
        global MAX_OFFSET_RX
        global DOPPLER_THRES_FM
        global DOPPLER_THRES_LINEAR

        # satellite
        global TLEFILE
        global TLEURL
        global SATNAMES
        global SQFILE

        # Radio
        global RADIO
        global CVIADDR
        global OPMODE



        LATITUDE = self.qthlat.displayText()
        configur['qth']['latitude'] = str(float(self.qthlat.displayText()))
        LONGITUDE = self.qthlong.displayText()
        configur['qth']['longitude'] = str(float(self.qthlong.displayText()))
        ALTITUDE = float(self.qthalt.displayText())
        configur['qth']['altitude'] = str(float(self.qthalt.displayText()))
        STEP_RX = int(self.qthsteprx.displayText())
        configur['qth']['step_rx'] = str(int(self.qthsteprx.displayText()))
        STEP_TX = int(self.qthsteptx.displayText())
        configur['qth']['step_tx'] = str(int(self.qthsteptx.displayText()))
        MAX_OFFSET_RX = int(self.qthmaxoffrx.displayText())
        configur['qth']['max_offset_rx'] = str(int(self.qthmaxoffrx.displayText()))
        MAX_OFFSET_TX = int(self.qthmaxoffrx.displayText())
        configur['qth']['max_offset_tx'] = str(int(self.qthmaxoffrx.displayText()))
        TLEFILE = configur['satellite']['tle_file'] = str(self.sattle.displayText())
        TLEURL =  configur['satellite']['tle_url'] = str(self.sattleurl.displayText())
        SATNAMES = configur['satellite']['amsatnames'] = str(self.satsatnames.displayText())
        SQFILE = configur['satellite']['sqffile'] = str(self.satsqf.displayText())
        
        DOPPLER_THRES_FM = int(self.doppler_fm_threshold.displayText())
        configur['satellite']['doppler_threshold_fm'] = str(int(self.doppler_fm_threshold.displayText()))
        DOPPLER_THRES_LINEAR = int(self.doppler_linear_threshold.displayText())
        configur['satellite']['doppler_threshold_linear'] = str(int(self.doppler_linear_threshold.displayText()))
        
        if self.radiolistcomb.currentText() == "Icom 9700":
            RADIO = configur['icom']['radio'] = '9700'
        #elif self.radiolistcomb.currentText() == "Icom 705":
        #    RADIO = configur['icom']['radio'] = '705'
        #elif self.radiolistcomb.currentText() == "Yaesu 818":
        #    RADIO = configur['icom']['radio'] = '818'
        elif self.radiolistcomb.currentText() == "Icom 910H":
            RADIO = configur['icom']['radio'] = '910'

        if self.radidplx.isChecked():
            OPMODE = True
            configur['icom']['fullmode'] = "True"
        else:
            OPMODE = False
            configur['icom']['fullmode'] = "False"
        CVIADDR = configur['icom']['cviaddress'] = str(self.radicvi.displayText())

        if self.offsetText.document().blockCount() >= 1:
            for i in range(0, self.offsetText.document().blockCount()):
                theline = self.offsetText.toPlainText().splitlines(i)
                index = 'satoffset' + str(i + 1)
                configur['offset_profiles'][index] = theline[i]

        with open('config.ini', 'w') as configfile:
            configur.write(configfile)
        self.close()

    def opmode_change(self):
        if self.radidplx.isChecked():
            self.hamlport2.setEnabled(True)
        else:
            self.hamlport2.setEnabled(False)

    def exit_config(self):
        self.close()

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.counter = 0
        self.my_satellite = Satellite()

        self.setWindowTitle("QT RigDoppler v0.4")
        self.setGeometry(0, 0, 900, 150)

        pagelayout = QVBoxLayout()

        uplayout = QHBoxLayout()
        downlayout = QHBoxLayout()

        pagelayout.addLayout(uplayout)
        pagelayout.addLayout(downlayout)
        
        labels_layout = QVBoxLayout()
        combo_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        combo_layout.setAlignment(Qt.AlignVCenter)

        uplayout.addLayout(combo_layout)
        uplayout.addLayout(labels_layout)
        uplayout.addLayout(button_layout)

        self.sattext = QLabel("Satellite:")
        self.sattext.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        combo_layout.addWidget(self.sattext)

        self.combo1 = QComboBox()
        satlist = []
        with open(SQFILE, 'r') as h:
            sqfdata = h.readlines() 
            for line in sqfdata:
                if ',' and not ";" in line:
                    newitem = str(line.split(",")[0].strip())
                    satlist += [newitem]
        satlist=list(dict.fromkeys(satlist))  
        self.combo1.addItems(['Select one...'])
        self.combo1.addItems(satlist)
        self.combo1.currentTextChanged.connect(self.sat_changed) 
        combo_layout.addWidget(self.combo1)
        
        self.tpxtext = QLabel("Transponder:")
        self.tpxtext.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        combo_layout.addWidget(self.tpxtext)
        self.combo2 = QComboBox()
        self.combo2.currentTextChanged.connect(self.tpx_changed) 
        combo_layout.addWidget(self.combo2)
        
        self.tonetext = QLabel("Subtone:")
        self.tonetext.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        combo_layout.addWidget(self.tonetext)
        self.combo3 = QComboBox()
        self.combo3.addItems(subtone_list)
        self.combo3.currentTextChanged.connect(self.tone_changed) 
        combo_layout.addWidget(self.combo3)
        
        doppler_thres_layout = QHBoxLayout()
        self.dopplerthreslabel = QLabel("Doppler threshold:")
        doppler_thres_layout.addWidget(self.dopplerthreslabel)
        self.dopplerthresval = QLabel("0.0")
        doppler_thres_layout.addWidget(self.dopplerthresval)
        #combo_layout.addLayout(doppler_thres_layout)
        
        # 1x Label: RX Offset
        self.rxoffsetboxtitle = QLabel("RX Offset:")
        self.rxoffsetboxtitle.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        combo_layout.addWidget(self.rxoffsetboxtitle)

        # 1x QSlider (RX offset)
        self.rxoffsetbox = QSpinBox()
        self.rxoffsetbox.setMinimum(-MAX_OFFSET_RX)
        self.rxoffsetbox.setMaximum(MAX_OFFSET_RX)
        self.rxoffsetbox.setSingleStep(int(STEP_RX))
        self.rxoffsetbox.valueChanged.connect(self.rxoffset_value_changed)
        combo_layout.addWidget(self.rxoffsetbox)

        myFont=QFont()
        myFont.setBold(True)
        
        groupbox_downlink = QGroupBox()
        groupbox_downlink.setStyleSheet("QGroupBox{padding-top:5px;padding-bottom:5px; margin-top:0px}")
        labels_layout.addWidget(groupbox_downlink)
        vbox_downlink = QVBoxLayout()
        groupbox_downlink.setLayout(vbox_downlink)
        
        rx_labels_radio_layout = QHBoxLayout()
        # 1x Label: RX freq
        self.rxfreqtitle = QLabel("RX @ Radio:")
        self.rxfreqtitle.setFont(myFont)
        rx_labels_radio_layout.addWidget(self.rxfreqtitle)

        self.rxfreq = QLabel("0.0")
        self.rxfreq.setFont(myFont)
        rx_labels_radio_layout.addWidget(self.rxfreq)
        
        vbox_downlink.addLayout(rx_labels_radio_layout)

        rx_labels_sat_layout = QHBoxLayout()
        # 1x Label: RX freq Satellite
        self.rxfreqsat_lbl = QLabel("RX @ Sat:")
        rx_labels_sat_layout.addWidget(self.rxfreqsat_lbl)

        self.rxfreq_onsat = QLabel("0.0")
        rx_labels_sat_layout.addWidget(self.rxfreq_onsat)
        vbox_downlink.addLayout(rx_labels_sat_layout)
        
        # 1x Label: RX Doppler Satellite
        rx_doppler_freq_layout = QHBoxLayout()
        self.rxdopplersat_lbl = QLabel("Doppler:")
        rx_doppler_freq_layout.addWidget(self.rxdopplersat_lbl)

        self.rxdoppler_val = QLabel("0.0 Hz")
        rx_doppler_freq_layout.addWidget(self.rxdoppler_val)
        
        vbox_downlink.addLayout(rx_doppler_freq_layout)
        
        # 1x Label: RX Doppler RateSatellite
        rx_doppler_rate_layout = QHBoxLayout()
        self.rxdopplerratesat_lbl = QLabel("Rate:")
        rx_doppler_rate_layout.addWidget(self.rxdopplerratesat_lbl)

        self.rxdopplerrate_val = QLabel("0.0 Hz/s")
        rx_doppler_rate_layout.addWidget(self.rxdopplerrate_val)
        
        vbox_downlink.addLayout(rx_doppler_rate_layout)
        
        groupbox_uplink = QGroupBox()
        groupbox_uplink.setStyleSheet("QGroupBox{padding-top:5px;padding-bottom:5px; margin-top:0px}")
        labels_layout.addWidget(groupbox_uplink)
        vbox_uplink = QVBoxLayout()
        groupbox_uplink.setLayout(vbox_uplink)

        tx_labels_radio_layout = QHBoxLayout()
        # 1x Label: TX freq
        self.txfreqtitle = QLabel("TX @ Radio:")
        self.txfreqtitle.setFont(myFont)
        tx_labels_radio_layout.addWidget(self.txfreqtitle)

        self.txfreq = QLabel("0.0")
        self.txfreq.setFont(myFont)
        tx_labels_radio_layout.addWidget(self.txfreq)
        
        vbox_uplink.addLayout(tx_labels_radio_layout)

        tx_labels_sat_layout = QHBoxLayout()
        # 1x Label: TX freq Satellite
        self.txfreqsat_lbl = QLabel("TX @ Sat:")
        tx_labels_sat_layout.addWidget(self.txfreqsat_lbl)

        self.txfreq_onsat = QLabel("0.0")
        tx_labels_sat_layout.addWidget(self.txfreq_onsat)
        vbox_uplink.addLayout(tx_labels_sat_layout)
        
        
        # 1x Label: TX Doppler Satellite
        tx_doppler_freq_layout = QHBoxLayout()
        self.txdopplersat_lbl = QLabel("Doppler:")
        tx_doppler_freq_layout.addWidget(self.txdopplersat_lbl)

        self.txdoppler_val = QLabel("0.0 Hz")
        tx_doppler_freq_layout.addWidget(self.txdoppler_val)
        
        vbox_uplink.addLayout(tx_doppler_freq_layout)
        
        # 1x Label: TX Doppler RateSatellite
        tx_doppler_rate_layout = QHBoxLayout()
        self.txdopplerratesat_lbl = QLabel("Rate:")
        tx_doppler_rate_layout.addWidget(self.txdopplerratesat_lbl)

        self.txdopplerrate_val = QLabel("0.0 Hz/s")
        tx_doppler_rate_layout.addWidget(self.txdopplerrate_val)
        
        vbox_uplink.addLayout(tx_doppler_rate_layout)
        
        # 1x QPushButton (Start)
        self.Startbutton = QPushButton("Start Tracking")
        self.Startbutton.clicked.connect(self.init_worker)
        button_layout.addWidget(self.Startbutton)
        self.Startbutton.setEnabled(False)

        # 1x QPushButton (Stop)
        self.Stopbutton = QPushButton("Stop Tracking")
        self.Stopbutton.clicked.connect(self.the_stop_button_was_clicked)
        button_layout.addWidget(self.Stopbutton)
        self.Stopbutton.setEnabled(False)
        
        # Sync to SQF freq
        self.syncbutton = QPushButton("Sync to SQF Frequencies")
        self.syncbutton.clicked.connect(self.the_sync_button_was_clicked)
        button_layout.addWidget(self.syncbutton)
        self.syncbutton.setEnabled(False)

        # 1x QPushButton (Exit)
        self.Exitbutton = QPushButton("Exit")
        self.Exitbutton.setCheckable(True)
        self.Exitbutton.clicked.connect(self.the_exit_button_was_clicked)
        button_layout.addWidget(self.Exitbutton)

        # Output log
        self.LogText = QTextEdit()
        self.LogText.setReadOnly(True)
        self.LogText.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        downlayout.addWidget(self.LogText)

        ## Menu
        self.button_action = QAction("&Main setup", self)
        self.button_action.setStatusTip("Load and edit configuration")
        self.button_action.triggered.connect(self.setup_config)

        menu = self.menuBar()
        self.config_menu = menu.addMenu("&Setup")
        self.config_menu.addAction(self.button_action)
        ## End Menu
        
        container = QWidget()
        container.setLayout(pagelayout)
        self.setCentralWidget(container)

        self.threadpool = QThreadPool()
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.recurring_timer)

    def setup_config(self, checked):
        self.cfgwindow = ConfigWindow()
        self.cfgwindow.show()

    def rxoffset_value_changed(self, i):
            global f_cal
            self.my_satellite.new_cal = 1
            self.my_satellite.F_cal =  f_cal = i
            self.LogText.append("*** New RX offset: {thenew}".format(thenew=i))
    
    def txoffset_value_changed(self, i):
        pass
            #global i_cal
            #self.my_satellite.I_cal = i_cal
            #self.LogText.append("*** New TX offset: {thenew}".format(thenew=i))
    
    def sat_changed(self, satname):
        self.LogText.clear()
        self.my_satellite.name = satname
        #   EA4HCF: Let's use PCSat32 translation from NoradID to Sat names, boring but useful for next step.
        #   From NORAD_ID identifier, will get the SatName to search satellite frequencies in dopler file in next step.
        try:
            with open(SATNAMES, 'r') as g:
                namesdata = g.readlines()  
                
            for line in namesdata:
                if re.search(satname, line):
                    self.my_satellite.noradid = line.split(" ")[0].strip()
        except IOError:
            raise MyError()
        
        if self.my_satellite.noradid == 0:
            self.LogText.append("***  Satellite not found in {badfile} file.".format(badfile=SATNAMES))

        #   EA4HCF: Now, let's really use PCSat32 dople file .
        #   From SatName,  will get the RX and TX frequencies.
        try:
            with open(SQFILE, 'r') as h:
                sqfdata = h.readlines()
                tpxlist=[]
                self.combo2.clear()
                for line in sqfdata:
                    if line.startswith(satname):
                        tpxlist += [str(line.split(",")[8].strip())]
                        
                tpxlist=list(dict.fromkeys(tpxlist))
                self.combo2.addItems(tpxlist)  
                    
        except IOError:
            raise MyError()
            
    def tpx_changed(self, tpxname):
        global F0
        global I0
        global f_cal
        global i_cal
        global MAX_OFFSET_RX
        global MAX_OFFSET_TX
        
        try:
            with open(SQFILE, 'r') as h:
                sqfdata = h.readlines()
                for lineb in sqfdata:
                    if lineb.startswith(";") == 0:
                        if lineb.split(",")[8].strip() == tpxname and lineb.split(",")[0].strip() == self.my_satellite.name:
                            self.my_satellite.F = self.my_satellite.F_init = float(lineb.split(",")[1].strip())*1000
                            self.rxfreq.setText(str(self.my_satellite.F))
                            F0 = self.my_satellite.F + f_cal
                            self.my_satellite.I = self.my_satellite.I_init = float(lineb.split(",")[2].strip())*1000
                            self.txfreq.setText(str(self.my_satellite.I))
                            I0 = self.my_satellite.I + i_cal
                            self.my_satellite.downmode =  lineb.split(",")[3].strip()
                            self.my_satellite.upmode =  lineb.split(",")[4].strip()
                            self.my_satellite.mode =  lineb.split(",")[5].strip()
                            #  check if frequencies are in the same band: e.g. U/U, V/V vs V/U, U/V
                            if abs(self.my_satellite.F - self.my_satellite.I) > 10000000:
                                self.my_satellite.rig_satmode = 1
                            else:
                                self.my_satellite.rig_satmode = 0
                            if self.my_satellite.noradid == 0 or self.my_satellite.F == 0 or self.my_satellite.I == 0:
                                self.Startbutton.setEnabled(False)
                                self.Stopbutton.setEnabled(False)
                                self.syncbutton.setEnabled(False)
                            else:
                                self.Startbutton.setEnabled(True)
                                self.syncbutton.setEnabled(True)
                            break
        except IOError:
            raise MyError()

        self.rxoffsetbox.setValue(0)
        for tpx in useroffsets:
            if tpx[0] == self.my_satellite.name and tpx[1] == tpxname:

                usrrxoffset=int(tpx[2])

                if usrrxoffset < MAX_OFFSET_RX and usrrxoffset > -MAX_OFFSET_RX:
                    self.rxoffsetbox.setMaximum(MAX_OFFSET_RX)
                    self.rxoffsetbox.setMinimum(-MAX_OFFSET_RX)
                    self.rxoffsetbox.setValue(usrrxoffset)
                    self.my_satellite.new_cal = 1
                    self.my_satellite.F_cal =  f_cal = usrrxoffset
                else:
                    self.LogText.append("***  ERROR: Max RX offset ({max}) not align with user offset: {value}.".format(value=usrrxoffset,max =MAX_OFFSET_RX))
                    self.rxoffsetbox.setValue(0)
                
                

        try:
            with open(TLEFILE, 'r') as f:
                data = f.readlines()   
                
                for index, line in enumerate(data):
                    if str(self.my_satellite.noradid) in line[2:7]:
                        self.my_satellite.tledata = ephem.readtle(data[index-1], data[index], data[index+1])
                        break
        except IOError:
            raise MyError()
        
        if self.my_satellite.tledata == "":
            self.LogText.append("***  Satellite not found in {badfile} file.".format(badfile=TLEFILE))
            self.Startbutton.setEnabled(False)
            self.syncbutton.setEnabled(False)
            return
        else:
            day_of_year = datetime.now().timetuple().tm_yday
            tleage = int(data[index][20:23])
            diff = day_of_year - tleage

            if diff > 7:
                self.LogText.append("***  Warning, your TLE file is getting older: {days} days.".format(days=diff))
            
        self.timer.start()
        
    def tone_changed(self, tone_name):
        
        if self.my_satellite.rig_satmode == 1:
            icomTrx.setVFO("Sub")
        else:
            icomTrx.setVFO("VFOB")
            
        if tone_name == "67 Hz":
            icomTrx.setToneHz(str(670))
            icomTrx.setToneOn(1)
        elif tone_name == "71.9 Hz":
            icomTrx.setToneHz(str(719))
            icomTrx.setToneOn(1)
        elif tone_name == "None":
            icomTrx.setToneOn(0)
            
        if self.my_satellite.rig_satmode == 1:
            icomTrx.setVFO("Main")
        else:
            icomTrx.setVFO("VFOA")

    def the_exit_button_was_clicked(self):
        icomTrx.close()
        sys.exit()
    
    def the_stop_button_was_clicked(self):
        global TRACKING_ACTIVE
        global INTERACTIVE
        TRACKING_ACTIVE = INTERACTIVE = False
        self.LogText.append("Stopped")
        self.Stopbutton.setEnabled(False)
        self.Startbutton.setEnabled(True)
        #self.syncbutton.setEnabled(False)
        self.combo1.setEnabled(True)
        self.combo2.setEnabled(True)
    def the_sync_button_was_clicked(self):
        self.my_satellite.F = self.my_satellite.F_init
        self.my_satellite.I = self.my_satellite.I_init
    
    def init_worker(self):
        global TRACKING_ACTIVE
        self.syncbutton.setEnabled(True)
        self.Stopbutton.setEnabled(True)

        if TRACKING_ACTIVE == False:
            TRACKING_ACTIVE = True
        # Pass the function to execute
        self.LogText.append("Sat TLE data {tletext}".format(tletext=self.my_satellite.tledata))
        self.LogText.append("Tracking: {sat_name}".format(sat_name=self.my_satellite.noradid))
        self.LogText.append("Sat DownLink mode: {sat_mode_down}".format(sat_mode_down=self.my_satellite.downmode))
        self.LogText.append("Sat UpLink mode: {sat_mode_up}".format(sat_mode_up=self.my_satellite.upmode))
        #self.LogText.append("Recieve Frequency (F) = {rx_freq}".format(rx_freq=self.my_satellite.F))
        #self.LogText.append("Transmit Frequency (I) = {tx_freq}".format(tx_freq=self.my_satellite.I))
        self.LogText.append("RX Frequency Offset = {rxfreq_off}".format(rxfreq_off=f_cal))
        self.LogText.append("TX Frequency Offset = {txfreq_off}".format(txfreq_off=i_cal))
        self.Startbutton.setEnabled(False)
        self.combo1.setEnabled(False)
        self.combo2.setEnabled(False)

        worker = Worker(self.calc_doppler)

        # Execute
        self.threadpool.start(worker)

    def calc_doppler(self, progress_callback):
        global CVIADDR
        global TRACKING_ACTIVE
        global INTERACTIVE
        global myloc
        global f_cal
        global i_cal
        global F0
        global I0
        global doppler_thres
        
        try:
                #################################
                #       INIT RADIOS
                #################################
                if RADIO == "9700" and self.my_satellite.rig_satmode == 0: #not implemented yet
                    pass
                elif RADIO == "910" and self.my_satellite.rig_satmode == 0:
                    icomTrx.setSatelliteMode(0)
                    icomTrx.setSplitOn(1)
                elif RADIO == "910" and self.my_satellite.rig_satmode == 1:
                    icomTrx.setSatelliteMode(1)
                    icomTrx.setSplitOn(0)
                elif ( RADIO == "705" or "818" ) and OPMODE == False and self.my_satellite.rig_satmode == 0: #not implemented yet
                    pass

                #################################
                #       SETUP DOWNLINK & UPLINK
                #################################
                
                # IC 910
                if RADIO == "910":
                    # Testing current satmode config for V/U or U/V and swapping if needed
                    
                    if True: #self.my_satellite.rig_satmode == 1:
                        icomTrx.setVFO("Main")
                        curr_band = int(icomTrx.getFrequency())
                        if curr_band > 400000000 and F0 < 400000000:
                            icomTrx.setExchange()
                        elif curr_band < 200000000 and F0 > 200000000:
                            icomTrx.setExchange()
                            
                    if self.my_satellite.rig_satmode == 1:
                        icomTrx.setVFO("Main")
                    else:
                        icomTrx.setVFO("VFOA")
                    icomTrx.setToneOn(0)
                    if self.my_satellite.downmode == "FM":
                        icomTrx.setMode("FM")
                        doppler_thres = DOPPLER_THRES_FM
                        INTERACTIVE = False
                    elif self.my_satellite.downmode == "FMN":
                        icomTrx.setMode("FM")
                        doppler_thres = DOPPLER_THRES_FM
                        INTERACTIVE = False
                    elif self.my_satellite.downmode ==  "LSB" or self.my_satellite.downmode ==  "DATA-LSB":
                        INTERACTIVE = True
                        icomTrx.setMode("LSB")
                        doppler_thres = DOPPLER_THRES_LINEAR
                    elif self.my_satellite.downmode ==  "USB" or self.my_satellite.downmode ==  "DATA-USB":
                        INTERACTIVE = True
                        icomTrx.setMode("USB")
                        doppler_thres = DOPPLER_THRES_LINEAR       
                    elif self.my_satellite.downmode == "CW":
                        INTERACTIVE = True
                        icomTrx.setMode("CW") 
                        doppler_thres = DOPPLER_THRES_LINEAR
                    else:
                        print("*** Downlink mode not implemented yet: {bad}".format(bad=self.my_satellite.downmode))
                        sys.exit()
                    doppler_thres = int(doppler_thres)
                    self.dopplerthresval.setText(str(doppler_thres) + " Hz")
                    if self.my_satellite.rig_satmode == 1:
                        icomTrx.setVFO("SUB")
                    else:
                        icomTrx.setVFO("VFOB")
                    icomTrx.setToneOn(0)
                    if self.my_satellite.upmode == "FM":
                        icomTrx.setMode("FM")
                    elif self.my_satellite.upmode == "FMN":
                        icomTrx.setMode("FM")
                    elif self.my_satellite.upmode == "LSB" or self.my_satellite.downmode ==  "DATA-LSB":
                        icomTrx.setMode("LSB")
                    elif self.my_satellite.upmode == "USB" or self.my_satellite.downmode ==  "DATA-USB":
                        icomTrx.setMode("USB")
                    elif self.my_satellite.upmode == "CW":
                        icomTrx.setMode("CW") 
                    else:
                        print("*** Uplink mode not implemented yet: {bad}".format(bad=self.my_satellite.upmode))
                        sys.exit()
                elif RADIO != "910":
                    print("*** Not implemented yet mate***")
                    sys.exit()

                print("All config done, starting doppler...")
                icomTrx.setVFO("Main") 

                date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                myloc.date = ephem.Date(date_val)

                F0 = rx_dopplercalc(self.my_satellite.tledata, self.my_satellite.F)
                I0 = tx_dopplercalc(self.my_satellite.tledata, self.my_satellite.I)
                self.LogText.append("Start RX@sat: {rx}".format(rx=self.my_satellite.F))
                self.LogText.append("Start TX@sat: {tx}".format(tx=self.my_satellite.I))
                self.LogText.append("Start RX@radio: {rx}".format(rx=F0))
                self.LogText.append("Start TX@radio: {tx}".format(tx=I0))
                self.rxdoppler_val.setText(str(float(rx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.F))))
                self.txdoppler_val.setText(str(float(tx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.I))))
                user_Freq = 0;
                user_Freq_history = [0, 0, 0, 0]
                vfo_not_moving = 0
                vfo_not_moving_old = 0
                
                if self.my_satellite.rig_satmode == 1:
                    icomTrx.setVFO("Main")
                    icomTrx.setToneOn(0)
                    icomTrx.setFrequency(str(int(F0)))
                    icomTrx.setVFO("SUB")
                    icomTrx.setFrequency(str(int(I0)))
                else:
                    icomTrx.setVFO("VFOA")
                    icomTrx.setToneOn(0)
                    icomTrx.setFrequency(str(int(F0)))
                    icomTrx.setVFO("VFOB")
                    icomTrx.setFrequency(str(int(I0)))
                    INTERACTIVE = False #for SSB packet sats
                
                # Ensure that initial frequencies are always written 
                tracking_init = 1

                while TRACKING_ACTIVE == True:
                    date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                    myloc.date = ephem.Date(date_val)

                    if INTERACTIVE == True:
                        
                        # Set RX VFO as standard
                        if self.my_satellite.rig_satmode == 1:
                            icomTrx.setVFO("Main")
                        else:
                            icomTrx.setVFO("VFOA")
                            
                        # read current RX
                        try:
                            user_Freq = int(icomTrx.getFrequency())
                            updated_rx = 1
                            user_Freq_history.pop(0)
                            user_Freq_history.append(user_Freq)
                        except:
                            updated_rx = 0
                            user_Freq = 0
                        
                        vfo_not_moving_old = vfo_not_moving
                        vfo_not_moving = user_Freq_history.count(user_Freq_history[0]) == len(user_Freq_history)
                        #print("Last n frequencies: " +str(user_Freq_history) +" --> no change: " + str(vfo_not_moving))
                        # check for valid received freq and if dial is not moving (last two read frequencies are the same)
                        if user_Freq > 0 and updated_rx == 1 and vfo_not_moving and self.my_satellite.new_cal == 0:
                            # check if there is an offset from the dial and move up/downlink accordingly
                            if abs(user_Freq - F0) > 1:
                                if True:
                                    if user_Freq > F0:
                                        delta_F = user_Freq - F0
                                        if self.my_satellite.mode == "REV":
                                            self.my_satellite.I -= delta_F
                                            I0 -= delta_F
                                            self.my_satellite.F += delta_F
                                        else:
                                            self.my_satellite.I += delta_F
                                            I0 += delta_F
                                            self.my_satellite.F += delta_F
                                    else:
                                        delta_F = F0 - user_Freq
                                        if self.my_satellite.mode == "REV":
                                            self.my_satellite.I += delta_F
                                            I0 += delta_F
                                            self.my_satellite.F -= delta_F
                                        else:
                                            self.my_satellite.I -= delta_F
                                            I0 -= delta_F
                                            self.my_satellite.F -= delta_F
                                    F0 = user_Freq
                                            
                        # check if dial isn't moving, might be skipable as later conditional check yields the same         
                        if updated_rx and vfo_not_moving and vfo_not_moving_old:#old_user_Freq == user_Freq and False:
                            new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata, self.my_satellite.F + self.my_satellite.F_cal))
                            if abs(new_rx_doppler-F0) > doppler_thres:
                                rx_doppler = new_rx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("Main")
                                else:
                                    icomTrx.setVFO("VFOA")
                                #print(self.my_satellite.F_cal)
                                icomTrx.setFrequency(str(rx_doppler))
                                F0 = rx_doppler
                        
                            new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata, self.my_satellite.I))
                            if abs(new_tx_doppler-I0) > doppler_thres:
                                tx_doppler = new_tx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("SUB")
                                else:
                                    icomTrx.setVFO("VFOB")
                                    # Don't switch VFO when PTT is pushed, to avoid switching VFO while TX 
                                    while icomTrx.isPttOff == 0:
                                        time.sleep(0.1)
                                        
                                icomTrx.setFrequency(str(tx_doppler))
                                I0 = tx_doppler
                    # FM sats, no dial input accepted!
                    else:
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata,self.my_satellite.F + self.my_satellite.F_cal))
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata,self.my_satellite.I))
                        if abs(new_rx_doppler-F0) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                rx_doppler = new_rx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("MAIN")
                                else:
                                    icomTrx.setVFO("VFOA")
                                icomTrx.setFrequency(str(rx_doppler))
                                F0 = rx_doppler
                                time.sleep(0.2)
                        if abs(new_tx_doppler-I0) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                tx_doppler = new_tx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("SUB")
                                else:
                                    # Don't switch VFO when PTT is pushed, to avoid switching VFO while TX 
                                    while icomTrx.isPttOff == 0:
                                        time.sleep(0.2)
                                        print("PTT is enganged, waiting....")
                                    icomTrx.setVFO("VFOB")
                                icomTrx.setFrequency(str(tx_doppler))
                                I0 = tx_doppler
                                time.sleep(0.2)
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("MAIN")
                                else:
                                    icomTrx.setVFO("VFOA")
                    self.my_satellite.new_cal = 0
                    time.sleep(0.01)
                    

        except:
            print("Failed to open ICOM rig")
            sys.exit()
    
    def recurring_timer(self):
        date_val = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
        myloc.date = ephem.Date(date_val)
        self.my_satellite.down_doppler_old = self.my_satellite.down_doppler
        self.my_satellite.down_doppler = float(rx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.F))
        self.my_satellite.down_doppler_rate = ((self.my_satellite.down_doppler - self.my_satellite.down_doppler_old)/2)/0.2
        if abs(self.my_satellite.down_doppler_rate) > 100.0:
            self.my_satellite.down_doppler_rate = 0.0
            
        self.my_satellite.up_doppler_old = self.my_satellite.up_doppler
        self.my_satellite.up_doppler = float(tx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.I))
        self.my_satellite.up_doppler_rate = ((self.my_satellite.up_doppler - self.my_satellite.up_doppler_old)/2)/0.2
        if abs(self.my_satellite.up_doppler_rate) > 100.0:
            self.my_satellite.up_doppler_rate = 0.0
            
        self.rxdoppler_val.setText(str(self.my_satellite.down_doppler) + " Hz")
        self.txdoppler_val.setText(str(self.my_satellite.up_doppler) + " Hz")
        self.rxdopplerrate_val.setText(str(format(self.my_satellite.down_doppler_rate, '.2f')) + " Hz/s")
        self.txdopplerrate_val.setText(str(format(self.my_satellite.up_doppler_rate, '.2f')) + " Hz/s")
        self.rxfreq.setText(str(F0))
        self.rxfreq_onsat.setText(str(float(self.my_satellite.F)))
        self.txfreq.setText(str(I0))
        self.txfreq_onsat.setText(str(float(self.my_satellite.I)))

class WorkerSignals(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(object)
    progress = pyqtSignal(int)

class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['progress_callback'] = self.signals.progress

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

## Starts here:
if RADIO != "9700" and RADIO != "705" and RADIO != "818" and RADIO != "910":
    print("***  Icom radio not supported: {badmodel}".format(badmodel=RADIO))
    sys.exit()

socket.setdefaulttimeout(15)

#try:
#   urllib.request.urlretrieve(TLEURL, TLEFILE)
#except Exception as e:
#   print("***  Unable to download TLE file: {theurl}".format(theurl=TLEURL))

app = QApplication(sys.argv)
window = MainWindow()
apply_stylesheet(app, theme='dark_lightgreen.xml')
tooltip_stylesheet = """
        QToolTip {
            color: white;
            background-color: black;
        }
        QComboBox {
            color: white;
        }
        QSpinBox {
            color: white;
        }
    """
app.setStyleSheet(app.styleSheet()+tooltip_stylesheet)
window.show()
app.exec()

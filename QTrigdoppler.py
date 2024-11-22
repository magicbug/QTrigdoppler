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
def sat_ele_calc(ephemdata):
    ephemdata.compute(myloc)
    ele = format(ephemdata.alt/ math.pi * 180.0,'.2f' )
    return ele    
def sat_azi_calc(ephemdata):
    ephemdata.compute(myloc)
    azi = format(ephemdata.az/ math.pi * 180.0,'.2f' )
    return azi
def sat_height_calc(ephemdata):
    ephemdata.compute(myloc)
    height = format(float(ephemdata.elevation)/1000.0,'.2f') 
    return height
    
    
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
FM_update_time = 0.3

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
        # QTH
        myFont=QFont()
        myFont.setBold(True)

        pagelayout = QVBoxLayout()  

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
        
        ### All of this should be moved to a global settings struct ....
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
        global SQFILE

        # Radio
        global RADIO
        global CVIADDR
        global OPMODE

        self.counter = 0
        self.my_satellite = Satellite()

        self.setWindowTitle("QT RigDoppler v0.4")
        #self.setGeometry(3840*2, 0, 718, 425)
        
        ### Overview Page

        overview_pagelayout = QVBoxLayout()

        control_layout = QHBoxLayout()
        log_layout = QHBoxLayout()
        #log_layout.setAlignment(Qt.AlignVCenter)

        overview_pagelayout.addLayout(control_layout)
        overview_pagelayout.addLayout(log_layout)
        
        labels_layout = QVBoxLayout()
        combo_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        combo_layout.setAlignment(Qt.AlignVCenter)

        control_layout.addLayout(combo_layout, stretch=1)
        control_layout.addLayout(labels_layout, stretch=1)
        control_layout.addLayout(button_layout, stretch=1)

        self.sattext = QLabel("Satellite:")
        self.sattext.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        combo_layout.addWidget(self.sattext)

        self.combo1 = QComboBox()
        self.sat_list_view = self.combo1.view()
        self.sat_list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)        
        QScroller.grabGesture(self.sat_list_view.viewport(), QScroller.LeftMouseButtonGesture)
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
        self.tpx_list_view = self.combo1.view()
        self.tpx_list_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)        
        QScroller.grabGesture(self.tpx_list_view.viewport(), QScroller.LeftMouseButtonGesture)
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
        self.rxfreqtitle.setStyleSheet("QLabel{font-size: 12pt;}")
        self.rxfreqtitle.setFont(myFont)
        rx_labels_radio_layout.addWidget(self.rxfreqtitle)

        self.rxfreq = QLabel("435,500,000.0 Hz")
        self.rxfreq.setStyleSheet("QLabel{font-size: 12pt;}")
        self.rxfreq.setFont(myFont)
        rx_labels_radio_layout.addWidget(self.rxfreq)
        
        vbox_downlink.addLayout(rx_labels_radio_layout)

        rx_labels_sat_layout = QHBoxLayout()
        # 1x Label: RX freq Satellite
        self.rxfreqsat_lbl = QLabel("RX @ Sat:")
        rx_labels_sat_layout.addWidget(self.rxfreqsat_lbl)

        self.rxfreq_onsat = QLabel("435,500,000.0 Hz")
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
        self.txfreqtitle.setStyleSheet("QLabel{font-size: 12pt;}")
        self.txfreqtitle.setFont(myFont)
        tx_labels_radio_layout.addWidget(self.txfreqtitle)

        self.txfreq = QLabel("145,900,000.0 Hz")
        self.txfreq.setStyleSheet("QLabel{font-size: 12pt;}")
        self.txfreq.setFont(myFont)
        tx_labels_radio_layout.addWidget(self.txfreq)
        
        vbox_uplink.addLayout(tx_labels_radio_layout)

        tx_labels_sat_layout = QHBoxLayout()
        # 1x Label: TX freq Satellite
        self.txfreqsat_lbl = QLabel("TX @ Sat:")
        tx_labels_sat_layout.addWidget(self.txfreqsat_lbl)

        self.txfreq_onsat = QLabel("145,900,000.0 Hz")
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
        self.syncbutton = QPushButton("Sync to SQF")
        self.syncbutton.clicked.connect(self.the_sync_button_was_clicked)
        button_layout.addWidget(self.syncbutton)
        self.syncbutton.setEnabled(False)
        
        self.store_offset_button = QPushButton("Store offset")
        #self.store_offset_button.clicked.connect(self.the_sync_button_was_clicked)
       # button_layout.addWidget(self.store_offset_button)
        self.store_offset_button.setEnabled(False)

        # 1x QPushButton (Exit)
        self.Exitbutton = QPushButton("Exit")
        self.Exitbutton.setCheckable(True)
        self.Exitbutton.clicked.connect(self.the_exit_button_was_clicked)
        button_layout.addWidget(self.Exitbutton)

        # Output log
        
        self.log_sat_status = QGroupBox()
        self.log_sat_status.setStyleSheet("QGroupBox{padding-top:5px;padding-bottom:5px; margin-top:0px;font-size: 18pt;} QLabel{font-size: 18pt;}")
        log_sat_status_layout = QGridLayout()
        
        self.log_sat_status_ele_lbl = QLabel("Elevation:")
        log_sat_status_layout.addWidget(self.log_sat_status_ele_lbl, 0, 0)

        self.log_sat_status_ele_val = QLabel("0.0 °")
        log_sat_status_layout.addWidget(self.log_sat_status_ele_val, 0, 1)
        
        self.log_sat_status_azi_lbl = QLabel("Azimuth:")
        log_sat_status_layout.addWidget(self.log_sat_status_azi_lbl, 0, 2)

        self.log_sat_status_azi_val = QLabel("0.0 °")
        log_sat_status_layout.addWidget(self.log_sat_status_azi_val, 0, 3)
        
        self.log_sat_status_height_lbl = QLabel("Height:")
        log_sat_status_layout.addWidget(self.log_sat_status_height_lbl, 0, 4)

        self.log_sat_status_height_val = QLabel("0.0 m")
        log_sat_status_layout.addWidget(self.log_sat_status_height_val, 0, 5)
        
        self.log_sat_status.setLayout(log_sat_status_layout)
        log_layout.addWidget(self.log_sat_status, 1)
        
        ### Settings Tab
        settings_layout = QHBoxLayout()
        
        
        # QTH Tab
        self.settings_qth_box = QGroupBox("QTH")
        self.settings_qth_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        settings_layout.addWidget(self.settings_qth_box)
        
        # Radio Tab (scrollable for smaller screens)
        self.settings_radio_box = QGroupBox("Radio")
        self.settings_radio_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        settings_layout.addWidget(self.settings_radio_box)
        
        # Files Tab
        self.settings_file_box = QGroupBox("Files")
        self.settings_file_box.setStyleSheet("QGroupBox{padding-top:1px;padding-bottom:5px; margin-top:5px}")
        settings_layout.addWidget(self.settings_file_box)
        
        
        ## QTH
        qth_settings_layout = QGridLayout()
        
        # LAT
        self.qth_settings_lat_lbl = QLabel("QTH latitude:")
        qth_settings_layout.addWidget(self.qth_settings_lat_lbl, 0,0)
        self.qth_settings_lat_edit = QLineEdit()
        self.qth_settings_lat_edit.setMaxLength(10)
        self.qth_settings_lat_edit.setText(str(LATITUDE))
        qth_settings_layout.addWidget(self.qth_settings_lat_edit, 0,1)        
        
        # LONG
        self.qth_settings_long_lbl = QLabel("QTH longitude:")
        qth_settings_layout.addWidget(self.qth_settings_long_lbl, 1, 0)
        self.qth_settings_long_edit = QLineEdit()
        self.qth_settings_long_edit.setMaxLength(10)
        self.qth_settings_long_edit.setText(str(LONGITUDE))
        qth_settings_layout.addWidget(self.qth_settings_long_edit, 1, 1)        
        
        # Altitude
        self.qth_settings_alt_lbl = QLabel("QTH Altitude:")
        qth_settings_layout.addWidget(self.qth_settings_alt_lbl, 2, 0)
        self.qth_settings_alt_edit = QLineEdit()
        self.qth_settings_alt_edit.setMaxLength(10)
        self.qth_settings_alt_edit.setText(str(ALTITUDE))
        qth_settings_layout.addWidget(self.qth_settings_alt_edit, 2, 1)

        self.settings_qth_box.setLayout(qth_settings_layout)
        
        ## Radio
        self.radio_settings_layout_scroller = QScrollArea()
        self.radio_settings_layout_scroller_widget = QWidget()
        radio_settings_layout = QGridLayout()
        
        # Radio selector
        self.radiolist_lbl = QLabel("Select radio:")
        radio_settings_layout.addWidget(self.radiolist_lbl, 0, 0)
        self.radiolistcomb = QComboBox()
        self.radiolistcomb.addItems(['Icom 9700'])
        #self.radiolistcomb.addItems(['Icom 705'])
        #self.radiolistcomb.addItems(['Yaesu 818'])
        self.radiolistcomb.addItems(['Icom 910H'])
        if configur['icom']['radio'] == '9700':
            self.radiolistcomb.setCurrentText('Icom 9700')
        elif configur['icom']['radio'] == '910':
            self.radiolistcomb.setCurrentText('Icom 910H')
        radio_settings_layout.addWidget(self.radiolistcomb, 0, 1)
        
        # CI-V selector
        self.radicvi_lbl = QLabel("CVI address:")
        radio_settings_layout.addWidget(self.radicvi_lbl, 1, 0)
        self.radicvi = QLineEdit()
        self.radicvi.setMaxLength(2)
        self.radicvi.setText(CVIADDR)
        radio_settings_layout.addWidget(self.radicvi, 1, 1)
        
        # 1x Label step RX
        self.qthsteprx_lbl = QLabel("Step (Hz) for RX:")
        radio_settings_layout.addWidget(self.qthsteprx_lbl, 2, 0)

        self.qthsteprx = QLineEdit()
        self.qthsteprx.setMaxLength(10)
        self.qthsteprx.setText(str(STEP_RX))
        radio_settings_layout.addWidget(self.qthsteprx, 2, 1)

        # 1x Label step TX
        self.qthsteptx_lbl = QLabel("Step (Hz) for TX:")
        radio_settings_layout.addWidget(self.qthsteptx_lbl, 3, 0)

        self.qthsteptx = QLineEdit()
        self.qthsteptx.setMaxLength(10)
        self.qthsteptx.setText(str(STEP_TX))
        radio_settings_layout.addWidget(self.qthsteptx, 3,1)

        # 1x Label Max Offset RX
        self.qthmaxoffrx_lbl = QLabel("Max Offset (Hz) for RX:")
        radio_settings_layout.addWidget(self.qthmaxoffrx_lbl, 4, 0)

        self.qthmaxoffrx = QLineEdit()
        self.qthmaxoffrx.setMaxLength(6)
        self.qthmaxoffrx.setText(str(MAX_OFFSET_RX))
        radio_settings_layout.addWidget(self.qthmaxoffrx, 4, 1)

        # 1x Label Max Offset TX
        self.qthmaxofftx_lbl = QLabel("Max Offset (Hz) for TX:")
        radio_settings_layout.addWidget(self.qthmaxofftx_lbl, 5, 0)

        self.qthmaxofftx = QLineEdit()
        self.qthmaxofftx.setMaxLength(6)
        self.qthmaxofftx.setText(str(MAX_OFFSET_TX))
        radio_settings_layout.addWidget(self.qthmaxofftx, 5, 1)
        
        # 1x Label doppler fm threshold
        self.doppler_fm_threshold_lbl = QLabel("Doppler threshold for FM")
        radio_settings_layout.addWidget(self.doppler_fm_threshold_lbl, 6, 0)

        self.doppler_fm_threshold = QLineEdit()
        self.doppler_fm_threshold.setMaxLength(6)
        self.doppler_fm_threshold.setText(str(DOPPLER_THRES_FM))
        radio_settings_layout.addWidget(self.doppler_fm_threshold, 6, 1)
        
        # 1x Label doppler linear threshold
        self.doppler_linear_threshold_lbl = QLabel("Doppler threshold for Linear")
        radio_settings_layout.addWidget(self.doppler_linear_threshold_lbl, 7, 0)

        self.doppler_linear_threshold = QLineEdit()
        self.doppler_linear_threshold.setMaxLength(6)
        self.doppler_linear_threshold.setText(str(DOPPLER_THRES_LINEAR))
        radio_settings_layout.addWidget(self.doppler_linear_threshold, 7, 1)
        
        #self.settings_radio_box.setLayout(radio_settings_layout)
        self.radio_settings_layout_scroller_widget.setLayout(radio_settings_layout)
        self.radio_settings_layout_scroller.setWidget(self.radio_settings_layout_scroller_widget)
        self.radio_settings_layout_scroller.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.radio_settings_layout_scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.radio_settings_layout_scroller.setWidgetResizable(True)
        self.radio_settings_layout_scroller_layout = QHBoxLayout()
        self.radio_settings_layout_scroller_layout.addWidget(self.radio_settings_layout_scroller)
        self.settings_radio_box.setLayout(self.radio_settings_layout_scroller_layout)
        
        ## Files
        files_settings_layout = QGridLayout()

        # 1x Label TLE file
        self.sattle_lbl = QLabel("TLE filename:")
        files_settings_layout.addWidget(self.sattle_lbl, 0, 0)

        self.sattle = QLineEdit()
        self.sattle.setMaxLength(30)
        self.sattle.setText(TLEFILE)
        files_settings_layout.addWidget(self.sattle, 0, 1)

        # 1x Label TLE URL
        self.sattleurl_lbl = QLabel("TLE URL:")
        files_settings_layout.addWidget(self.sattleurl_lbl, 1, 0)

        self.sattleurl = QLineEdit()
        self.sattleurl.setMaxLength(70)
        self.sattleurl.setText(TLEURL)
        files_settings_layout.addWidget(self.sattleurl, 1, 1)


        # 1x Label SQF file
        self.satsqf_lbl = QLabel("SQF filename:")
        files_settings_layout.addWidget(self.satsqf_lbl, 2, 0)

        self.satsqf = QLineEdit()
        self.satsqf.setMaxLength(30)
        self.satsqf.setText(SQFILE)
        files_settings_layout.addWidget(self.satsqf, 2, 1)
        
        self.settings_file_box.setLayout(files_settings_layout)
        
        

        ###  UI Layout / Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_overview = QWidget()
        self.tab_settings = QWidget()
        self.tab_widget.addTab(self.tab_overview,"Overview")
        self.tab_widget.addTab(self.tab_settings,"Settings")
        self.tab_overview.setLayout(overview_pagelayout)
        self.tab_settings.setLayout(settings_layout)
        self.setCentralWidget(self.tab_widget)
        
        QScroller.grabGesture(
            self.combo1, QScroller.LeftMouseButtonGesture
        )

        self.threadpool = QThreadPool()
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.recurring_timer)

    def rxoffset_value_changed(self, i):
            global f_cal
            self.my_satellite.new_cal = 1
            self.my_satellite.F_cal =  f_cal = i
    
    def sat_changed(self, satname):
        self.my_satellite.name = satname

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
        
        try:
            with open(SQFILE, 'r') as h:
                sqfdata = h.readlines()
                for lineb in sqfdata:
                    if lineb.startswith(";") == 0:
                        if lineb.split(",")[8].strip() == tpxname and lineb.split(",")[0].strip() == self.my_satellite.name:
                            self.my_satellite.F = self.my_satellite.F_init = float(lineb.split(",")[1].strip())*1000
                            self.rxfreq.setText(str('{:,}'.format(self.my_satellite.F))+ " Hz")
                            F0 = self.my_satellite.F + f_cal
                            self.my_satellite.I = self.my_satellite.I_init = float(lineb.split(",")[2].strip())*1000
                            self.txfreq.setText(str('{:,}'.format(self.my_satellite.I)) + " Hz")
                            I0 = self.my_satellite.I + i_cal
                            self.my_satellite.downmode =  lineb.split(",")[3].strip()
                            self.my_satellite.upmode =  lineb.split(",")[4].strip()
                            self.my_satellite.mode =  lineb.split(",")[5].strip()
                            #  check if frequencies are in the same band: e.g. U/U, V/V vs V/U, U/V
                            if abs(self.my_satellite.F - self.my_satellite.I) > 10000000:
                                self.my_satellite.rig_satmode = 1
                            else:
                                self.my_satellite.rig_satmode = 0
                            if self.my_satellite.F == 0 or self.my_satellite.I == 0:
                                self.Startbutton.setEnabled(False)
                                self.Stopbutton.setEnabled(False)
                                self.syncbutton.setEnabled(False)
                                self.store_offset_button.setEnabled(False)
                            else:
                                self.Startbutton.setEnabled(True)
                                self.syncbutton.setEnabled(True)
                                self.store_offset_button.setEnabled(True)
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
                    self.rxoffsetbox.setValue(0)
                
                

        try:
            with open(TLEFILE, 'r') as f:
                data = f.readlines()   
                
                for index, line in enumerate(data):
                    if str(self.my_satellite.name) in line:
                        self.my_satellite.tledata = ephem.readtle(data[index], data[index+1], data[index+2])
                        break
        except IOError:
            raise MyError()
        
        if self.my_satellite.tledata == "":
            self.Startbutton.setEnabled(False)
            self.syncbutton.setEnabled(False)
            self.store_offset_button.setEnabled(False)
            return
        else:
            #day_of_year = datetime.now().timetuple().tm_yday
            #tleage = int(data[index+1][20:23])
            #diff = day_of_year - tleage

            #if diff > 7:
            #    
            pass
            
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
        TRACKING_ACTIVE = False
        INTERACTIVE = False
        self.threadpool.clear()
        self.Stopbutton.setEnabled(False)
        self.Startbutton.setEnabled(True)
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
            
        self.Startbutton.setEnabled(False)
        self.combo1.setEnabled(False)
        self.combo2.setEnabled(False)

        self.doppler_worker = Worker(self.calc_doppler)
        self.threadpool.start(self.doppler_worker)

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

                icomTrx.setVFO("Main") 

                date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                myloc.date = ephem.Date(date_val)

                F0 = rx_dopplercalc(self.my_satellite.tledata, self.my_satellite.F)
                I0 = tx_dopplercalc(self.my_satellite.tledata, self.my_satellite.I)
                self.rxdoppler_val.setText(str('{:,}'.format(float(rx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.F)))))
                self.txdoppler_val.setText(str('{:,}'.format(float(tx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.I)))))
                user_Freq = 0;
                user_Freq_history = [0, 0, 0, 0]
                vfo_not_moving = 0
                vfo_not_moving_old = 0
                ptt_state = 0
                ptt_state_old = 0
                
                if self.my_satellite.rig_satmode == 1:
                    icomTrx.setVFO("Main")
                    #icomTrx.setToneOn(0)
                    #self.combo3.setCurrentIndex(0);
                    icomTrx.setFrequency(str(int(F0)))
                    icomTrx.setVFO("SUB")
                    icomTrx.setFrequency(str(int(I0)))
                else:
                    icomTrx.setVFO("VFOA")
                    #icomTrx.setToneOn(0)
                    #self.combo3.setCurrentIndex(0);
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
                    elif self.my_satellite.rig_satmode == 1: 
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata,self.my_satellite.F + self.my_satellite.F_cal))
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata,self.my_satellite.I))
                        if abs(new_rx_doppler-F0) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                rx_doppler = new_rx_doppler
                                icomTrx.setVFO("MAIN")
                                icomTrx.setFrequency(str(rx_doppler))
                                F0 = rx_doppler
                                time.sleep(FM_update_time)
                        if abs(new_tx_doppler-I0) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                tx_doppler = new_tx_doppler
                                icomTrx.setVFO("SUB")
                                icomTrx.setFrequency(str(tx_doppler))
                                I0 = tx_doppler
                                time.sleep(FM_update_time)
                                icomTrx.setVFO("MAIN")
                    else:
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata,self.my_satellite.F + self.my_satellite.F_cal))
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata,self.my_satellite.I))
                        # 0 = PTT is pressed
                        # 1 = PTT is released
                        ptt_state_old = ptt_state
                        ptt_state = icomTrx.isPttOff()
                        # Check for RX -> TX transition
                        if  ptt_state_old and ptt_state == 0:# and abs(new_tx_doppler-I0) > doppler_thres:
                            #icomTrx.setVFO("VFOB")
                            print("TX inititated")
                            tx_doppler = new_tx_doppler
                            I0 = tx_doppler
                            icomTrx.setFrequency(str(tx_doppler))
                        # Check for RX -> TX transition
                        if  ptt_state_old == 0 and ptt_state:# and abs(new_rx_doppler-F0) > doppler_thres:
                            print("RX inititated")
                            rx_doppler = new_rx_doppler
                            F0 = rx_doppler
                            icomTrx.setVFO("VFOA")
                            icomTrx.setFrequency(str(rx_doppler))
                        time.sleep(0.05)
                        
                    self.my_satellite.new_cal = 0
                    time.sleep(0.01)
                    

        except:
            print("Failed to open ICOM rig")
            sys.exit()
    
    def recurring_timer(self):
        try:
            date_val = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
            myloc.date = ephem.Date(date_val)
            #date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
            #myloc.date = ephem.Date(date_val)
            #print(myloc.date)
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
                
            self.rxdoppler_val.setText(str('{:,}'.format(self.my_satellite.down_doppler)) + " Hz")
            self.txdoppler_val.setText(str('{:,}'.format(self.my_satellite.up_doppler)) + " Hz")
            self.rxdopplerrate_val.setText(str(format(self.my_satellite.down_doppler_rate, '.2f')) + " Hz/s")
            self.txdopplerrate_val.setText(str(format(self.my_satellite.up_doppler_rate, '.2f')) + " Hz/s")
            self.rxfreq.setText(str('{:,}'.format(F0))+ " Hz")
            self.rxfreq_onsat.setText(str('{:,}'.format(self.my_satellite.F))+ " Hz")
            self.txfreq.setText(str('{:,}'.format(I0))+ " Hz")
            self.txfreq_onsat.setText(str('{:,}'.format(self.my_satellite.I))+ " Hz")
            self.log_sat_status_ele_val.setText(str(sat_ele_calc(self.my_satellite.tledata)) + " °")
            self.log_sat_status_azi_val.setText(str(sat_azi_calc(self.my_satellite.tledata)) + " °")
            self.log_sat_status_height_val.setText(str(sat_height_calc(self.my_satellite.tledata)) + " km")
        except:
            print("Error in label timer")
            traceback.print_exc()

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

try:
   urllib.request.urlretrieve(TLEURL, TLEFILE)
except Exception as e:
   print("***  Unable to download TLE file: {theurl}".format(theurl=TLEURL))

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
        QLineEdit {
            color: white;
        }
    """
tooltip_stylesheet_rpi = """
        QToolTip {
            color: white;
            background-color: black;
        }
        QComboBox {
            color: white;
            font-size: 20pt;
        }
        QSpinBox {
            color: white;
            font-size: 20pt;
        }
        QLineEdit {
            color: white;
        }
        QLabel{font-size: 18pt;}
        QButton{font-size: 18pt;}
        QPushButton{font-size: 20pt;}
    """
app.setStyleSheet(app.styleSheet()+tooltip_stylesheet)
#window.setWindowFlag(Qt.FramelessWindowHint)
window.show()
app.exec()

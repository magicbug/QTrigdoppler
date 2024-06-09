# Autor:
#   Original from K8DP Doug Papay (v0.1)
#
#   Adapted v0.3 by EA4HCF Pedro Cabrera


import ephem
import socket
import sys
import math
import time
import re
import urllib.request
import traceback

from contextlib import contextmanager
from time import gmtime, strftime
from datetime import datetime, timedelta

from configparser import ConfigParser

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

C = 299792458.

@contextmanager
def socketcontext(*args, **kwargs):
    s = socket.socket(*args, **kwargs)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    yield s
    s.close()

def tx_dopplercalc(ephemdata):
    global I0
    ephemdata.compute(myloc)
    doppler = int(I0 + ephemdata.range_velocity * I0 / C)
    return doppler

def rx_dopplercalc(ephemdata):
    global F0
    ephemdata.compute(myloc)
    doppler = int(F0 - ephemdata.range_velocity * F0 / C)
    return doppler

def MyError():
    print("Failed to find required file!")
    sys.exit()

print("QT Rigdoppler v0.3")

try:
    with open('config.ini') as f:
        f.close()
        configur = ConfigParser()
        configur.read('config.ini')
except IOError:
    raise MyError()


# EA4HCF, params from config.ini
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
SQFILE = configur.get('satellite','sqffile')
RADIO = configur.get('icom','radio')
CVIADDR = configur.get('icom','cviaddress')
if configur.get('icom', 'fullmode') == "True":
    OPMODE = True
elif configur.get('icom', 'fullmode') == "False":
    OPMODE = False
ADDRESS = configur.get('hamlib','address')
PORT = configur.getint('hamlib','port')
if configur.has_option('hamlib','portfull'):
    PORTFULL = configur.getint('hamlib','portfull')
else:
    PORTFULL = 5434

useroffsets = {}

for (each_key, each_val) in configur.items('offset_profiles'):
    # Format SATNAME:RXoffset,TXoffset
    useroffsets[each_val.split(':')[0]] = each_val.split(':')[1]

F0=0.0
I0=0.0
f_cal = 0
i_cal = 0

myloc = ephem.Observer()
myloc.lon = LONGITUDE
myloc.lat = LATITUDE
myloc.elevation = ALTITUDE

SEMAPHORE = True
INTERACTIVE = False

class Satellite:
    name = ""
    noradid = 0
    amsatname= ""
    downmode = ""
    upmode = ""
    mode = ""
    F = 0
    F_init = 0
    I = 0
    I_init = 0
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

        # satellite
        global TLEFILE
        global TLEURL
        global SATNAMES
        global SQFILE

        # Radio
        global RADIO
        global CVIADDR
        global OPMODE

        # Hamlib
        global ADDRESS
        global PORT
        global PORTFULL

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
        hamlib_layout = QVBoxLayout()
        offset_layout = QVBoxLayout()
        buttons_layout = QVBoxLayout()

        uplayout.addLayout(qth_layout)
        uplayout.addLayout(satellite_layout)

        mediumlayout.addLayout(radio_layout)
        mediumlayout.addLayout(hamlib_layout)

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
        self.radiolistcomb.addItems(['Icom 705'])
        self.radiolistcomb.addItems(['Yaesu 818'])
        self.radiolistcomb.addItems(['Icom 910H'])
        if configur['icom']['radio'] == '9700':
            self.radiolistcomb.setCurrentText('Icom 9700')
        elif configur['icom']['radio'] == '705':
            self.radiolistcomb.setCurrentText('Icom 705')
        elif configur['icom']['radio'] == '818':
            self.radiolistcomb.setCurrentText('Yaesu 818')
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

        ### HamLib
        self.haml = QLabel("HamLib Parameters")
        self.haml.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.haml.setFont(myFont)
        hamlib_layout.addWidget(self.haml)

        # 1x Label address address
        self.hamladd_lbl = QLabel("HamLib IP address:")
        self.hamladd_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        hamlib_layout.addWidget(self.hamladd_lbl)

        self.hamladd = QLineEdit()
        self.hamladd.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.hamladd.setMaxLength(30)
        self.hamladd.setText(ADDRESS)
        hamlib_layout.addWidget(self.hamladd)

        # 1x Label port address
        self.hamlport_lbl = QLabel("HamLib TCP port:")
        self.hamlport_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        hamlib_layout.addWidget(self.hamlport_lbl)

        self.hamlport = QLineEdit()
        self.hamlport.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.hamlport.setMaxLength(5)
        self.hamlport.setText(str(PORT))
        hamlib_layout.addWidget(self.hamlport)

        # 1x Label second port address
        self.hamlport2_lbl = QLabel("HamLib second TCP port:")
        self.hamlport2_lbl.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        hamlib_layout.addWidget(self.hamlport2_lbl)

        self.hamlport2 = QLineEdit()
        self.hamlport2.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.hamlport2.setMaxLength(5)
        self.hamlport2.setText(str(PORTFULL))
        if OPMODE == False:
            self.hamlport2.setEnabled(False)
        elif OPMODE == True:
            self.hamlport2.setEnabled(True)
        hamlib_layout.addWidget(self.hamlport2)

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
            self.offsetText.append("{name}:{theoffsets}".format(name=each_val.split(':')[0],theoffsets=each_val.split(':')[1]))

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

        # satellite
        global TLEFILE
        global TLEURL
        global SATNAMES
        global SQFILE

        # Radio
        global RADIO
        global CVIADDR
        global OPMODE

        # Hamlib
        global ADDRESS
        global PORT
        global PORTFULL

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
        if self.radiolistcomb.currentText() == "Icom 9700":
            RADIO = configur['icom']['radio'] = '9700'
        elif self.radiolistcomb.currentText() == "Icom 705":
            RADIO = configur['icom']['radio'] = '705'
        elif self.radiolistcomb.currentText() == "Yaesu 818":
            RADIO = configur['icom']['radio'] = '818'
        elif self.radiolistcomb.currentText() == "Icom 910H":
            RADIO = configur['icom']['radio'] = '910'

        if self.radidplx.isChecked():
            OPMODE = True
            configur['icom']['fullmode'] = "True"
            PORTFULL = configur['hamlib']['portfull'] = str(self.hamlport2.displayText())
        else:
            OPMODE = False
            configur['icom']['fullmode'] = "False"
            configur.remove_option('hamlib','portfull')
        CVIADDR = configur['icom']['cviaddress'] = str(self.radicvi.displayText())
        ADDRESS = configur['hamlib']['address'] = str(self.hamladd.displayText())
        configur['hamlib']['port'] = str(int(self.hamlport.displayText()))
        PORT = int(self.hamlport.displayText())

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

        self.setWindowTitle("QT RigDoppler v0.3")
        self.setGeometry(0, 0, 800, 150)

        pagelayout = QVBoxLayout()

        uplayout = QHBoxLayout()
        downlayout = QHBoxLayout()

        pagelayout.addLayout(uplayout)
        pagelayout.addLayout(downlayout)
        
        labels_layout = QVBoxLayout()
        combo_layout = QVBoxLayout()
        offset_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        combo_layout.setAlignment(Qt.AlignVCenter)

        uplayout.addLayout(combo_layout)
        uplayout.addLayout(labels_layout)
        uplayout.addLayout(offset_layout)
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

        myFont=QFont()
        myFont.setBold(True)

        # 1x Label: RX freq
        self.rxfreqtitle = QLabel("RX freq:")
        self.rxfreqtitle.setFont(myFont)
        labels_layout.addWidget(self.rxfreqtitle)

        self.rxfreq = QLabel("0.0")
        self.rxfreq.setFont(myFont)
        labels_layout.addWidget(self.rxfreq)

        # 1x Label: RX freq Satellite
        self.rxfreqsat_lbl = QLabel("RX freq on Sat:")
        labels_layout.addWidget(self.rxfreqsat_lbl)

        self.rxfreq_onsat = QLabel("0.0")
        labels_layout.addWidget(self.rxfreq_onsat)

        # 1x Label: TX freq
        self.txfreqtitle = QLabel("TX freq:")
        self.txfreqtitle.setFont(myFont)
        labels_layout.addWidget(self.txfreqtitle)

        self.txfreq = QLabel("0.0")
        self.txfreq.setFont(myFont)
        labels_layout.addWidget(self.txfreq)

        # 1x Label: TX freq Satellite
        self.txfreqsat_lbl = QLabel("TX freq on Sat:")
        labels_layout.addWidget(self.txfreqsat_lbl)

        self.txfreq_onsat = QLabel("0.0")
        labels_layout.addWidget(self.txfreq_onsat)

        # 1x Label: RX Offset
        self.rxoffsetboxtitle = QLabel("RX Offset:")
        offset_layout.addWidget(self.rxoffsetboxtitle)

        # 1x QSlider (RX offset)
        self.rxoffsetbox = QSpinBox()
        self.rxoffsetbox.setMinimum(-MAX_OFFSET_RX)
        self.rxoffsetbox.setMaximum(MAX_OFFSET_RX)
        self.rxoffsetbox.setSingleStep(int(STEP_RX))
        self.rxoffsetbox.valueChanged.connect(self.rxoffset_value_changed)
        offset_layout.addWidget(self.rxoffsetbox)

        # 1x Label: TX Offset
        self.txoffsetboxtitle = QLabel("TX Offset:")
        offset_layout.addWidget(self.txoffsetboxtitle)

        # 1x QSlider (TX offset)
        self.txoffsetbox = QSpinBox()
        self.txoffsetbox.setMinimum(-MAX_OFFSET_TX)
        self.txoffsetbox.setMaximum(MAX_OFFSET_TX)
        self.txoffsetbox.setSingleStep(int(STEP_TX))
        self.txoffsetbox.valueChanged.connect(self.txoffset_value_changed)
        offset_layout.addWidget(self.txoffsetbox)

         # Start Label
        self.butontitle = QLabel("Press start to connect to Icom radio:")
        self.butontitle.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        button_layout.addWidget(self.butontitle)

        # 1x QPushButton (Start)
        self.Startbutton = QPushButton("Start")
        self.Startbutton.clicked.connect(self.init_worker)
        button_layout.addWidget(self.Startbutton)

        # 1x QPushButton (Stop)
        self.Stopbutton = QPushButton("Stop")
        self.Stopbutton.clicked.connect(self.the_stop_button_was_clicked)
        button_layout.addWidget(self.Stopbutton)

        # Exit Label
        self.exitbutontitle = QLabel("Disconect and exit:")
        self.exitbutontitle.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        button_layout.addWidget(self.exitbutontitle)

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
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.recurring_timer)
        self.timer.start()

    def setup_config(self, checked):
        self.cfgwindow = ConfigWindow()
        self.cfgwindow.show()

    def rxoffset_value_changed(self, i):
            global f_cal
            global F0
            f_cal = i
            F0 = self.my_satellite.F_init + f_cal
            self.LogText.append("*** New RX offset: {thenew}".format(thenew=i))
    
    def txoffset_value_changed(self, i):
            global i_cal
            global I0
            i_cal = i
            I0 = self.my_satellite.I_init + i_cal
            self.LogText.append("*** New TX offset: {thenew}".format(thenew=i))
    
    def sat_changed(self, satname):
        global F0
        global I0
        global f_cal
        global i_cal
        global MAX_OFFSET_RX
        global MAX_OFFSET_TX

        self.LogText.clear()
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
                
            for lineb in sqfdata:
                if re.search(satname, lineb):
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
                    else:
                        self.Startbutton.setEnabled(True)
                    break
        except IOError:
            raise MyError()

        if satname in useroffsets:
            usrrxoffset=int(useroffsets[satname].split(',')[0])
            usrtxoffset=int(useroffsets[satname].split(',')[1])

            if usrrxoffset < MAX_OFFSET_RX and usrrxoffset > -MAX_OFFSET_RX:
                self.rxoffsetbox.setMaximum(MAX_OFFSET_RX)
                self.rxoffsetbox.setMinimum(-MAX_OFFSET_RX)
                self.rxoffsetbox.setValue(usrrxoffset)
            else:
                self.LogText.append("***  ERROR: Max RX offset ({max}) not align with user offset: {value}.".format(value=usrrxoffset,max =MAX_OFFSET_RX))
                self.rxoffsetbox.setValue(0)
            
            if usrtxoffset < MAX_OFFSET_TX and usrtxoffset > -MAX_OFFSET_TX:
                self.txoffsetbox.setMaximum(MAX_OFFSET_TX)
                self.txoffsetbox.setMinimum(-MAX_OFFSET_TX)
                self.txoffsetbox.setValue(usrtxoffset)
            else:
                self.LogText.append("***  ERROR: Max TX offset ({max}) not align with user offset: {value}.".format(value=usrtxoffset,max=MAX_OFFSET_TX))
                self.txoffsetbox.setValue(0)
        else:
            self.rxoffsetbox.setValue(0)
            self.txoffsetbox.setValue(0)

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
            return
        else:
            day_of_year = datetime.now().timetuple().tm_yday
            tleage = int(data[index][20:23])
            diff = day_of_year - tleage

            if diff > 7:
                self.LogText.append("***  Warning, your TLE file is getting older: {days} days.".format(days=diff))

    def the_exit_button_was_clicked(self):
        if RADIO == "705" or "818":
            try:
                with socketcontext(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ADDRESS, PORT))
                    #switch off SPLIT operation
                    F_string = "S 0 VFOB\n"
                    s.send(bytes(F_string, 'ascii'))
                    time.sleep(0.2)
            except socket.error:
                print("Failed to connect to Rigctld on {addr}:{port} exiting the application.".format(addr=ADDRESS,port=PORT))
        sys.exit()
    
    def the_stop_button_was_clicked(self):
        global SEMAPHORE
        global INTERACTIVE
        SEMAPHORE = INTERACTIVE = False
        self.LogText.append("Stopped")
        self.Startbutton.setEnabled(True)
        self.combo1.setEnabled(True)
    
    def init_worker(self):
        global SEMAPHORE

        if SEMAPHORE == False:
            SEMAPHORE = True
        # Pass the function to execute
        self.LogText.append("Connected to Rigctld on {addr}:{port}".format(addr=ADDRESS,port=PORT))
        self.LogText.append("Sat TLE data {tletext}".format(tletext=self.my_satellite.tledata))
        self.LogText.append("Tracking: {sat_name}".format(sat_name=self.my_satellite.noradid))
        self.LogText.append("Sat DownLink mode: {sat_mode_down}".format(sat_mode_down=self.my_satellite.downmode))
        self.LogText.append("Sat UpLink mode: {sat_mode_up}".format(sat_mode_up=self.my_satellite.upmode))
        self.LogText.append("Recieve Frequency (F) = {rx_freq}".format(rx_freq=self.my_satellite.F))
        self.LogText.append("Transmit Frequency (I) = {tx_freq}".format(tx_freq=self.my_satellite.I))
        self.LogText.append("RX Frequency Offset = {rxfreq_off}".format(rxfreq_off=f_cal))
        self.LogText.append("TX Frequency Offset = {txfreq_off}".format(txfreq_off=i_cal))
        self.Startbutton.setEnabled(False)
        self.combo1.setEnabled(False)

        worker = Worker(self.calc_doppler)

        # Execute
        self.threadpool.start(worker)

    def calc_doppler(self, progress_callback):
        global CVIADDR
        global SEMAPHORE
        global INTERACTIVE
        global myloc
        global f_cal
        global i_cal
        global F0
        global I0
        
        try:
            with socketcontext(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((ADDRESS, PORT))

                #################################
                #       INIT RADIOS
                #################################
                if RADIO == "9700" and self.my_satellite.rig_satmode == 0:
                    # turn off satellite mode
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x16\\0x5A\\0x00\\0xFD 14\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                    #turn on scope waterfall
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x1A\\0x05\\0x01\\0x97\\0x01\\0xFD 16\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                    #show scope during TX
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x1A\\0x05\\0x01\\0x87\\0x01\\0xFD 16\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                    #set span = 5kHz
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x27\\0x15\\0x00\\0x00\\0x50\\0x00\\0x00\\0x00\\0xFD 22\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                elif RADIO == "910" and self.my_satellite.rig_satmode == 0:
                    # turn off satellite mode
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x1A\\0x07\\0x00\\0xFD 14\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                elif RADIO == "910" and self.my_satellite.rig_satmode == 1:
                    # turn on satellite mode
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x1A\\0x07\\0x01\\0xFD 14\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                    # turn off split
                    cmds = "W \\0xFE\\0xFE\\0x" + CVIADDR + "\\0xE2\\0x0F\\0x01\\0x00\\0xFD 14\n"
                    s.sendall(cmds.encode('utf-8'))
                    time.sleep(0.2)
                elif ( RADIO == "705" or "818" ) and OPMODE == False and self.my_satellite.rig_satmode == 0:
                    #check SPLIT operation
                    F_string = "s\n"
                    s.send(bytes(F_string, 'ascii'))
                    time.sleep(0.2)
                    data = s.recv(1024)
                    status = str(data).split('\\n')[0].replace("b\'",'')

                    if int(status) == 0:
                        print("Setting split mode ON ({a})".format(a=status))
                        F_string = "S 1 VFOB\n"
                        s.send(bytes(F_string, 'ascii'))
                        time.sleep(0.2)
                    else:
                        print("Split mode already ON ({a})".format(a=status))

                #################################
                #       SETUP DOWNLINK & UPLINK
                #################################
                F_string = "m\n"
                s.send(bytes(F_string, 'ascii'))
                time.sleep(0.2)
                data = s.recv(1024)
                curr_mode = str(data)
                print("Current mode VFO-A: ({a})".format(a=curr_mode))
                
                s.sendall(b"V VFOA\n")
                time.sleep(0.2) 
                if self.my_satellite.downmode == "FM":
                    #set VFOA to FM mode
                    s.sendall(b"M FM 15000\n")
                    time.sleep(0.2)
                elif self.my_satellite.downmode == "FMN":
                    #set VFOA to WFM mode
                    s.sendall(b"M WFM 15000\n")
                    time.sleep(0.2)
                elif self.my_satellite.downmode ==  "USB":
                    INTERACTIVE = True
                    print("Set VFO A modulation to USB...")
                    #set VFOA to USB mode
                    s.sendall(b"M USB 3000\n")
                    time.sleep(0.2)
                elif (self.my_satellite.downmode == "DATA-USB" or self.my_satellite.downmode == "USB-D"):
                    #set VFOA to Data USB mode
                    s.sendall(b"M PKTUSB 3000\n")
                    time.sleep(0.2)     
                elif self.my_satellite.downmode == "CW":
                    INTERACTIVE = True
                    #set VFOA to CW mode
                    s.sendall(b"M CW 3000\n")
                    time.sleep(0.2)
                else:
                    print("*** Downlink mode not implemented yet: {bad}".format(bad=self.my_satellite.downmode))
                    sys.exit()
                
                if OPMODE == False:
                    F_string = "x\n"
                    s.send(bytes(F_string, 'ascii'))
                    time.sleep(0.2)
                    data = s.recv(1024)
                    curr_mode = str(data)
                    print("Current mode VFO-B: ({a})".format(a=curr_mode))

                    s.sendall(b"V VFOB\n")
                    time.sleep(0.2) 
                    if self.my_satellite.upmode == "FM":
                        #set VFOB to FM mode
                        s.sendall(b"X FM 15000\n")
                        time.sleep(0.2)
                    elif self.my_satellite.upmode == "FMN":
                        s.sendall(b"X WFM 15000\n")
                        time.sleep(0.2)
                    elif self.my_satellite.upmode == "LSB":
                        print("Set VFO B modulation to LSB...")
                        #set VFOB to LSB mode
                        s.sendall(b"X LSB 3000\n")
                        time.sleep(0.2)
                    elif (self.my_satellite.upmode == "DATA-USB" or self.my_satellite.upmode == "USB-D"):
                        #set VFOB to USB mode
                        s.sendall(b"X PKTUSB 2400\n")
                        time.sleep(0.2)     
                    elif self.my_satellite.upmode == "DATA-LSB":
                        #set VFOB to LSB mode
                        s.sendall(b"X PKTLSB 2400\n")
                        time.sleep(0.2)    
                    elif self.my_satellite.upmode == "CW":
                        #set VFOB to CW mode
                        s.sendall(b"X CW 3000\n")
                        time.sleep(0.2)
                    else:
                        print("*** Uplink mode not implemented yet: {bad}".format(bad=self.my_satellite.upmode))
                        sys.exit()
                else:
                    with socketcontext(socket.AF_INET, socket.SOCK_STREAM) as s2:
                        s2.connect((ADDRESS, PORT))
                        
                        F_string = "m\n"
                        s2.send(bytes(F_string, 'ascii'))
                        time.sleep(0.2)
                        data = s2.recv(1024)
                        curr_mode = str(data)
                        print("Current mode VFO-A: ({a})".format(a=curr_mode))
                        
                        s2.sendall(b"V VFOA\n")
                        time.sleep(0.2) 
                        if self.my_satellite.downmode == "FM":
                            #set VFOA to FM mode
                            s2.sendall(b"M FM 15000\n")
                            time.sleep(0.2)
                        elif self.my_satellite.downmode == "FMN":
                            #set VFOA to WFM mode
                            s2.sendall(b"M WFM 15000\n")
                            time.sleep(0.2)
                        elif self.my_satellite.downmode ==  "USB":
                            INTERACTIVE = True
                            print("Set VFO A modulation to USB...")
                            #set VFOA to USB mode
                            s2.sendall(b"M USB 3000\n")
                            time.sleep(0.2)
                        elif (self.my_satellite.downmode == "DATA-USB" or self.my_satellite.downmode == "USB-D"):
                            #set VFOA to Data USB mode
                            s2.sendall(b"M PKTUSB 3000\n")
                            time.sleep(0.2)     
                        elif self.my_satellite.downmode == "CW":
                            INTERACTIVE = True
                            #set VFOA to CW mode
                            s2.sendall(b"M CW 3000\n")
                            time.sleep(0.2)
                        else:
                            print("*** Downlink mode not implemented yet: {bad}".format(bad=self.my_satellite.downmode))
                            sys.exit()

                print("All config done, starting doppler...")
                s.sendall(b"V VFOA\n")

                rx_doppler = F0
                tx_doppler = I0

                while SEMAPHORE == True:
                    date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                    myloc.date = ephem.Date(date_val)

                    if INTERACTIVE == True:
                        F_string = "f\n"
                        s.send(bytes(F_string, 'ascii'))
                        time.sleep(0.2)
                        data = s.recv(1024)
                        user_Freq = float(str(data).split('\\n')[0].replace("b\'",'').replace('RPRT',''))

                        if user_Freq > 0:
                            if abs(user_Freq - self.my_satellite.F) > 100:
                                if user_Freq > self.my_satellite.F:
                                    delta_F = user_Freq - self.my_satellite.F
                                    if self.my_satellite.mode == "REV":
                                        I0 -= delta_F
                                        F0 += delta_F
                                    else:
                                        I0 += delta_F
                                        F0 += delta_F
                                else:
                                    delta_F = self.my_satellite.F - user_Freq
                                    if self.my_satellite.mode == "REV":
                                        I0 += delta_F
                                        F0 -= delta_F
                                    else:
                                        I0 -= delta_F
                                        F0 -= delta_F
                    if self.my_satellite.rig_satmode == 0 and RADIO == "910":
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata),-1)
                        if new_rx_doppler != rx_doppler:
                            rx_doppler = new_rx_doppler
                            F_string = "F Main {the_rx_doppler:.0f}\n".format(the_rx_doppler=rx_doppler)  
                            s.send(bytes(F_string, 'ascii'))
                            self.my_satellite.F = rx_doppler
                    
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata),-1)
                        if new_tx_doppler != tx_doppler:
                            tx_doppler = new_tx_doppler
                            I_string = "I Sub{the_tx_doppler:.0f}\n".format(the_tx_doppler=tx_doppler)
                            if OPMODE == False:
                                s.send(bytes(I_string, 'ascii'))
                            else:
                                F2_string = "F Main{the_tx_doppler:.0f}\n".format(the_tx_doppler=tx_doppler)
                                s2.send(bytes(F2_string, 'ascii'))
                            self.my_satellite.I = tx_doppler
                    else:
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata),-1)
                        if new_rx_doppler != rx_doppler:
                            rx_doppler = new_rx_doppler
                            F_string = "F {the_rx_doppler:.0f}\n".format(the_rx_doppler=rx_doppler)  
                            s.send(bytes(F_string, 'ascii'))
                            self.my_satellite.F = rx_doppler
                    
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata),-1)
                        if new_tx_doppler != tx_doppler:
                            tx_doppler = new_tx_doppler
                            I_string = "I {the_tx_doppler:.0f}\n".format(the_tx_doppler=tx_doppler)
                            if OPMODE == False:
                                s.send(bytes(I_string, 'ascii'))
                            else:
                                F2_string = "F {the_tx_doppler:.0f}\n".format(the_tx_doppler=tx_doppler)
                                s2.send(bytes(F2_string, 'ascii'))
                            self.my_satellite.I = tx_doppler
                            
                    time.sleep(1)

        except socket.error:
            print("Failed to connect to Rigctld on {addr}:{port}.".format(addr=ADDRESS,port=PORT))
            sys.exit()
    
    def recurring_timer(self):
        self.rxfreq.setText(str(float(self.my_satellite.F)))
        self.rxfreq_onsat.setText(str(F0))
        self.txfreq.setText(str(float(self.my_satellite.I)))
        self.txfreq_onsat.setText(str(I0))

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
window.show()
app.exec()

# Autor:
#   Original from K8DP Doug Papay (v0.1)
#
#   Adapted v0.3 by EA4HCF Pedro Cabrera
#
#   v0.4 and beyond: Extended, partly rewritten and adapted from hamlib to direct radio control by DL3JOP Joshua Petry

### Mandatory imports
import ephem
import socket
import sys
import math
import time
import re
import urllib.request
import traceback
from lib import icom
import os
import numpy as np
import threading
from time import gmtime, strftime
from datetime import datetime, timedelta, timezone
from configparser import ConfigParser
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtCore import Qt, Signal, Slot, QObject, QMetaObject, Q_ARG, QThreadPool
from qt_material import apply_stylesheet
import logging
from serial.tools import list_ports
from lib.pass_recorder import PassRecorder
import sounddevice as sd
from lib import rotator
from lib.rotator_optimizer import RotatorOptimizer
from lib.sat_utils import *
from lib.logbook_connector import *
import pynmea2
import serial
from lib.gps_reader import GPSReader

# Set logging level back to WARNING
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler("qtrigdoppler.log", mode='w')
    ]
)

### Read config and import additional libraries if needed
# parsing config file
try:
    with open('config.ini') as f:
        f.close()
        configur = ConfigParser()
        configur.read('config.ini')
except IOError:
    logging.critical("Failed to find configuration file!")
    sys.exit()

# Set environment variables
LATITUDE = configur.get('qth','latitude', fallback=0.0)
LONGITUDE = configur.get('qth','longitude', fallback=0.0)
ALTITUDE = configur.getfloat('qth','altitude', fallback=0.0)
STEP_RX = configur.getint('qth','step_rx', fallback=1)
MAX_OFFSET_RX = configur.getint('qth','max_offset_rx',fallback=5000)
TLEFILE = configur.get('satellite','tle_file')
TLEURL = configur.get('satellite','tle_url')
DOPPLER_THRES_FM = configur.get('satellite', 'doppler_threshold_fm',fallback=200)
DOPPLER_THRES_LINEAR = configur.get('satellite', 'doppler_threshold_linear',fallback=20)
SQFILE = configur.get('satellite','sqffile')
RADIO = configur.get('icom','radio')
CVIADDR = configur.get('icom','cviaddress')
RIG_SERIAL_PORT = configur.get('icom', 'serialport')
RIG_TYPE = configur.get('icom', 'rig_type')
LAST_TLE_UPDATE = configur.get('misc', 'last_tle_update')
TLE_UPDATE_INTERVAL = configur.get('misc', 'tle_update_interval')

# Rotator config
ROTATOR_ENABLED = configur.getboolean('rotator', 'enabled', fallback=False)
ROTATOR_SERIAL_PORT = configur.get('rotator', 'serial_port', fallback='COM4')
ROTATOR_BAUDRATE = configur.getint('rotator', 'baudrate', fallback=4800)
ROTATOR_AZ_PARK = configur.getint('rotator', 'az_park', fallback=0)
ROTATOR_EL_PARK = configur.getint('rotator', 'el_park', fallback=0)
ROTATOR_AZ_MIN = configur.getint('rotator', 'az_min', fallback=0)
ROTATOR_AZ_MAX = configur.getint('rotator', 'az_max', fallback=450)
ROTATOR_EL_MIN = configur.getint('rotator', 'el_min', fallback=0)
ROTATOR_EL_MAX = configur.getint('rotator', 'el_max', fallback=180)
ROTATOR_MIN_ELEVATION = configur.getint('rotator', 'min_elevation', fallback=5)
ROTATOR_POSITION_POLL_INTERVAL = configur.getfloat('rotator', 'position_poll_interval', fallback=5.0)

# Cloudlog config
CLOUDLOG_API_KEY = configur.get('Cloudlog', 'api_key', fallback=None)
CLOUDLOG_URL = configur.get('Cloudlog', 'url', fallback=None)
CLOUDLOG_ENABLED = configur.getboolean('Cloudlog', 'enabled', fallback=False)

# Passrecoder config
if configur.has_section('passrecording') and configur.getboolean('passrecording', 'enabled'):
    PASS_RECORDER_ENABLED = True
else:
    PASS_RECORDER_ENABLED = False

# Webapi config
if configur.has_section('web_api') and configur.getboolean('web_api', 'enabled'):
    WEBAPI_ENABLED = True
else:
    WEBAPI_ENABLED = False
if configur.has_section('web_api') and configur.getboolean('web_api', 'debug'):
    WEBAPI_DEBUG_ENABLED = True
else:
    WEBAPI_DEBUG_ENABLED = False
WEBAPI_PORT = configur.getint('web_api', 'port', fallback=5000)
    
if configur.get('icom', 'fullmode') == "True":
    OPMODE = True
elif configur.get('icom', 'fullmode') == "False":
    OPMODE = False
if configur.get('misc', 'display_map') == "True":
    DISPLAY_MAP = True
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    import matplotlib.pyplot as plt
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    from pyproj import Geod
elif configur.get('misc', 'display_map') == "False":
    DISPLAY_MAP = False

# Import the remote client if section exists
REMOTE_ENABLED = False
if configur.has_section('remote_server') and configur.getboolean('remote_server', 'enable'):
    from lib import remote_client
    REMOTE_ENABLED = True

if WEBAPI_ENABLED or REMOTE_ENABLED:
    from lib import web_api  # Import the web API module
    from lib import web_api_proxy

### Global constants
subtone_list = ["None", "67 Hz", "71.9 Hz", "74.4 Hz", "141.3 Hz"]
if DISPLAY_MAP:
    GEOD = Geod(ellps="WGS84")

#i = 0
useroffsets = []
for (each_key, each_val) in configur.items('offset_profiles'):
    # Format SATNAME,TRANSPONDER,RXoffset,TXoffset
    parts = each_val.split(',')
    useroffsets += [parts]
    #i+=1

# radio frequencies
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
RX_TPX_ONLY = False
RIG_CONNECTED = False
if configur['icom']['radio'] == '9700':
    icomTrx = icom.icom(RIG_SERIAL_PORT, '19200', 96)
elif configur['icom']['radio'] == '910':
    icomTrx = icom.icom(RIG_SERIAL_PORT, '19200', 96)
RIG_CONNECTED = icomTrx.is_connected()    

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
    tle_age = "-1"
    rig_satmode = 0
    F_RIG = 0.0
    I_RIG = 0.0
    
if DISPLAY_MAP:
    class SatMapCanvas(FigureCanvas):
        def __init__(self, lat, lon, alt_km):
            self.fig = plt.figure()
            self.fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
            super().__init__(self.fig)
            self.lat = lat
            self.lon = lon
            self.alt_km = alt_km
            self.ax = self.fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())
            self.ax.clear()
            self.ax.set_global()
            self.ax.stock_img()
            self.ax.coastlines()
            self.ax.add_feature(cfeature.BORDERS, linestyle=':')
            self.ax.set_aspect('auto')

    
        def draw_map(self):
            for l in self.ax.get_lines():
                l.remove()
    
            # Generate geodesic footprint
            azimuths = np.linspace(0, 360, 361)
            radius_m = footprint_radius_km(self.alt_km) * 1000
            lons, lats, _ = GEOD.fwd(
                np.full(azimuths.shape, self.lon),
                np.full(azimuths.shape, self.lat),
                azimuths,
                np.full(azimuths.shape, radius_m)
            )
    
            # Normalize longitudes
            lons = ((lons + 180) % 360) - 180
            lats = np.clip(lats, -90, 90)
    
            # Split into segments to handle wraparound
            segments = []
            seg_lon = [lons[0]]
            seg_lat = [lats[0]]
            for i in range(1, len(lons)):
                if abs(lons[i] - lons[i-1]) > 180 or abs(lats[i] - lats[i-1]) > 90:
                    segments.append((seg_lon, seg_lat))
                    seg_lon = []
                    seg_lat = []
                seg_lon.append(lons[i])
                seg_lat.append(lats[i])
            if seg_lon:
                segments.append((seg_lon, seg_lat))
    
            # Plot all segments
            for seg_lon, seg_lat in segments:
                self.ax.plot(seg_lon, seg_lat, 'b--', transform=ccrs.PlateCarree(), linewidth=1)
            
            # Plot satellite subpoint
            self.ax.plot(float(self.lon), float(self.lat), 'ro', markersize=6, label="Subpoint", transform=ccrs.PlateCarree())
    
            self.draw()


class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        
        ## Pyinstaller Splashscreen handler
        if '_PYI_SPLASH_IPC' in os.environ:
            import pyi_splash
            pyi_splash.update_text('UI Loaded ...')
            pyi_splash.close()
        
        ### All of this should be moved to a global settings struct ....
        global LATITUDE
        global LONGITUDE
        global ALTITUDE
        global STEP_RX
        global MAX_OFFSET_RX
        global DOPPLER_THRES_FM
        global DOPPLER_THRES_LINEAR

        # satellite
        global TLEFILE
        global TLEURL
        global SQFILE

        # Radio
        global RADIO        
        global CVIADDR
        global OPMODE

        self.counter = 0
        self.my_satellite = Satellite()
        
        if WEBAPI_ENABLED:
            # Register this window with the web API
            web_api.register_window(self)
        
            # Start web API server in a separate thread if enabled
            self.web_api_thread = threading.Thread(target=web_api.run_socketio, daemon=True)
            
            # Set thread name for easier identification in diagnostics
            self.web_api_thread.name = "WebSocketThread"
            
            # Start with lower priority if possible
            self.web_api_thread.start()
            
            # Attempt to set thread priority lower (platform-specific)
            try:
                import platform
                if platform.system() == 'Windows':
                    import ctypes
                    # Get thread ID for the current thread
                    thread_id = self.web_api_thread.ident
                    if thread_id:
                        # THREAD_PRIORITY_BELOW_NORMAL = -1
                        handle = ctypes.windll.kernel32.OpenThread(0x0200, False, thread_id)
                        if handle:
                            ctypes.windll.kernel32.SetThreadPriority(handle, -1)
                            ctypes.windll.kernel32.CloseHandle(handle)
                            logging.debug("Set web_api_thread to below normal priority")
            except Exception as e:
                logging.warning(f"Failed to adjust web_api_thread priority: {e}")
            
            logging.info(f"Web API server started on port {configur.get('web_api', 'port', fallback='5000')}")
        
            # Set up the web API proxy for thread-safe GUI/timer operations
            self.web_api_proxy = web_api_proxy.WebApiGuiProxy()
            self.web_api_proxy.select_satellite.connect(self.slot_select_satellite)
            self.web_api_proxy.select_transponder.connect(self.slot_select_transponder)
            self.web_api_proxy.set_subtone.connect(self.slot_set_subtone)
            self.web_api_proxy.set_rx_offset.connect(self.slot_set_rx_offset)
            self.web_api_proxy.start_tracking.connect(self.init_worker)
            self.web_api_proxy.stop_tracking.connect(self.the_stop_button_was_clicked)
        
        # If remote server is enabled, register with remote client
        if REMOTE_ENABLED:
            # Make sure we have a web API proxy for signals even if local web API is disabled
            if not WEBAPI_ENABLED:
                self.web_api_proxy = web_api_proxy.WebApiGuiProxy()
                self.web_api_proxy.select_satellite.connect(self.slot_select_satellite)
                self.web_api_proxy.select_transponder.connect(self.slot_select_transponder)
                self.web_api_proxy.set_subtone.connect(self.slot_set_subtone)
                self.web_api_proxy.set_rx_offset.connect(self.slot_set_rx_offset)
                self.web_api_proxy.start_tracking.connect(self.init_worker)
                self.web_api_proxy.stop_tracking.connect(self.the_stop_button_was_clicked)
            
            # Register with remote client
            remote_client.register_window(self)
            logging.info(f"Remote client registered with server: {configur.get('remote_server', 'url', fallback='http://localhost:5001')}")
            
        # Rotator integration
        self.ROTATOR_ENABLED = ROTATOR_ENABLED
        self.rotator = None
        self.rotator_thread = None
        self.rotator_error = None
        self.rotator_optimizer = None
        self.pass_optimization = None  # Store current pass optimization
        if ROTATOR_ENABLED:
            try:
                self.rotator = rotator.YaesuRotator(
                    ROTATOR_SERIAL_PORT,
                    baudrate=ROTATOR_BAUDRATE,
                    az_min=ROTATOR_AZ_MIN,
                    az_max=ROTATOR_AZ_MAX,
                    el_min=ROTATOR_EL_MIN,
                    el_max=ROTATOR_EL_MAX
                )
                # Initialize rotator optimizer
                self.rotator_optimizer = RotatorOptimizer(
                    az_min=ROTATOR_AZ_MIN,
                    az_max=ROTATOR_AZ_MAX,
                    min_elevation=ROTATOR_MIN_ELEVATION
                )
                logging.info(f"Rotator and optimizer initialized")
            except Exception as e:
                self.rotator_error = f"Rotator init failed: {e}"
                logging.error(self.rotator_error)
                self.rotator = None


        
        self.setWindowTitle("QTRigDoppler")
        #self.setGeometry(3840*2, 0, 718, 425)
        
        ### Overview Page

        overview_pagelayout = QVBoxLayout()
        
        control_container = QWidget()
        map_container = QWidget()
        log_container = QWidget()

        control_layout = QHBoxLayout(control_container)
        map_layout = QHBoxLayout(map_container)
        log_layout = QHBoxLayout(log_container)

        overview_pagelayout.addWidget(control_container,stretch=2)
        if DISPLAY_MAP:
            overview_pagelayout.addWidget(map_container, stretch=1)
        overview_pagelayout.addWidget(log_container, stretch=1)
        
        labels_layout = QVBoxLayout()
        combo_layout = QVBoxLayout()
        button_layout = QVBoxLayout()

        combo_layout.setAlignment(Qt.AlignVCenter)
        control_layout.addLayout(combo_layout, stretch=1)
        control_layout.addLayout(labels_layout, stretch=1)
        control_layout.addLayout(button_layout, stretch=1);

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
                # Skip comment lines
                if line.strip().startswith(';'):
                    continue
                    
                if ',' in line:
                    newitem = str(line.split(",")[0].strip())
                    if newitem:
                        satlist += [newitem]
        satlist = list(dict.fromkeys(satlist))  # Deduplicate

        def sat_sort_key(name):
            match = re.match(r"([A-Za-z]+)-(\d+)", name)
            if match:
                prefix, num = match.groups()
                return (prefix, int(num))
            return (name, 0)
        satlist.sort(key=sat_sort_key)
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
        
        offset_button_layout = QHBoxLayout()
        labels = ["+1000", "+100", "+10", "-10", "-100", "-1000"]
        self.offset_buttons = [QPushButton(label) for label in labels]
        
        for button in self.offset_buttons:
            button.setStyleSheet("font-size: 8pt;")
            button.clicked.connect(lambda _, b=button: self.rxoffset_button_pushed(b.text()))
            offset_button_layout.addWidget(button)

        combo_layout.addLayout(offset_button_layout)

        myFont=QFont()
        myFont.setBold(True)
        
        groupbox_downlink = QGroupBox()
        groupbox_downlink.setStyleSheet("QGroupBox{padding-top:5px;padding-bottom:5px; margin-top:0px}")
        labels_layout.addWidget(groupbox_downlink)
        vbox_downlink = QVBoxLayout()
        groupbox_downlink.setLayout(vbox_downlink)
        
        rx_labels_sat_layout = QHBoxLayout()
        # 1x Label: RX freq Satellite
        self.rxfreqsat_lbl = QLabel("RX @ Sat:")
        self.rxfreqsat_lbl.setStyleSheet("QLabel{font-size: 12pt;}")
        self.rxfreqsat_lbl.setFont(myFont)
        rx_labels_sat_layout.addWidget(self.rxfreqsat_lbl)

        self.rxfreq_onsat = QLabel("435,500,000.0 Hz")
        self.rxfreq_onsat.setStyleSheet("QLabel{font-size: 12pt;}")
        self.rxfreq_onsat.setFont(myFont)
        rx_labels_sat_layout.addWidget(self.rxfreq_onsat)
        vbox_downlink.addLayout(rx_labels_sat_layout)
        
        rx_labels_radio_layout = QHBoxLayout()
        # 1x Label: RX freq
        self.rxfreqtitle = QLabel("RX @ Radio:")
        rx_labels_radio_layout.addWidget(self.rxfreqtitle)

        self.rxfreq = QLabel("435,500,000.0 Hz")
        rx_labels_radio_layout.addWidget(self.rxfreq)
        
        vbox_downlink.addLayout(rx_labels_radio_layout)

        
        # 1x Label: RX Doppler Satellite
        rx_doppler_freq_layout = QHBoxLayout()
        self.rxdopplersat_lbl = QLabel("Doppler:")
        rx_doppler_freq_layout.addWidget(self.rxdopplersat_lbl)

        self.rxdoppler_val = QLabel("0.0 Hz")
        rx_doppler_freq_layout.addWidget(self.rxdoppler_val)
        
        vbox_downlink.addLayout(rx_doppler_freq_layout)
        
        # 1x Label: RX Doppler RateSatellite
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

        tx_labels_sat_layout = QHBoxLayout()
        # 1x Label: TX freq Satellite
        self.txfreqsat_lbl = QLabel("TX @ Sat:")
        self.txfreqsat_lbl.setStyleSheet("QLabel{font-size: 12pt;}")
        self.txfreqsat_lbl.setFont(myFont)
        tx_labels_sat_layout.addWidget(self.txfreqsat_lbl)

        self.txfreq_onsat = QLabel("145,900,000.0 Hz")
        self.txfreq_onsat.setStyleSheet("QLabel{font-size: 12pt;}")
        self.txfreq_onsat.setFont(myFont)
        tx_labels_sat_layout.addWidget(self.txfreq_onsat)
        vbox_uplink.addLayout(tx_labels_sat_layout)
        
        tx_labels_radio_layout = QHBoxLayout()
        # 1x Label: TX freq
        self.txfreqtitle = QLabel("TX @ Radio:")
        tx_labels_radio_layout.addWidget(self.txfreqtitle)

        self.txfreq = QLabel("145,900,000.0 Hz")
        tx_labels_radio_layout.addWidget(self.txfreq)
        
        vbox_uplink.addLayout(tx_labels_radio_layout)
        
        
        # 1x Label: TX Doppler Satellite
        tx_doppler_freq_layout = QHBoxLayout()
        self.txdopplersat_lbl = QLabel("Doppler:")
        tx_doppler_freq_layout.addWidget(self.txdopplersat_lbl)

        self.txdoppler_val = QLabel("0.0 Hz")
        tx_doppler_freq_layout.addWidget(self.txdoppler_val)
        
        vbox_uplink.addLayout(tx_doppler_freq_layout)
        
        # 1x Label: TX Doppler RateSatellite
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
        self.syncbutton = QPushButton("Memory to VFO")
        self.syncbutton.clicked.connect(self.the_sync_button_was_clicked)
        button_layout.addWidget(self.syncbutton)
        self.syncbutton.setEnabled(False)
        
        # Sync to SQF freq
        self.offsetstorebutton = QPushButton("Store Offset")
        self.offsetstorebutton.clicked.connect(self.save_settings)
        button_layout.addWidget(self.offsetstorebutton)
        self.offsetstorebutton.setEnabled(False)
        
        # Rotator buttons
        if ROTATOR_ENABLED:
            # Park Button
            self.park_rotator_button = QPushButton("Park Rotators")
            self.park_rotator_button.clicked.connect(self.park_rotators)
            button_layout.addWidget(self.park_rotator_button)
            # Stop Button
            self.stop_rotator_button = QPushButton("Stop Rotation")
            self.stop_rotator_button.clicked.connect(self.stop_rotators)
            button_layout.addWidget(self.stop_rotator_button)
            # Add refresh button
            self.refresh_rotator_button = QPushButton("Refresh Rotator Position")
            self.refresh_rotator_button.clicked.connect(self.update_rotator_position)
            button_layout.addWidget(self.refresh_rotator_button)

        # 1x QPushButton (Exit)
        self.Exitbutton = QPushButton("Exit")
        self.Exitbutton.setCheckable(True)
        self.Exitbutton.clicked.connect(self.the_exit_button_was_clicked)
        button_layout.addWidget(self.Exitbutton)

        # Output log
        
        self.log_sat_status = QGroupBox()
        self.log_sat_status.setStyleSheet("QGroupBox{padding-top:0px;padding-bottom:0px; margin-top:0px;font-size: 16pt;} QLabel{font-size: 16pt;}")
        log_sat_status_layout = QGridLayout()
        
        self.log_sat_status_ele_lbl = QLabel("🛰 Elevation:")
        log_sat_status_layout.addWidget(self.log_sat_status_ele_lbl, 0, 0,alignment=Qt.AlignCenter)

        self.log_sat_status_ele_val = QLabel("0.0 °")
        log_sat_status_layout.addWidget(self.log_sat_status_ele_val, 0, 1,alignment=Qt.AlignCenter)
        
        self.log_sat_status_azi_lbl = QLabel("🛰 Azimuth:")
        log_sat_status_layout.addWidget(self.log_sat_status_azi_lbl, 1, 0,alignment=Qt.AlignCenter)

        self.log_sat_status_azi_val = QLabel("0.0 °")
        log_sat_status_layout.addWidget(self.log_sat_status_azi_val, 1, 1,alignment=Qt.AlignCenter)
        
        self.log_sat_status_height_lbl = QLabel("🛰 Height:")
        log_sat_status_layout.addWidget(self.log_sat_status_height_lbl, 0, 3,alignment=Qt.AlignCenter)

        self.log_sat_status_height_val = QLabel("0.0 m")
        log_sat_status_layout.addWidget(self.log_sat_status_height_val, 0, 4,alignment=Qt.AlignCenter)
        
        self.log_sat_status_illuminated_lbl = QLabel("🛰 Visibility:")
        log_sat_status_layout.addWidget(self.log_sat_status_illuminated_lbl, 1, 3,alignment=Qt.AlignCenter)

        self.log_sat_status_illumintated_val = QLabel("n/a")
        log_sat_status_layout.addWidget(self.log_sat_status_illumintated_val, 1, 4,alignment=Qt.AlignCenter)
        
        self.status_layout_vline_right = QFrame()
        self.status_layout_vline_right.setFrameShape(QFrame.VLine)
        self.status_layout_vline_right.setFrameShadow(QFrame.Plain)
        self.status_layout_vline_right.setStyleSheet("background-color: #4f5b62;border: none;")
        self.status_layout_vline_right.setFixedWidth(2)
        log_sat_status_layout.addWidget(self.status_layout_vline_right, 0, 2, 2, 1)
        
        self.log_sat_status.setLayout(log_sat_status_layout)
        log_layout.addWidget(self.log_sat_status, stretch=2)
        
        self.log_rig_status = QGroupBox()
        self.log_rig_status.setStyleSheet("QGroupBox{padding-top:2px;padding-bottom:2px; margin-top:0px;font-size: 12pt;} QLabel{font-size: 12pt;}")
        log_rig_status_layout = QGridLayout()
        
        self.log_rig_state_lbl = QLabel("Radio:")
        log_rig_status_layout.addWidget(self.log_rig_state_lbl, 0, 0,alignment=Qt.AlignCenter)

        self.log_rig_state_val = QLabel("✘")
        self.log_rig_state_val.setStyleSheet('color: red')
        log_rig_status_layout.addWidget(self.log_rig_state_val, 0, 1,alignment=Qt.AlignCenter)
        
        self.log_tle_state_lbl = QLabel("TLE age:")
        log_rig_status_layout.addWidget(self.log_tle_state_lbl, 0, 3,alignment=Qt.AlignCenter)

        self.log_tle_state_val = QLabel("{0} day(s)".format(self.my_satellite.tle_age))
        log_rig_status_layout.addWidget(self.log_tle_state_val, 0, 4,alignment=Qt.AlignCenter)
        
        self.log_sat_event_val = QLabel("events n/a")
        log_rig_status_layout.addWidget(self.log_sat_event_val, 1, 3, 1,2,alignment=Qt.AlignCenter)
        
        self.log_time_lbl = QLabel("UTC:")
        log_rig_status_layout.addWidget(self.log_time_lbl, 1, 0,alignment=Qt.AlignCenter)

        self.log_time_val = QLabel(datetime.now(timezone.utc).strftime('%H:%M:%S')+"z")
        log_rig_status_layout.addWidget(self.log_time_val, 1, 1,alignment=Qt.AlignCenter)
        
        if PASS_RECORDER_ENABLED:
            # --- Pass Recording Status Label ---
            self.recording_text_label = QLabel("Recording:")
            self.recording_status_label = QLabel("✘")
            self.recording_status_label.setStyleSheet("QLabel{font-size: 12pt; font-weight: bold; color: red}")
            log_rig_status_layout.addWidget(self.recording_text_label,2,0)
            log_rig_status_layout.addWidget(self.recording_status_label,2,1)
        
        self.log_layout_vline_right = QFrame()
        self.log_layout_vline_right.setFrameShape(QFrame.VLine)
        self.log_layout_vline_right.setFrameShadow(QFrame.Plain)
        self.log_layout_vline_right.setStyleSheet("background-color: #4f5b62;border: none;")
        self.log_layout_vline_right.setFixedWidth(2)
        if PASS_RECORDER_ENABLED:
            log_rig_status_layout.addWidget(self.log_layout_vline_right, 0, 2, 3, 1)
        else:
            log_rig_status_layout.addWidget(self.log_layout_vline_right, 0, 2, 2, 1)
        
        self.log_rig_status.setLayout(log_rig_status_layout)
        log_layout.addWidget(self.log_rig_status, stretch=1)
        
        if ROTATOR_ENABLED:
            # Add rotator position labels in a styled group box
            self.rotator_status_box = QGroupBox("")
            self.rotator_status_box.setStyleSheet("QGroupBox{padding-top:2px;padding-bottom:2px; margin-top:0px;font-size: 12pt;} QLabel{font-size: 12pt;}")
            rotator_status_layout = QGridLayout()
            self.rotator_az_label = QLabel("📡 Azimuth:")
            self.rotator_el_label = QLabel("📡 Elevation:")
            self.rotator_az_val = QLabel("0.0°")
            self.rotator_el_val = QLabel("0.0°")
            self.rotator_optimization_label = QLabel("🛰 Route:")
            self.rotator_optimization_val = QLabel("Parked")
            rotator_status_layout.addWidget(self.rotator_el_label, 0, 0)
            rotator_status_layout.addWidget(self.rotator_az_label, 1, 0)
            rotator_status_layout.addWidget(self.rotator_optimization_label, 2, 0)
            rotator_status_layout.addWidget(self.rotator_el_val, 0, 1)
            rotator_status_layout.addWidget(self.rotator_az_val, 1, 1)
            rotator_status_layout.addWidget(self.rotator_optimization_val, 2, 1)
            self.rotator_status_box.setLayout(rotator_status_layout)
            log_layout.addWidget(self.rotator_status_box, stretch=1)
            
            #Read and display position at startup
            self.update_rotator_position()
            #If rotator failed to init, show error
            if self.rotator_error:
                self.rotator_az_val.setText("error")
                self.rotator_el_val.setText("error")
            self.start_rotator_position_worker()
        
        ## Map layout
        if DISPLAY_MAP:
            self.mapbox = QGroupBox()
            self.mapbox.setStyleSheet("QGroupBox{padding-top:2px;padding-bottom:2px; margin-top:0px;font-size: 14pt;} QLabel{font-size: 14pt;}")
            mapbox_layout = QHBoxLayout()
            self.mapbox.setLayout(mapbox_layout)
            map_layout.addWidget(self.mapbox)
            self.map_canvas = SatMapCanvas(-60, -80, 1)
            mapbox_layout.addWidget(self.map_canvas)
        
        
        
        ### Settings Tab
        settings_value_layout = QHBoxLayout()
        
        
        # QTH Tab
        self.settings_qth_box = QGroupBox("QTH")
        self.settings_qth_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        settings_value_layout.addWidget(self.settings_qth_box)
        
        # Radio Tab (scrollable for smaller screens)
        self.settings_radio_box = QGroupBox("Radio")
        self.settings_radio_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        settings_value_layout.addWidget(self.settings_radio_box)
        
        # Files Tab
        self.settings_file_box = QGroupBox("Files")
        self.settings_file_box.setStyleSheet("QGroupBox{padding-top:1px;padding-bottom:5px; margin-top:5px}")
        settings_value_layout.addWidget(self.settings_file_box)
        
        
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
        self.qth_settings_alt_lbl = QLabel("QTH Altitude (meters):")
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
        
        # Radio config --> EU/Tone or US/TQSL
        self.radio_country_config_lbl = QLabel("Radio type:")
        radio_settings_layout.addWidget(self.radio_country_config_lbl, 1, 0)
        self.radio_country_config_eu_button = QRadioButton("EU/Tone")
        self.radio_country_config_us_button = QRadioButton("US/TSQL")
        self.radio_country_config_group = QButtonGroup()
        self.radio_country_config_group.addButton(self.radio_country_config_eu_button)
        self.radio_country_config_group.addButton(self.radio_country_config_us_button)
        radio_settings_layout.addWidget(self.radio_country_config_eu_button, 1, 1)
        radio_settings_layout.addWidget(self.radio_country_config_us_button, 1, 2)
        if RIG_TYPE == "EU":
            self.radio_country_config_eu_button.setChecked(1)
        elif RIG_TYPE == "US":
            self.radio_country_config_us_button.setChecked(1)
        
        # CI-V selector
        self.radicvi_lbl = QLabel("CVI address:")
        radio_settings_layout.addWidget(self.radicvi_lbl, 2, 0)
        self.radicvi = QLineEdit()
        self.radicvi.setMaxLength(2)
        self.radicvi.setText(CVIADDR)
        radio_settings_layout.addWidget(self.radicvi, 2, 1)
        
        self.rig_serialport_lbl = QLabel("Port:")
        radio_settings_layout.addWidget(self.rig_serialport_lbl, 3, 0)

        # Replace QLineEdit with QComboBox for COM port selection
        self.rig_serialport_val = QComboBox()
        available_ports = [port.device for port in list_ports.comports()]
        self.rig_serialport_val.addItems(available_ports)
        # Add the saved port if not in the list
        if str(RIG_SERIAL_PORT) not in available_ports:
            self.rig_serialport_val.addItem(str(RIG_SERIAL_PORT))
        self.rig_serialport_val.setCurrentText(str(RIG_SERIAL_PORT))
        radio_settings_layout.addWidget(self.rig_serialport_val, 3, 1)
        
        # 1x Label step RX
        self.qthsteprx_lbl = QLabel("Step (Hz) for RX offset:")
        radio_settings_layout.addWidget(self.qthsteprx_lbl, 4, 0)

        self.qthsteprx = QLineEdit()
        self.qthsteprx.setMaxLength(10)
        self.qthsteprx.setText(str(STEP_RX))
        radio_settings_layout.addWidget(self.qthsteprx, 4, 1)

        # 1x Label Max Offset RX
        self.qthmaxoffrx_lbl = QLabel("Max Offset (Hz) for RX:")
        radio_settings_layout.addWidget(self.qthmaxoffrx_lbl, 5, 0)

        self.qthmaxoffrx = QLineEdit()
        self.qthmaxoffrx.setMaxLength(6)
        self.qthmaxoffrx.setText(str(MAX_OFFSET_RX))
        radio_settings_layout.addWidget(self.qthmaxoffrx, 5, 1)

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
        
        self.UpdateTLEButton = QPushButton("Update TLE")
        self.UpdateTLEButton.clicked.connect(self.update_tle_file)
        files_settings_layout.addWidget(self.UpdateTLEButton, 3,0)
        self.UpdateTLEButton.setEnabled(True)
        
        self.tleupdate_stat_lbl = QLabel(LAST_TLE_UPDATE)
        files_settings_layout.addWidget(self.tleupdate_stat_lbl, 3, 1)
        
        self.settings_file_box.setLayout(files_settings_layout)
        
        # Settings store layout
        settings_store_layout = QVBoxLayout()
        
        self.SafeSettingsButton = QPushButton("Store Settings - location changes require restart")
        self.SafeSettingsButton.clicked.connect(self.save_settings)
        settings_store_layout.addWidget(self.SafeSettingsButton)
        self.SafeSettingsButton.setEnabled(True)
        
        
        # Glueing settinglayouts together
        settings_layout = QVBoxLayout()
        settings_layout.addLayout(settings_value_layout)
        settings_layout.addLayout(settings_store_layout)
        
        ### Advanced Settings Tab
        adv_settings_value_layout = QGridLayout()
        adv_settings_value_layout_first_column = QVBoxLayout()
        
        
        # --- Webapi ---
        self.adv_settings_webapi_box = QGroupBox("WebAPI")
        self.adv_settings_webapi_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        adv_settings_value_layout_first_column.addWidget(self.adv_settings_webapi_box)
        
        ## Enable
        webapi_settings_layout = QGridLayout()
        self.webapi_en_lbl = QLabel("Active:")
        webapi_settings_layout.addWidget(self.webapi_en_lbl, 0, 0)
        
        self.webapi_enable_button = QCheckBox()
        webapi_settings_layout.addWidget(self.webapi_enable_button, 0, 1)
        if WEBAPI_ENABLED == True:
            self.webapi_enable_button.setChecked(1)
        elif WEBAPI_ENABLED == False:
            self.webapi_enable_button.setChecked(0)
            
        self.webapi_en_lbl = QLabel("Debug:")
        webapi_settings_layout.addWidget(self.webapi_en_lbl, 1, 0)    
        self.webapi_debug_enable_button = QCheckBox()
        webapi_settings_layout.addWidget(self.webapi_debug_enable_button, 1, 1)
        if WEBAPI_DEBUG_ENABLED == True:
            self.webapi_debug_enable_button.setChecked(1)
        elif WEBAPI_DEBUG_ENABLED == False:
            self.webapi_debug_enable_button.setChecked(0)
            
        self.webapi_port_lbl = QLabel("Port:")
        webapi_settings_layout.addWidget(self.webapi_port_lbl, 2, 0)

        self.webapi_port_val = QLineEdit()
        self.webapi_port_val.setMaxLength(5)
        self.webapi_port_val.setText(str(WEBAPI_PORT))
        webapi_settings_layout.addWidget(self.webapi_port_val, 2, 1)
        
        self.adv_settings_webapi_box.setLayout(webapi_settings_layout)
        # --- End Webapi ---
        
        # --- Cloudlog/Wavelog ---
        self.adv_settings_log_box = QGroupBox("Logbook")
        self.adv_settings_log_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        adv_settings_value_layout_first_column.addWidget(self.adv_settings_log_box)
        
        ## Enable
        log_settings_layout = QGridLayout()
        self.log_en_lbl = QLabel("Active:")
        log_settings_layout.addWidget(self.log_en_lbl, 0, 0)
        
        self.log_enable_button = QCheckBox()
        log_settings_layout.addWidget(self.log_enable_button, 0, 1)
            
        self.log_url_lbl = QLabel("URL:")
        log_settings_layout.addWidget(self.log_url_lbl, 1, 0)

        self.log_url_val = QLineEdit()
        self.log_url_val.setMaxLength(100)
        self.log_url_val.setText(str("localhost"))
        log_settings_layout.addWidget(self.log_url_val, 1, 1)
        
        self.adv_settings_log_box.setLayout(log_settings_layout)
        # --- End Cloudlog/Wavelog ---
        
        # --- GPS QTH Settings UI ---
        self.gps_settings_box = QGroupBox("GPS QTH")
        self.gps_settings_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        gps_settings_layout = QGridLayout()
        # Enable checkbox
        self.gps_enable_checkbox = QCheckBox("Use GPS for QTH")
        gps_settings_layout.addWidget(self.gps_enable_checkbox, 0, 0, 1, 2)
        # Serial port dropdown
        self.gps_serialport_label = QLabel("GPS Serial Port:")
        gps_settings_layout.addWidget(self.gps_serialport_label, 1, 0)
        self.gps_serialport_val = QComboBox()
        gps_ports = [port.device for port in list_ports.comports()]
        self.gps_serialport_val.addItems(gps_ports)
        gps_settings_layout.addWidget(self.gps_serialport_val, 1, 1)
        # Status label
        self.gps_status_label = QLabel("GPS Status: Not connected")
        gps_settings_layout.addWidget(self.gps_status_label, 2, 0, 1, 2)
        # Lock button
        self.gps_lock_button = QPushButton("Lock Current Position")
        self.gps_lock_button.setEnabled(False)
        gps_settings_layout.addWidget(self.gps_lock_button, 3, 0, 1, 2)
        self.gps_settings_box.setLayout(gps_settings_layout)
        adv_settings_value_layout_first_column.addWidget(self.gps_settings_box)
        # --- End GPS QTH Settings UI ---
        adv_settings_value_layout.addLayout(adv_settings_value_layout_first_column,0,0)

        
        # Rotator
        self.adv_settings_rotator_box = QGroupBox("rotator")
        self.adv_settings_rotator_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        adv_settings_value_layout.addWidget(self.adv_settings_rotator_box, 0,1)
        
        self.rotator_settings_layout_scroller = QScrollArea()
        self.rotator_settings_layout_scroller_widget = QWidget()
        
        ## Enable
        rotator_settings_layout = QGridLayout()
        self.rotator_en_lbl = QLabel("Active:")
        rotator_settings_layout.addWidget(self.rotator_en_lbl, 0, 0)
        
        self.rotator_enable_button = QCheckBox()
        rotator_settings_layout.addWidget(self.rotator_enable_button, 0, 1)
        if ROTATOR_ENABLED == True:
            self.rotator_enable_button.setChecked(1)
        elif ROTATOR_ENABLED == False:
            self.rotator_enable_button.setChecked(0)
            
        self.rotator_serialport_lbl = QLabel("Port:")
        rotator_settings_layout.addWidget(self.rotator_serialport_lbl, 1, 0)

        # Replace QLineEdit with QComboBox for COM port selection
        self.rotator_serialport_val = QComboBox()
        available_ports = [port.device for port in list_ports.comports()]
        self.rotator_serialport_val.addItems(available_ports)
        # Add the saved port if not in the list
        if str(ROTATOR_SERIAL_PORT) not in available_ports:
            self.rotator_serialport_val.addItem(str(ROTATOR_SERIAL_PORT))
        self.rotator_serialport_val.setCurrentText(str(ROTATOR_SERIAL_PORT))
        rotator_settings_layout.addWidget(self.rotator_serialport_val, 1, 1)
        
        self.rotator_serialrate_lbl = QLabel("Baudrate:")
        rotator_settings_layout.addWidget(self.rotator_serialrate_lbl, 2, 0)

        self.rotator_serialrate_val = QLineEdit()
        self.rotator_serialrate_val.setMaxLength(6)
        self.rotator_serialrate_val.setText(str(ROTATOR_BAUDRATE))
        rotator_settings_layout.addWidget(self.rotator_serialrate_val, 2, 1)
        
        self.rotator_azpark_lbl = QLabel("Az Park:")
        rotator_settings_layout.addWidget(self.rotator_azpark_lbl, 3, 0)
        self.rotator_azpark_val = QLineEdit()
        self.rotator_azpark_val.setMaxLength(6)
        self.rotator_azpark_val.setText(str(ROTATOR_AZ_PARK))
        rotator_settings_layout.addWidget(self.rotator_azpark_val, 3, 1)
        
        self.rotator_elpark_lbl = QLabel("El Park:")
        rotator_settings_layout.addWidget(self.rotator_elpark_lbl, 4, 0)
        self.rotator_elpark_val = QLineEdit()
        self.rotator_elpark_val.setMaxLength(6)
        self.rotator_elpark_val.setText(str(ROTATOR_EL_PARK))
        rotator_settings_layout.addWidget(self.rotator_elpark_val, 4, 1)
        
        self.rotator_azmin_lbl = QLabel("Az Min:")
        rotator_settings_layout.addWidget(self.rotator_azmin_lbl, 5, 0)
        self.rotator_azmin_val = QLineEdit()
        self.rotator_azmin_val.setMaxLength(6)
        self.rotator_azmin_val.setText(str(ROTATOR_AZ_MIN))
        rotator_settings_layout.addWidget(self.rotator_azmin_val, 5, 1)
        
        self.rotator_azmax_lbl = QLabel("Az Max:")
        rotator_settings_layout.addWidget(self.rotator_azmax_lbl, 6, 0)
        self.rotator_azmax_val = QLineEdit()
        self.rotator_azmax_val.setMaxLength(6)
        self.rotator_azmax_val.setText(str(ROTATOR_AZ_MAX))
        rotator_settings_layout.addWidget(self.rotator_azmax_val, 6, 1)
        
        self.rotator_elmin_lbl = QLabel("El Min:")
        rotator_settings_layout.addWidget(self.rotator_elmin_lbl, 7, 0)
        self.rotator_elmin_val = QLineEdit()
        self.rotator_elmin_val.setMaxLength(6)
        self.rotator_elmin_val.setText(str(ROTATOR_EL_MIN))
        rotator_settings_layout.addWidget(self.rotator_elmin_val, 7, 1)
        
        self.rotator_elmax_lbl = QLabel("El Max:")
        rotator_settings_layout.addWidget(self.rotator_elmax_lbl, 8, 0)
        self.rotator_elmax_val = QLineEdit()
        self.rotator_elmax_val.setMaxLength(6)
        self.rotator_elmax_val.setText(str(ROTATOR_EL_MAX))
        rotator_settings_layout.addWidget(self.rotator_elmax_val, 8, 1)

        self.rotator_minelev_lbl = QLabel("Min Elevation:")
        rotator_settings_layout.addWidget(self.rotator_minelev_lbl, 9, 0)
        self.rotator_minelev_val = QLineEdit()
        self.rotator_minelev_val.setMaxLength(6)
        self.rotator_minelev_val.setText(str(ROTATOR_MIN_ELEVATION))
        rotator_settings_layout.addWidget(self.rotator_minelev_val, 9, 1)
        
        self.rotator_pollinterval_lbl = QLabel("Position Poll Interval (sec):")
        rotator_settings_layout.addWidget(self.rotator_pollinterval_lbl, 10, 0)
        self.rotator_pollinterval_val = QLineEdit()
        self.rotator_pollinterval_val.setMaxLength(6)
        self.rotator_pollinterval_val.setText(str(ROTATOR_POSITION_POLL_INTERVAL))
        rotator_settings_layout.addWidget(self.rotator_pollinterval_val, 10, 1)
        
        self.rotator_settings_layout_scroller.setLayout(rotator_settings_layout)
        self.rotator_settings_layout_scroller.setWidget(self.rotator_settings_layout_scroller_widget)
        self.rotator_settings_layout_scroller.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.rotator_settings_layout_scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rotator_settings_layout_scroller.setWidgetResizable(True)
        self.rotator_settings_layout_scroller_layout = QHBoxLayout()
        self.rotator_settings_layout_scroller_layout.addWidget(self.rotator_settings_layout_scroller)
            
        self.adv_settings_rotator_box.setLayout(self.rotator_settings_layout_scroller_layout)
        
        #Store button
        adv_settings_store_layout = QVBoxLayout()
        
        self.SafeADVSettingsButton = QPushButton("Store Settings - requires restart")
        self.SafeADVSettingsButton.clicked.connect(self.save_settings)
        adv_settings_store_layout.addWidget(self.SafeADVSettingsButton)
        self.SafeADVSettingsButton.setEnabled(True)
        
        # Glueing advanced setting layouts together
        adv_settings_layout = QVBoxLayout()
        adv_settings_layout.addLayout(adv_settings_value_layout)
        adv_settings_layout.addLayout(adv_settings_store_layout)
        #settings_layout.addLayout(settings_store_layout)
        
        # --- Pass Recording Settings UI ---
        self.passrec_settings_box = QGroupBox("Pass Recording")
        self.passrec_settings_box.setStyleSheet("QGroupBox{padding-top:15px;padding-bottom:5px; margin-top:5px}")
        passrec_settings_layout = QGridLayout()
        # Enable checkbox
        self.passrec_enable_checkbox = QCheckBox("Enable Pass Recording")
        self.passrec_enable_checkbox.setChecked(configur.getboolean('passrecording', 'enabled', fallback=False))
        passrec_settings_layout.addWidget(self.passrec_enable_checkbox, 0, 0, 1, 2)
        # Soundcard dropdown
        self.passrec_soundcard_label = QLabel("Soundcard:")
        passrec_settings_layout.addWidget(self.passrec_soundcard_label, 1, 0)
        self.passrec_soundcard_dropdown = QComboBox()
        devices = sd.query_devices()
        input_devices = [(i, d) for i, d in enumerate(devices) if d['max_input_channels'] > 0]
        for idx, dev in input_devices:
            hostapi = sd.query_hostapis(dev['hostapi'])['name'] if 'hostapi' in dev else ''
            # Create a more readable label for the device
            friendly_name = dev['name'].replace("[", "").replace("]", "").strip()
            if "Default" in friendly_name or "default" in friendly_name:
                label = f"Default Device"
            else:
                label = f"{friendly_name}"
                
            # Store the technical details as tooltip
            tech_details = f"{dev['name']} [{hostapi}] (index {idx})"
            self.passrec_soundcard_dropdown.addItem(label, idx)
            # Also store the device name and full details for persistence
            self.passrec_soundcard_dropdown.setItemData(self.passrec_soundcard_dropdown.count()-1, dev['name'], Qt.UserRole + 1)
            self.passrec_soundcard_dropdown.setItemData(self.passrec_soundcard_dropdown.count()-1, tech_details, Qt.ToolTipRole)
        # Set current
        current_card = configur.get('passrecording', 'soundcard', fallback='default dev')
        if current_card == 'default dev':
            self.passrec_soundcard_dropdown.setCurrentIndex(0)
        else:
            try:
                # Try to find the device by name instead of index
                found = False
                for i in range(self.passrec_soundcard_dropdown.count()):
                    if self.passrec_soundcard_dropdown.itemData(i, Qt.UserRole + 1) == current_card:
                        self.passrec_soundcard_dropdown.setCurrentIndex(i)
                        found = True
                        break
                # If name not found, try using it as an index (for backwards compatibility)
                if not found:
                    try:
                        index = int(current_card)
                        if 0 <= index < self.passrec_soundcard_dropdown.count():
                            self.passrec_soundcard_dropdown.setCurrentIndex(index)
                    except:
                        self.passrec_soundcard_dropdown.setCurrentIndex(0)
            except:
                self.passrec_soundcard_dropdown.setCurrentIndex(0)
        passrec_settings_layout.addWidget(self.passrec_soundcard_dropdown, 1, 1)
        
        # Add an audio level meter
        self.passrec_level_label = QLabel("Input Level:")
        passrec_settings_layout.addWidget(self.passrec_level_label, 8, 0)
        self.passrec_level_meter = AudioLevelMeter()
        passrec_settings_layout.addWidget(self.passrec_level_meter, 8, 1)
        
        # Add monitor button
        self.passrec_monitor_button = QPushButton("Start Monitoring")
        passrec_settings_layout.addWidget(self.passrec_monitor_button, 9, 0, 1, 2)
        self.passrec_monitor_button.clicked.connect(self.toggle_audio_monitoring)
        
        # Save dir
        self.passrec_savedir_label = QLabel("Save Directory:")
        passrec_settings_layout.addWidget(self.passrec_savedir_label, 2, 0)
        self.passrec_savedir_edit = QLineEdit(configur.get('passrecording', 'save_dir', fallback='./recordings'))
        passrec_settings_layout.addWidget(self.passrec_savedir_edit, 2, 1)
        # Min elevation
        self.passrec_minelev_label = QLabel("Min Elevation (deg):")
        passrec_settings_layout.addWidget(self.passrec_minelev_label, 3, 0)
        self.passrec_minelev_spin = QDoubleSpinBox()
        self.passrec_minelev_spin.setRange(0, 90)
        self.passrec_minelev_spin.setValue(configur.getfloat('passrecording', 'min_elevation', fallback=20.0))
        passrec_settings_layout.addWidget(self.passrec_minelev_spin, 3, 1)
        # Audio settings (advanced)
        self.passrec_samplerate_label = QLabel("Sample Rate:")
        passrec_settings_layout.addWidget(self.passrec_samplerate_label, 4, 0)
        self.passrec_samplerate_spin = QSpinBox()
        self.passrec_samplerate_spin.setRange(8000, 192000)
        self.passrec_samplerate_spin.setValue(configur.getint('passrecording', 'sample_rate', fallback=44100))
        passrec_settings_layout.addWidget(self.passrec_samplerate_spin, 4, 1)
        self.passrec_channels_label = QLabel("Channels:")
        passrec_settings_layout.addWidget(self.passrec_channels_label, 5, 0)
        self.passrec_channels_spin = QSpinBox()
        self.passrec_channels_spin.setRange(1, 2)
        self.passrec_channels_spin.setValue(configur.getint('passrecording', 'channels', fallback=1))
        passrec_settings_layout.addWidget(self.passrec_channels_spin, 5, 1)
        self.passrec_bitdepth_label = QLabel("Bit Depth:")
        passrec_settings_layout.addWidget(self.passrec_bitdepth_label, 6, 0)
        self.passrec_bitdepth_spin = QSpinBox()
        self.passrec_bitdepth_spin.setRange(8, 32)
        self.passrec_bitdepth_spin.setValue(configur.getint('passrecording', 'bit_depth', fallback=16))
        passrec_settings_layout.addWidget(self.passrec_bitdepth_spin, 6, 1)
        self.passrec_settings_box.setLayout(passrec_settings_layout)
        adv_settings_value_layout.addWidget(self.passrec_settings_box, 0,3)
        # --- End Pass Recording Settings UI ---
        
        ###  UI Layout / Tab Widget
        self.tab_widget = QTabWidget()
        self.tab_overview = QWidget()
        self.tab_settings = QWidget()
        self.tab_adv_settings = QWidget()
        self.tab_widget.addTab(self.tab_overview,"Overview")
        self.tab_widget.addTab(self.tab_settings,"Settings")
        self.tab_widget.addTab(self.tab_adv_settings,"Feature Settings")
        self.tab_overview.setLayout(overview_pagelayout)
        self.tab_settings.setLayout(settings_layout)
        self.tab_adv_settings.setLayout(adv_settings_layout)
        self.setCentralWidget(self.tab_widget)
        
        QScroller.grabGesture(
            self.combo1, QScroller.LeftMouseButtonGesture
        )

        self.threadpool = QThreadPool()
        self.timer = QTimer()
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.recurring_timer)

        self.utc_clock_timer = QTimer()
        self.utc_clock_timer.setInterval(500)
        self.utc_clock_timer.timeout.connect(self.recurring_utc_clock_timer)
        self.utc_clock_timer.start()
            
        
        self._last_cloudlog_F = None
        self._last_cloudlog_I = None
        self.pass_recorder = PassRecorder(configur)
        self.gps_enable_checkbox.toggled.connect(self.toggle_gps_qth)
        self.gps_reader = None
        self.gps_last_port = None
        self.gps_lock_button.clicked.connect(self.lock_gps_position)
        # Set last used port if available
        last_gps_port = configur.get('qth', 'gps_port', fallback=None)
        if last_gps_port and last_gps_port in gps_ports:
            self.gps_serialport_val.setCurrentText(last_gps_port)
            if self.gps_enable_checkbox.isChecked():
                self.start_gps_reader()
        elif last_gps_port:
            self.gps_status_label.setText("GPS Status: Saved port not available")
            self.gps_enable_checkbox.setChecked(False)
    
    def save_settings(self):
        global LATITUDE
        global LONGITUDE
        global ALTITUDE
        global STEP_RX
        global MAX_OFFSET_RX
        global DOPPLER_THRES_FM
        global DOPPLER_THRES_LINEAR
        global TLEFILE
        global TLEURL
        global SQFILE
        global RADIO
        global CVIADDR
        global OPMODE
        global LAST_TLE_UPDATE
        global RIG_TYPE
        global ROTATOR_SERIAL_PORT
        global ROTATOR_BAUDRATE
        global ROTATOR_AZ_PARK
        global ROTATOR_EL_PARK
        global ROTATOR_AZ_MIN
        global ROTATOR_AZ_MAX
        global ROTATOR_EL_MIN
        global ROTATOR_EL_MAX
        global ROTATOR_MIN_ELEVATION

        LATITUDE = self.qth_settings_lat_edit.displayText()
        configur['qth']['latitude'] = str(float(LATITUDE))
        LONGITUDE = self.qth_settings_long_edit.displayText()
        configur['qth']['longitude'] = str(float(LONGITUDE))
        ALTITUDE = float(self.qth_settings_alt_edit.displayText())
        configur['qth']['altitude'] = str(float(ALTITUDE))
        STEP_RX = int(self.qthsteprx.displayText())
        configur['qth']['step_rx'] = str(int(STEP_RX))
        MAX_OFFSET_RX = int(self.qthmaxoffrx.displayText())
        configur['qth']['max_offset_rx'] = str(int(MAX_OFFSET_RX))
        TLEFILE = configur['satellite']['tle_file'] = str(self.sattle.displayText())
        TLEURL =  configur['satellite']['tle_url'] = str(self.sattleurl.displayText())
        SQFILE = configur['satellite']['sqffile'] = str(self.satsqf.displayText())
        
        DOPPLER_THRES_FM = int(self.doppler_fm_threshold.displayText())
        configur['satellite']['doppler_threshold_fm'] = str(int(DOPPLER_THRES_FM))
        DOPPLER_THRES_LINEAR = int(self.doppler_linear_threshold.displayText())
        configur['satellite']['doppler_threshold_linear'] = str(int(DOPPLER_THRES_LINEAR))
        
        if self.radiolistcomb.currentText() == "Icom 9700":
            RADIO = configur['icom']['radio'] = '9700'
        elif self.radiolistcomb.currentText() == "Icom 910H":
            RADIO = configur['icom']['radio'] = '910'
            
        if self.radio_country_config_eu_button.isChecked():
            RIG_TYPE = "EU"
        elif self.radio_country_config_us_button.isChecked():
            RIG_TYPE = "US"
        configur['icom']['rig_type'] = RIG_TYPE

        CVIADDR = str(self.radicvi.displayText())
        configur['icom']['cviaddress'] = CVIADDR
        RIG_SERIAL_PORT = self.rig_serialport_val.currentText()
        configur['icom']['serialport'] = RIG_SERIAL_PORT
        
        # Saving offsets
        offset_stored = False        
        num_offsets = 0
        for (each_key, each_val) in configur.items('offset_profiles'):
            num_offsets = num_offsets+1
            # Iterate through each entry if sat/tpx combo is already in list otherwise adds it. 
            parts = each_val.split(",")
            if len(parts) >= 3 and parts[0].strip() == self.my_satellite.name and parts[1].strip() == self.my_transponder_name:
                offset_stored = True
                if int(parts[2].strip()) != int(self.rxoffsetbox.value()):
                    configur['offset_profiles'][each_key] = self.my_satellite.name + "," + self.my_transponder_name + ","+str(self.rxoffsetbox.value()) + ",0"
        if offset_stored == False and int(self.rxoffsetbox.value()) != 0 and self.combo1.currentIndex() != 0:
            configur['offset_profiles']["satoffset"+str(num_offsets+1)] = self.my_satellite.name + "," + self.my_transponder_name + ","+str(self.rxoffsetbox.value()) + ",0"
            offset_stored = True
        
        # Save TLE update
        configur['misc']['last_tle_update'] = LAST_TLE_UPDATE
        
        ROTATOR_ENABLED = self.rotator_enable_button.isChecked()
        configur['rotator']['enabled'] = str(ROTATOR_ENABLED)
        ROTATOR_SERIAL_PORT = self.rotator_serialport_val.currentText()
        configur['rotator']['serial_port'] = ROTATOR_SERIAL_PORT
        ROTATOR_BAUDRATE = int(self.rotator_serialrate_val.displayText())
        configur['rotator']['baudrate'] = str(ROTATOR_BAUDRATE)
        ROTATOR_AZ_PARK = int(self.rotator_azpark_val.displayText())
        configur['rotator']['az_park'] = str(ROTATOR_AZ_PARK)
        ROTATOR_EL_PARK = int(self.rotator_elpark_val.displayText())
        configur['rotator']['el_park'] = str(ROTATOR_EL_PARK)
        ROTATOR_AZ_MIN = int(self.rotator_azmin_val.displayText())
        configur['rotator']['az_min'] = str(ROTATOR_AZ_MIN)
        ROTATOR_AZ_MAX = int(self.rotator_azmax_val.displayText())
        configur['rotator']['az_max'] = str(ROTATOR_AZ_MAX)
        ROTATOR_EL_MIN = int(self.rotator_elmin_val.displayText())
        configur['rotator']['el_min'] = str(ROTATOR_EL_MIN)
        ROTATOR_EL_MAX = int(self.rotator_elmax_val.displayText())
        configur['rotator']['el_max'] = str(ROTATOR_EL_MAX)
        ROTATOR_MIN_ELEVATION = int(self.rotator_minelev_val.displayText())
        configur['rotator']['min_elevation'] = str(ROTATOR_MIN_ELEVATION)
        ROTATOR_POSITION_POLL_INTERVAL = float(self.rotator_pollinterval_val.displayText())
        configur['rotator']['position_poll_interval'] = str(ROTATOR_POSITION_POLL_INTERVAL)
        
        WEBAPI_ENABLED = self.webapi_enable_button.isChecked()
        WEBAPI_DEBUG_ENABLED = self.webapi_debug_enable_button.isChecked()
        configur['web_api']['enabled'] = str(WEBAPI_ENABLED)
        configur['web_api']['debug'] = str(WEBAPI_DEBUG_ENABLED)
        configur['web_api']['port'] = WEBAPI_PORT = self.webapi_port_val.displayText()

        # Pass Recording settings
        configur['passrecording']['enabled'] = str(self.passrec_enable_checkbox.isChecked())
        # Store the device name instead of the index
        selected_idx = self.passrec_soundcard_dropdown.currentIndex()
        if selected_idx >= 0:
            # First try to get the full device name (most reliable)
            device_name = self.passrec_soundcard_dropdown.itemData(selected_idx, Qt.UserRole + 1)
            if device_name:
                configur['passrecording']['soundcard'] = device_name
                logging.info(f"Saved audio device by name: {device_name}")
            else:
                # Fallback to index if name isn't available (should not happen)
                device_idx = self.passrec_soundcard_dropdown.itemData(selected_idx)
                if device_idx is not None:
                    configur['passrecording']['soundcard'] = str(device_idx)
                    logging.info(f"Saved audio device by index: {device_idx}")
                else:
                    configur['passrecording']['soundcard'] = 'default'
                    logging.info("Saved default audio device")
        else:
            configur['passrecording']['soundcard'] = 'default'
            logging.info("Saved default audio device")
        configur['passrecording']['save_dir'] = self.passrec_savedir_edit.text()
        configur['passrecording']['min_elevation'] = str(self.passrec_minelev_spin.value())
        configur['passrecording']['sample_rate'] = str(self.passrec_samplerate_spin.value())
        configur['passrecording']['channels'] = str(self.passrec_channels_spin.value())
        configur['passrecording']['bit_depth'] = str(self.passrec_bitdepth_spin.value())

        # GPS QTH settings
        configur['qth']['use_gps'] = str(self.gps_enable_checkbox.isChecked())
        configur['qth']['gps_port'] = self.gps_serialport_val.currentText()

        with open('config.ini', 'w') as configfile:
            configur.write(configfile)
        self.pass_recorder.update_config(configur)

    def rxoffset_value_changed(self, i):
            global f_cal
            self.my_satellite.new_cal = 1
            self.my_satellite.F_cal = f_cal = i
            
            # Notify web clients of RX offset change
            if WEBAPI_ENABLED:
                try:
                    web_api.safe_emit('status', {'rx_offset': i})
                except Exception as e:
                    logging.error(f"Error broadcasting RX offset change to web clients: {e}")
    
    def rxoffset_button_pushed(self, i):
            new_value = self.rxoffsetbox.value() + int(i)
            self.rxoffsetbox.setValue(new_value)
            
            # Notify web clients of RX offset change (note: setValue will trigger the valueChanged signal, 
            # but we'll add this for clarity and as a backup)
            if WEBAPI_ENABLED:
                try:
                    web_api.safe_emit('status', {'rx_offset': new_value})
                except Exception as e:
                    logging.error(f"Error broadcasting RX offset button change to web clients: {e}")
    def update_tle_file(self):
        self.the_stop_button_was_clicked()
        try:
            
            global LAST_TLE_UPDATE
            urllib.request.urlretrieve(TLEURL, TLEFILE)
            LAST_TLE_UPDATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.tleupdate_stat_lbl.setText("✔" + LAST_TLE_UPDATE)
            self.save_settings()
            if self.my_satellite.name != '':
                self.sat_changed(self.my_satellite.name)
        except Exception as e:
            logging.error("***  Unable to download TLE file: {theurl}".format(theurl=TLEURL))
            logging.error(e)
            self.tleupdate_stat_lbl.setText("❌")
            
    def sat_changed(self, satname):
        self.my_satellite.name = satname

        try:
            with open(SQFILE, 'r') as h:
                sqfdata = h.readlines()
                tpxlist=[]
                # Block signals temporarily while we clear the combo box
                self.combo2.blockSignals(True)
                self.combo2.clear()
                self.combo2.blockSignals(False)
                
                for line in sqfdata:
                    if line.startswith(satname):
                        tpxlist += [str(line.split(",")[8].strip())]
                        
                tpxlist=list(dict.fromkeys(tpxlist))
                
                # Add items one by one to ensure signals are properly emitted
                for tpx in tpxlist:
                    self.combo2.addItem(tpx)
                    
        except Exception as e:
            logging.error(f"Error reading SQFFile: {e}")
            
        # Notify web clients of the satellite change
        if WEBAPI_ENABLED:
            try:
                web_api.broadcast_satellite_change(satname)
            except Exception as e:
                logging.error(f"Error broadcasting satellite change to web clients: {e}")
                
    def tpx_changed(self, tpxname):
        global f_cal
        global i_cal
        global MAX_OFFSET_RX
        global RX_TPX_ONLY
        
        logging.debug(f"tpx_changed called with transponder: {tpxname}")
        self.my_transponder_name = tpxname
        
        try:
            with open(SQFILE, 'r') as h:
                sqfdata = h.readlines()
                found_match = False
                for lineb in sqfdata:
                    if lineb.startswith(";") == 0:
                        if lineb.split(",")[8].strip() == tpxname and lineb.split(",")[0].strip() == self.my_satellite.name:
                            found_match = True
                            logging.debug(f"Found matching transponder in SQFILE: {tpxname} for satellite {self.my_satellite.name}")
                            self.my_satellite.F = self.my_satellite.F_init = float(lineb.split(",")[1].strip())*1000
                            self.rxfreq.setText(str('{:,}'.format(self.my_satellite.F))+ " Hz")
                            self.my_satellite.F_RIG = self.my_satellite.F + f_cal
                            self.my_satellite.I = self.my_satellite.I_init = float(lineb.split(",")[2].strip())*1000
                            self.txfreq.setText(str('{:,}'.format(self.my_satellite.I)) + " Hz")
                            self.my_satellite.I_RIG = self.my_satellite.I + i_cal
                            self.my_satellite.downmode =  lineb.split(",")[3].strip()
                            self.my_satellite.upmode =  lineb.split(",")[4].strip()
                            self.my_satellite.mode =  lineb.split(",")[5].strip()
                            #  check if frequencies are in the same band: e.g. U/U, V/V vs V/U, U/V
                            if abs(self.my_satellite.F - self.my_satellite.I) > 10000000:
                                self.my_satellite.rig_satmode = 1
                            else:
                                self.my_satellite.rig_satmode = 0
                            if self.my_satellite.F == 0:
                                self.Startbutton.setEnabled(False)
                                self.Stopbutton.setEnabled(False)
                                self.syncbutton.setEnabled(False)
                                self.offsetstorebutton.setEnabled(False)
                            else:
                                self.Startbutton.setEnabled(True)
                                self.syncbutton.setEnabled(True)
                                self.offsetstorebutton.setEnabled(True)
                                
                            if  self.my_satellite.F > 0 and self.my_satellite.I == 0:
                                RX_TPX_ONLY = True
                                self.my_satellite.rig_satmode = 0
                            else:
                                RX_TPX_ONLY = False
                            break
                
                if not found_match:
                    logging.info(f"Warning: No matching entry found for transponder: {tpxname} and satellite: {self.my_satellite.name}")
        except IOError as e:
            logging.error(f"IO Error when processing transponder change: {e}")

        logging.debug(f"Setting RX offset to 0")
        self.rxoffsetbox.setValue(0)
        for tpx in useroffsets:
            if tpx[0] == self.my_satellite.name and tpx[1] == tpxname:
                usrrxoffset=int(tpx[2])
                logging.debug(f"Found user offset for this satellite+transponder: {usrrxoffset}")
                if usrrxoffset < MAX_OFFSET_RX and usrrxoffset > -MAX_OFFSET_RX:
                    logging.debug(f"Setting RX offset to: {usrrxoffset}")
                    self.rxoffsetbox.setMaximum(MAX_OFFSET_RX)
                    self.rxoffsetbox.setMinimum(-MAX_OFFSET_RX)
                    self.rxoffsetbox.setValue(usrrxoffset)
                    self.my_satellite.new_cal = 1
                    self.my_satellite.F_cal = f_cal = usrrxoffset
                else:
                    logging.debug(f"User offset {usrrxoffset} outside allowed range [-{MAX_OFFSET_RX}, {MAX_OFFSET_RX}]")
                    self.rxoffsetbox.setValue(0)
                
                
        self.my_satellite.tledata = ""
        
        # Safely stop the timer from any thread
        try:
            QMetaObject.invokeMethod(self.timer, "stop", Qt.QueuedConnection)
            logging.debug("Timer stopped safely")
        except Exception as e:
            logging.error(f"Error stopping timer: {e}")
            # Fallback: try direct stop if invokeMethod failed
            try:
                if QThread.currentThread() == self.thread():
                    self.timer.stop()
                    logging.debug("Timer stopped directly")
                else:
                    logging.error("Cannot stop timer - not in main thread")
            except Exception as e2:
                logging.error(f"Error in fallback timer stop: {e2}")
                
        try:
            with open(TLEFILE, 'r') as f:
                data = f.readlines()  
                tle_found = False
                for index, line in enumerate(data):
                    if str(self.my_satellite.name) in line:
                        logging.debug(f"Found TLE data for satellite: {self.my_satellite.name}")
                        self.my_satellite.tledata = ephem.readtle(data[index], data[index+1], data[index+2])
                        tle_found = True
                        break
                        
                if not tle_found:
                    logging.warning(f"Warning: No TLE data found for satellite: {self.my_satellite.name}")
        except IOError as e:
            logging.error(f"IO Error when reading TLE file: {e}")
        
        if self.my_satellite.tledata == "":
            logging.info("TLE data is empty, disabling tracking buttons")
            self.Startbutton.setEnabled(False)
            self.syncbutton.setEnabled(False)
            self.offsetstorebutton.setEnabled(False)
            self.log_tle_state_val.setText("n/a")
            return
        else:
            day_of_year = datetime.now().timetuple().tm_yday
            tleage = int(data[index+1][20:23])
            self.my_satellite.tle_age = day_of_year - tleage
            self.log_tle_state_val.setText("{0} day(s)".format(self.my_satellite.tle_age))

        # Send to Cloudlog in background after updating satellite/transponder info
        if not CLOUDLOG_ENABLED:
            logging.debug("Cloudlog: Disabled in config.ini")
        elif not CLOUDLOG_API_KEY or not CLOUDLOG_URL:
            logging.warning("Cloudlog API key or URL not set in config.ini")
        else:
            worker = CloudlogWorker(
                sat=self.my_satellite,
                tx_freq=self.my_satellite.I,
                rx_freq=self.my_satellite.F,
                tx_mode=self.my_satellite.upmode,
                rx_mode=self.my_satellite.downmode,
                sat_name=self.my_satellite.name,
                log_url=CLOUDLOG_URL,
                log_api_key=CLOUDLOG_API_KEY
            )
            QThreadPool.globalInstance().start(worker)
            self._last_cloudlog_F = self.my_satellite.F
            self._last_cloudlog_I = self.my_satellite.I
            
        # Safely start the timer from any thread    
        try:
            QMetaObject.invokeMethod(self.timer, "start", Qt.QueuedConnection)
            logging.debug("Timer started safely")
        except Exception as e:
            logging.error(f"Error starting timer: {e}")
            # Fallback: try direct start if invokeMethod failed
            try:
                if QThread.currentThread() == self.thread():
                    self.timer.start()
                    logging.debug("Timer started directly")
                else:
                    logging.error("Cannot start timer - not in main thread")
            except Exception as e2:
                logging.error(f"Error in fallback timer start: {e2}")
        
        # Notify web clients of the transponder change
        if WEBAPI_ENABLED:
            try:
                web_api.broadcast_transponder_change(tpxname)
            except Exception as e:
                logging.error(f"Error broadcasting transponder change to web clients: {e}")
            
    def tone_changed(self, tone_name):
        
        if self.my_satellite.rig_satmode == 1:
            icomTrx.setVFO("Sub")
        else:
            icomTrx.setVFO("VFOB")
            
        if RIG_TYPE == "US":
            if tone_name == "67 Hz":
                icomTrx.setToneSQLHz(str(670))
                icomTrx.setToneSquelchOn(1)
            elif tone_name == "71.9 Hz":
                icomTrx.setToneSQLHz(str(719))
                icomTrx.setToneSquelchOn(1)
            elif tone_name == "74.4 Hz":
                icomTrx.setToneSQLHz(str(744))
                icomTrx.setToneSquelchOn(1)
            elif tone_name == "141.3 Hz":
                icomTrx.setToneSQLHz(str(1413))
                icomTrx.setToneSquelchOn(1)
            elif tone_name == "None":
                icomTrx.setToneSquelchOn(0)
        elif RIG_TYPE == "EU":
            if tone_name == "67 Hz":
                icomTrx.setToneHz(str(670))
                icomTrx.setToneOn(1)
            elif tone_name == "71.9 Hz":
                icomTrx.setToneHz(str(719))
                icomTrx.setToneOn(1)
            elif tone_name == "74.4 Hz":
                icomTrx.setToneHz(str(744))
                icomTrx.setToneOn(1)
            elif tone_name == "141.3 Hz":
                icomTrx.setToneHz(str(1413))
                icomTrx.setToneOn(1)
            elif tone_name == "None":
                icomTrx.setToneOn(0)
            
        if self.my_satellite.rig_satmode == 1:
            icomTrx.setVFO("Main")
        else:
            icomTrx.setVFO("VFOA")
            
        # Notify web clients of the subtone change
        if WEBAPI_ENABLED:
            try:
                web_api.broadcast_subtone_change(tone_name)
            except Exception as e:
                logging.error(f"Error broadcasting subtone change to web clients: {e}")

    def the_exit_button_was_clicked(self):
        self.the_stop_button_was_clicked()
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
        # Set pass recorder to inactive tracking state
        self.pass_recorder.set_tracking_active(False)
        # Stop rotator thread and park
        if ROTATOR_ENABLED:
            self.stop_rotator_thread()
            self.park_rotators()
        # Restart position worker with slower polling when tracking stops
        if ROTATOR_ENABLED:
            self.restart_rotator_position_worker()
        # Notify web clients of tracking state change
        if WEBAPI_ENABLED:
            try:
                web_api.broadcast_tracking_state(False)
            except Exception as e:
                logging.error(f"Error broadcasting tracking stop to web clients: {e}")

    def the_sync_button_was_clicked(self):
        self.my_satellite.F = self.my_satellite.F_init
        self.my_satellite.I = self.my_satellite.I_init
    
    def init_worker(self):
        global TRACKING_ACTIVE
        self.syncbutton.setEnabled(True)
        self.offsetstorebutton.setEnabled(True)
        self.Stopbutton.setEnabled(True)
        if TRACKING_ACTIVE == False:
            TRACKING_ACTIVE = True
        self.Startbutton.setEnabled(False)
        self.combo1.setEnabled(False)
        self.combo2.setEnabled(False)
        self.doppler_worker = Worker(self.calc_doppler)
        
        # Set high priority for doppler calculations
        # This ensures doppler calculations run at higher priority than WebSocket communications
        # For PySide6, we need to use the integer priority value directly
        self.threadpool.start(self.doppler_worker, QThread.HighestPriority.value)
        
        # Set pass recorder to active tracking state
        self.pass_recorder.set_tracking_active(True)
        # Optimize rotator route before starting tracking (only if satellite is visible or approaching)
        if ROTATOR_ENABLED and self.rotator_optimizer:
            self.last_prediction_time = time.time()  # Initialize prediction timer
            # Only optimize if satellite is visible or approaching horizon
            current_elevation = float(sat_ele_calc(self.my_satellite.tledata, myloc))
            if current_elevation >= -3:
                logging.info(f"🛰 Starting tracking - optimizing route (el={current_elevation:.1f}°)")
                self.optimize_rotator_route()
            else:
                logging.info(f"🛰 Starting tracking - satellite below horizon (el={current_elevation:.1f}°), skipping optimization")
        # Start rotator thread
        if ROTATOR_ENABLED:
            self.start_rotator_thread()
        # Restart position worker with faster polling when tracking starts
        if ROTATOR_ENABLED:
            self.restart_rotator_position_worker()
        # Notify web clients of tracking state change
        if WEBAPI_ENABLED:
            try:
                web_api.broadcast_tracking_state(True)
            except Exception as e:
                logging.error(f"Error broadcasting tracking start to web clients: {e}")

    def calc_doppler(self, progress_callback):
        global CVIADDR
        global TRACKING_ACTIVE
        global INTERACTIVE
        global myloc
        global f_cal
        global i_cal
        global doppler_thres
        
        try:
                #################################
                #       INIT RADIOS
                #################################

                if RADIO == "910" and self.my_satellite.rig_satmode == 0 and RX_TPX_ONLY == False:
                    icomTrx.setSatelliteMode(0)
                    icomTrx.setSplitOn(1)
                elif RADIO == "910" and self.my_satellite.rig_satmode == 0 and RX_TPX_ONLY == True:
                    icomTrx.setSatelliteMode(0)
                    icomTrx.setSplitOn(0)
                elif RADIO == "910" and self.my_satellite.rig_satmode == 1:
                    icomTrx.setSatelliteMode(1)
                    icomTrx.setSplitOn(0)
                elif ( RADIO == "705" or "818" ) and OPMODE == False and self.my_satellite.rig_satmode == 0: #not implemented yet
                    logging.error("*** Not implemented yet mate***")
                    sys.exit()

                #################################
                #       SETUP DOWNLINK & UPLINK
                #################################

                if RADIO == "910":
                    # Testing current satmode config for V/U or U/V and swapping if needed
                    icomTrx.setVFO("Main")
                    curr_band = int(icomTrx.getFrequency())
                    if curr_band > 400000000 and self.my_satellite.F_RIG < 400000000:
                        icomTrx.setExchange()
                    elif curr_band < 200000000 and self.my_satellite.F_RIG > 200000000:
                        icomTrx.setExchange()
                            
                    doppler_thres, INTERACTIVE = icomTrx.setup_vfos(self.my_satellite.rig_satmode,self.my_satellite.downmode, self.my_satellite.upmode, DOPPLER_THRES_FM, DOPPLER_THRES_LINEAR)
                    
                elif RADIO != "910":
                    logging.error("*** Not implemented yet mate***")
                    sys.exit()

                icomTrx.setVFO("Main") 

                date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                myloc.date = ephem.Date(date_val)

                self.my_satellite.F_RIG = rx_dopplercalc(self.my_satellite.tledata, self.my_satellite.F, myloc)
                self.my_satellite.I_RIG = tx_dopplercalc(self.my_satellite.tledata, self.my_satellite.I, myloc)
                self.rxdoppler_val.setText(str('{:,}'.format(float(rx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.F, myloc)))))
                self.txdoppler_val.setText(str('{:,}'.format(float(tx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.I, myloc)))))
                user_Freq = 0;
                user_Freq_history = [0, 0, 0, 0]
                vfo_not_moving = 0
                vfo_not_moving_old = 0
                ptt_state = 0
                ptt_state_old = 0
                
                if self.my_satellite.rig_satmode == 1:
                    icomTrx.setVFO("Main")
                    icomTrx.setFrequency(str(int(self.my_satellite.F_RIG)))
                    icomTrx.setVFO("SUB")
                    icomTrx.setFrequency(str(int(self.my_satellite.I_RIG)))
                else:
                    icomTrx.setVFO("VFOA")
                    icomTrx.setFrequency(str(int(self.my_satellite.F_RIG)))
                    if RX_TPX_ONLY == False:
                        icomTrx.setVFO("VFOB")
                        icomTrx.setFrequency(str(int(self.my_satellite.I_RIG)))
                        INTERACTIVE = False #for SSB packet sats
                        icomTrx.setVFO("VFOA")
                    else:
                        icomTrx.setSplitOn(0)
                
                # Ensure that initial frequencies are always written 
                tracking_init = 1

                while TRACKING_ACTIVE == True:
                    a = datetime.now()
                    #date_val = strftime('%Y/%m/%d %H:%M:%S', gmtime())
                    date_val = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
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
                            if abs(user_Freq - self.my_satellite.F_RIG) > 1:
                                if True:
                                    if user_Freq > self.my_satellite.F_RIG:
                                        delta_F = user_Freq - self.my_satellite.F_RIG
                                        if self.my_satellite.mode == "REV":
                                            self.my_satellite.I -= delta_F
                                            self.my_satellite.I_RIG -= delta_F
                                            self.my_satellite.F += delta_F
                                        else:
                                            self.my_satellite.I += delta_F
                                            self.my_satellite.I_RIG += delta_F
                                            self.my_satellite.F += delta_F
                                    else:
                                        delta_F = self.my_satellite.F_RIG - user_Freq
                                        if self.my_satellite.mode == "REV":
                                            self.my_satellite.I += delta_F
                                            self.my_satellite.I_RIG += delta_F
                                            self.my_satellite.F -= delta_F
                                        else:
                                            self.my_satellite.I -= delta_F
                                            self.my_satellite.I_RIG -= delta_F
                                            self.my_satellite.F -= delta_F
                                    self.my_satellite.F_RIG = user_Freq
                                            
                        # check if dial isn't moving, might be skipable as later conditional check yields the same         
                        if updated_rx and vfo_not_moving and vfo_not_moving_old:#old_user_Freq == user_Freq and False:
                            new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata, self.my_satellite.F + self.my_satellite.F_cal, myloc))
                            if abs(new_rx_doppler-self.my_satellite.F_RIG) > doppler_thres:
                                rx_doppler = new_rx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("Main")
                                else:
                                    icomTrx.setVFO("VFOA")
                                
                                icomTrx.setFrequency(str(rx_doppler))
                                self.my_satellite.F_RIG = rx_doppler
                        
                            new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata, self.my_satellite.I, myloc))
                            if abs(new_tx_doppler-self.my_satellite.I_RIG) > doppler_thres:
                                tx_doppler = new_tx_doppler
                                if self.my_satellite.rig_satmode == 1:
                                    icomTrx.setVFO("SUB")
                                else:
                                    icomTrx.setVFO("VFOB")
                                    # Don't switch VFO when PTT is pushed, to avoid switching VFO while TX 
                                    while icomTrx.isPttOff == 0:
                                        time.sleep(0.1)
                                        
                                icomTrx.setFrequency(str(tx_doppler))
                                self.my_satellite.I_RIG = tx_doppler
                            time.sleep(0.2)
                    # FM sats, no dial input accepted!
                    elif self.my_satellite.rig_satmode == 1:
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata,self.my_satellite.F + self.my_satellite.F_cal, myloc))
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata,self.my_satellite.I, myloc))
                        if abs(new_rx_doppler-self.my_satellite.F_RIG) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                rx_doppler = new_rx_doppler
                                icomTrx.setVFO("MAIN")
                                icomTrx.setFrequency(str(rx_doppler))
                                self.my_satellite.F_RIG = rx_doppler
                        if abs(new_tx_doppler-self.my_satellite.I_RIG) > doppler_thres or tracking_init == 1:
                                tracking_init = 0
                                tx_doppler = new_tx_doppler
                                icomTrx.setVFO("SUB")
                                icomTrx.setFrequency(str(tx_doppler))
                                self.my_satellite.I_RIG = tx_doppler
                                icomTrx.setVFO("MAIN")
                        if doppler_thres > 0:
                            time.sleep(FM_update_time) # Slower update rate on FM, max on linear sats
                            
                    else:
                        new_rx_doppler = round(rx_dopplercalc(self.my_satellite.tledata,self.my_satellite.F + self.my_satellite.F_cal, myloc))
                        new_tx_doppler = round(tx_dopplercalc(self.my_satellite.tledata,self.my_satellite.I, myloc))
                        # 0 = PTT is pressed
                        # 1 = PTT is released
                        ptt_state_old = ptt_state
                        ptt_state = icomTrx.isPttOff()
                        # Check for RX -> TX transition
                        if  ptt_state_old and ptt_state == 0 and abs(new_tx_doppler-self.my_satellite.I_RIG) > doppler_thres:
                            #icomTrx.setVFO("VFOB")
                            logging.debug("TX inititated")
                            tx_doppler = new_tx_doppler
                            self.my_satellite.I_RIG = tx_doppler
                            icomTrx.setFrequency(str(tx_doppler))
                        if  ptt_state and abs(new_rx_doppler-self.my_satellite.F_RIG) > doppler_thres:
                            rx_doppler = new_rx_doppler
                            self.my_satellite.F_RIG = rx_doppler
                            icomTrx.setVFO("VFOA")
                            icomTrx.setFrequency(str(rx_doppler))
                        time.sleep(0.025)
                        
                    self.my_satellite.new_cal = 0
                    time.sleep(0.01)
                    #b = datetime.now()
                    #c = b - a
                    #print("Ups:" +str(1000000/c.microseconds))  
                    

        except:
            logging.critical("Failed to open ICOM rig")
            sys.exit()
    
    def recurring_utc_clock_timer(self):
        date_val = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
        myloc.date = ephem.Date(date_val)
        self.log_time_val.setText(datetime.now(timezone.utc).strftime('%H:%M:%S')+"z")
        if self.my_satellite.tledata != "":
            self.log_sat_event_val.setText(str(sat_next_event_calc(self.my_satellite.tledata, myloc)))
        if icomTrx.is_connected():
            self.log_rig_state_val.setText("✔")
            self.log_rig_state_val.setStyleSheet('color: green')
        else:
            self.log_rig_state_val.setText("✘")
            self.log_rig_state_val.setStyleSheet('color: red')
            
    
    def recurring_timer(self):
        try:
            date_val = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
            myloc.date = ephem.Date(date_val)
            
            
            self.my_satellite.down_doppler_old = self.my_satellite.down_doppler
            self.my_satellite.down_doppler = float(rx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.F, myloc))
            self.my_satellite.down_doppler_rate = ((self.my_satellite.down_doppler - self.my_satellite.down_doppler_old)/2)/0.2
            if abs(self.my_satellite.down_doppler_rate) > 100.0:
                self.my_satellite.down_doppler_rate = 0.0
                
            self.my_satellite.up_doppler_old = self.my_satellite.up_doppler
            self.my_satellite.up_doppler = float(tx_doppler_val_calc(self.my_satellite.tledata,self.my_satellite.I, myloc))
            self.my_satellite.up_doppler_rate = ((self.my_satellite.up_doppler - self.my_satellite.up_doppler_old)/2)/0.2
            if abs(self.my_satellite.up_doppler_rate) > 100.0:
                self.my_satellite.up_doppler_rate = 0.0
                
            self.rxdoppler_val.setText(str('{:,}'.format(self.my_satellite.down_doppler)) + " Hz")
            self.txdoppler_val.setText(str('{:,}'.format(self.my_satellite.up_doppler)) + " Hz")
            self.rxdopplerrate_val.setText(str(format(self.my_satellite.down_doppler_rate, '.2f')) + " Hz/s")
            self.txdopplerrate_val.setText(str(format(self.my_satellite.up_doppler_rate, '.2f')) + " Hz/s")
            self.rxfreq.setText(str('{:,}'.format(self.my_satellite.F_RIG))+ " Hz")
            self.rxfreq_onsat.setText(str('{:,}'.format(self.my_satellite.F))+ " Hz")
            self.txfreq.setText(str('{:,}'.format(self.my_satellite.I_RIG))+ " Hz")
            self.txfreq_onsat.setText(str('{:,}'.format(self.my_satellite.I))+ " Hz")
            self.log_sat_status_ele_val.setText(str(sat_ele_calc(self.my_satellite.tledata, myloc)) + " °")
            self.log_sat_status_azi_val.setText(str(sat_azi_calc(self.my_satellite.tledata, myloc)) + " °")
            self.log_sat_status_height_val.setText(str(sat_height_calc(self.my_satellite.tledata, myloc)) + " km")
            self.log_sat_status_illumintated_val.setText(sat_eclipse_calc(self.my_satellite.tledata, myloc))
            
            if DISPLAY_MAP:
                self.map_canvas.lat = sat_lat_calc(self.my_satellite.tledata, myloc)
                self.map_canvas.lon = sat_lon_calc(self.my_satellite.tledata, myloc)
                self.map_canvas.alt_km = int(round(float(sat_height_calc(self.my_satellite.tledata, myloc))))
                self.map_canvas.draw_map()

            # Cloudlog: only log if F or I changed and satellite is above horizon
            try:
                # Get elevation value directly
                elevation = float(sat_ele_calc(self.my_satellite.tledata, myloc))
                
                # Update pass recorder with current elevation - no need to log every update
                if self.my_satellite.name:
                    self.on_satellite_update(elevation, self.my_satellite.name)
                
                # Check if we need to update optimization status based on elevation change
                if ROTATOR_ENABLED and hasattr(self, 'pass_optimization'):
                    self.check_and_update_optimization_status()
                
                # Only re-predict if no optimization exists and satellite is approaching horizon
                if ROTATOR_ENABLED and hasattr(self, 'last_prediction_time'):
                    # Only re-predict if no optimization data exists AND satellite is approaching horizon (-3° to 0°)
                    if ((not hasattr(self, 'pass_optimization') or self.pass_optimization is None) and
                        elevation >= -3 and elevation < 0):
                        logging.info(f"🔄 Re-running satellite pass prediction (el={elevation:.1f}°)...")
                        self.optimize_rotator_route()
                        self.last_prediction_time = time.time()
                
                # Handle Cloudlog updates
                F_now = self.my_satellite.F
                I_now = self.my_satellite.I
                if elevation > 0.0 and (F_now != self._last_cloudlog_F or I_now != self._last_cloudlog_I):
                    if not CLOUDLOG_ENABLED:
                        logging.debug("Cloudlog: Disabled in config.ini")
                    elif not CLOUDLOG_API_KEY or not CLOUDLOG_URL:
                        logging.warning("Cloudlog API key or URL not set in config.ini")
                    else:
                        worker = CloudlogWorker(
                            sat=self.my_satellite,
                            tx_freq=self.my_satellite.I,
                            rx_freq=self.my_satellite.F,
                            tx_mode=self.my_satellite.upmode,
                            rx_mode=self.my_satellite.downmode,
                            sat_name=self.my_satellite.name,
                            log_url=CLOUDLOG_URL,
                            log_api_key=CLOUDLOG_API_KEY
                        )
                        QThreadPool.globalInstance().start(worker)
                        self._last_cloudlog_F = self.my_satellite.F
                        self._last_cloudlog_I = self.my_satellite.I
            except Exception as e:
                logging.error(f"Error getting satellite elevation: {e}")
                elevation = -1
        except:
            logging.warning("Error in label timer")
            traceback.print_exc()

    @Slot(str)
    def slot_select_satellite(self, sat_name):
        # Set the combo box and call sat_changed in the main thread
        for i in range(self.combo1.count()):
            if self.combo1.itemText(i) == sat_name:
                self.combo1.setCurrentIndex(i)
                break
        self.sat_changed(sat_name)

    @Slot(str)
    def slot_select_transponder(self, tpx_name):
        for i in range(self.combo2.count()):
            if self.combo2.itemText(i) == tpx_name:
                self.combo2.setCurrentIndex(i)
                break
        self.tpx_changed(tpx_name)

    @Slot(str)
    def slot_set_subtone(self, tone):
        for i in range(self.combo3.count()):
            if self.combo3.itemText(i) == tone:
                self.combo3.setCurrentIndex(i)
                break
        self.tone_changed(tone)

    @Slot(int)
    def slot_set_rx_offset(self, offset):
        min_val = self.rxoffsetbox.minimum()
        max_val = self.rxoffsetbox.maximum()
        if min_val <= offset <= max_val:
            self.rxoffsetbox.setValue(offset)

    # The slots for start_tracking and stop_tracking are already connected to init_worker and the_stop_button_was_clicked

    # Remove all QMetaObject.invokeMethod and run_on_ui_thread logic for GUI/timer operations in this file.
    # Only start/stop timers in the main thread via these slots.

    def get_current_az_el(self):
        # Returns (az, el) as floats for the current satellite
        try:
            az = float(sat_azi_calc(self.my_satellite.tledata, myloc))
            el = float(sat_ele_calc(self.my_satellite.tledata, myloc))
            
            # If we have optimization data and satellite is approaching horizon, use the optimized azimuth
            if (hasattr(self, 'pass_optimization') and self.pass_optimization and 
                el >= -10):  # Only check optimization when satellite is approaching horizon
                opt_details = self.pass_optimization.get('optimization_details', {})
                route_segments = opt_details.get('route_segments', [])
                
                # Find the closest route segment to current time
                current_time = datetime.now(timezone.utc)
                closest_segment = None
                min_time_diff = float('inf')
                
                for segment in route_segments:
                    time_diff = abs((segment['time'] - current_time).total_seconds())
                    if time_diff < min_time_diff:
                        min_time_diff = time_diff
                        closest_segment = segment
                
                # If we found a close segment (within 30 seconds), use its optimized azimuth
                if closest_segment and min_time_diff < 30:
                    az = closest_segment['target_az']
                    logging.debug(f"Using optimized azimuth: {az:.1f}° (segment time diff: {min_time_diff:.1f}s)")
                else:
                    # If no close segment but we have optimization data, only use optimal start azimuth
                    # when satellite is approaching the horizon (-3° to 0°) for pre-positioning
                    optimal_start_az = opt_details.get('optimal_start_az')
                    if (optimal_start_az is not None and optimal_start_az > 360 and 
                        el >= -3 and el < ROTATOR_MIN_ELEVATION):
                        az = optimal_start_az
                        logging.debug(f"Using optimal start azimuth: {az:.1f}° for pre-positioning (el={el:.1f}°)")
                    else:
                        # Only log when elevation changes significantly or when approaching horizon
                        if (not hasattr(self, '_last_logged_el') or 
                            abs(el - self._last_logged_el) > 5 or 
                            (el >= -5 and el < ROTATOR_MIN_ELEVATION)):
                            logging.debug(f"Using raw satellite azimuth: {az:.1f}° (no close segment, el={el:.1f}°)")
                            self._last_logged_el = el
                
                # Only log route segments when they're actually being used or when elevation changes significantly
                if route_segments and (closest_segment and min_time_diff < 30 or 
                                     (not hasattr(self, '_last_logged_el') or abs(el - self._last_logged_el) > 5)):
                    logging.debug(f"Available route segments: {len(route_segments)}")
                    for i, seg in enumerate(route_segments[:3]):  # Show first 3
                        logging.debug(f"  Segment {i}: {seg['time'].strftime('%H:%M:%S')} -> {seg['target_az']:.1f}°")
                    if len(route_segments) > 3:
                        logging.debug(f"  ... and {len(route_segments)-3} more segments")
            
            return az, el
        except Exception as e:
            logging.error(f"Error getting current az/el: {e}")
            return ROTATOR_AZ_PARK, ROTATOR_EL_PARK
    def best_rotator_azimuth(self, current_az, target_az, az_max):
        """
        Returns the best azimuth to command the rotator to, using the optimizer.
        """
        if self.rotator_optimizer:
            distance, optimal_az = self.rotator_optimizer.calculate_rotation_distance(current_az, target_az)
            return optimal_az
        else:
            # Fallback to original simple logic
            current_az = current_az % az_max
            target_az = target_az % az_max
            direct_diff = abs(target_az - current_az)
            overlap_target = target_az
            if az_max > 360:
                # Try using overlap (e.g., 370 instead of 10)
                if target_az < 90 and current_az > 270:
                    overlap_target = target_az + 360
                elif target_az > 270 and current_az < 90:
                    overlap_target = target_az - 360
            overlap_diff = abs(overlap_target - current_az)
            if overlap_diff < direct_diff:
                return overlap_target
            else:
                return target_az

    def rotator_set_position(self, az, el):
        # Defensive: ensure az, el are always float to avoid TypeError
        az = float(az)
        el = float(el)
        if self.rotator:
            # The azimuth should already be optimized from the route optimization
            # Just send it directly to the rotator
            self.rotator.set_position(az, el)
            self.update_rotator_position()

    def rotator_park(self, az_park, el_park):
        # Defensive: ensure arguments are always float to avoid TypeError in rotator.set_position
        az_park = float(az_park)
        el_park = float(el_park)
        if self.rotator:
            self.rotator.park(az_park, el_park)
            self.update_rotator_position()

    def rotator_stop(self):
        if self.rotator:
            self.rotator.stop()
            self.update_rotator_position()

    def park_rotators(self):
        self.rotator_park(ROTATOR_AZ_PARK, ROTATOR_EL_PARK)
        logging.info("Rotator parked.")
        # Update UI status after manual parking
        self.on_rotator_parked(manual_park=True)

    def stop_rotators(self):
        self.rotator_stop()
        logging.info("Rotator stopped.")
        
    def optimize_rotator_route(self):
        """
        Predict satellite pass and optimize rotator route with 450-degree support
        """
        if not (self.rotator_optimizer and self.my_satellite.tledata):
            logging.warning("Cannot optimize rotator route: missing optimizer or satellite data")
            return
        try:
            # Predict the satellite pass
            predictions = self.rotator_optimizer.predict_satellite_pass(
                self.my_satellite.tledata, 
                myloc, 
                duration_minutes=20,  # Look ahead 20 minutes
                interval_seconds=10   # Every 10 seconds
            )
            # Filter for visible portion of pass
            visible_predictions = self.rotator_optimizer.filter_visible_pass(predictions)
            if not visible_predictions:
                logging.info("No visible satellite pass predicted in next 20 minutes")
                self.pass_optimization = None
                self.update_optimization_status(None)
                return
            # --- Log AOS, TCA, LOS ---
            aos_time, aos_az = visible_predictions[0][0], visible_predictions[0][1]
            tca_idx = max(range(len(visible_predictions)), key=lambda i: visible_predictions[i][2])
            tca_time, tca_az, tca_el = visible_predictions[tca_idx]
            los_time, los_az = visible_predictions[-1][0], visible_predictions[-1][1]
            logging.info(f"AOS: {aos_time.strftime('%Y-%m-%d %H:%M:%S')} az={aos_az:.1f}° | TCA: {tca_time.strftime('%Y-%m-%d %H:%M:%S')} az={tca_az:.1f}° el={tca_el:.1f}° | LOS: {los_time.strftime('%Y-%m-%d %H:%M:%S')} az={los_az:.1f}°")
            # Get current rotator position
            current_az = None
            if self.rotator:
                try:
                    current_az, _ = self.rotator.get_position()
                except Exception as e:
                    logging.warning(f"Could not get current rotator position: {e}")
            # Get pre-positioning recommendation
            recommendation = self.rotator_optimizer.get_pre_positioning_recommendation(
                visible_predictions, 
                current_az
            )
            # Store optimization results
            self.pass_optimization = recommendation
            # Log the optimization results
            if recommendation['should_preposition']:
                logging.info(f"🛰 Rotator Optimization: {recommendation['reason']}")
                logging.info(f"📡 Recommended pre-position: {recommendation['recommended_az']:.1f}°")
                # Get details from optimization
                opt_details = recommendation.get('optimization_details', {})
                if opt_details:
                    logging.info(f"📊 Route optimization: {opt_details.get('recommendation', 'N/A')}")
                    savings = opt_details.get('savings', 0)
                    if savings > 0:
                        logging.info(f"💡 Rotation savings: {savings:.1f}°")
                    
                    # Log the first few route segments to show the optimized azimuths
                    route_segments = opt_details.get('route_segments', [])
                    if route_segments:
                        logging.info(f"🛤️ Route segments (first 5):")
                        for i, segment in enumerate(route_segments[:5]):
                            logging.info(f"   {i+1}: {segment['time'].strftime('%H:%M:%S')} az={segment['target_az']:.1f}° el={segment['elevation']:.1f}°")
                        if len(route_segments) > 5:
                            logging.info(f"   ... and {len(route_segments)-5} more segments")
                # Always pre-position if beneficial, even if satellite is already visible
                logging.info(f"⏱️ Pre-positioning rotator (even if pass is in progress)")
                logging.info(f"📡 Sending optimized azimuth to rotator: {recommendation['recommended_az']:.1f}°")
                self.rotator_set_position(recommendation['recommended_az'], ROTATOR_EL_PARK)
                # Immediately update UI to show pre-positioned
                self.update_optimization_status(recommendation)
                return
            else:
                logging.info(f"📡 Rotator optimization: {recommendation['reason']}")
            # Update UI with optimization status (Standard, Error, etc.)
            self.update_optimization_status(recommendation)
        except Exception as e:
            logging.error(f"Error optimizing rotator route: {e}")
            self.pass_optimization = None
            self.update_optimization_status(None)
    
    def check_and_update_optimization_status(self):
        """Check current elevation and update optimization status accordingly"""
        if not ROTATOR_ENABLED or not self.my_satellite.tledata:
            return
            
        try:
            current_elevation = float(sat_ele_calc(self.my_satellite.tledata, myloc))
            
            # Check if we should trigger route prediction at -3° elevation
            if (current_elevation >= -3 and current_elevation < ROTATOR_MIN_ELEVATION and
                (not hasattr(self, 'pass_optimization') or self.pass_optimization is None) and
                hasattr(self, 'last_prediction_time')):
                
                current_time = time.time()
                # Only predict once when crossing -3° threshold (avoid repeated predictions)
                if not hasattr(self, 'prediction_triggered_at_neg3'):
                    logging.info(f"🛰 Satellite at {current_elevation:.1f}° - triggering route prediction before AOS")
                    self.optimize_rotator_route()
                    self.last_prediction_time = current_time
                    self.prediction_triggered_at_neg3 = True
            
            # Clear optimization data when satellite goes well below horizon (for next pass)
            if current_elevation < -10:
                if hasattr(self, 'prediction_triggered_at_neg3'):
                    delattr(self, 'prediction_triggered_at_neg3')
                # Clear old optimization data when satellite is well below horizon
                if hasattr(self, 'pass_optimization') and self.pass_optimization is not None:
                    logging.debug(f"🛰 Satellite at {current_elevation:.1f}° - clearing old optimization data")
                    self.pass_optimization = None
            
            # If elevation is below minimum, show "Parked"
            if current_elevation < ROTATOR_MIN_ELEVATION:
                self.rotator_optimization_val.setText("Parked")
                self.rotator_optimization_val.setStyleSheet("color: #888888")  # Gray
                return
            
            # If elevation is above minimum and we have optimization data, show the optimization status
            if hasattr(self, 'pass_optimization') and self.pass_optimization:
                self.update_optimization_status(self.pass_optimization)
            else:
                # No optimization data but satellite is visible - show "Tracking"
                self.rotator_optimization_val.setText("Tracking")
                self.rotator_optimization_val.setStyleSheet("color: green")
                
        except Exception as e:
            logging.error(f"Error checking optimization status: {e}")

    def force_reoptimize_route(self):
        """Manually trigger route re-optimization"""
        if ROTATOR_ENABLED and self.rotator_optimizer:
            logging.info("🔄 Manual route re-optimization triggered")
            self.last_prediction_time = time.time()
            self.optimize_rotator_route()

    def update_optimization_status(self, recommendation):
        """Update the UI with rotator optimization status"""
        if not ROTATOR_ENABLED:
            return
        if recommendation is None:
            self.rotator_optimization_val.setText("Error")
            self.rotator_optimization_val.setStyleSheet("color: red")
            return
        try:
            # Check current elevation first - if below minimum, show "Parked" regardless of future predictions
            if self.my_satellite.tledata:
                current_elevation = float(sat_ele_calc(self.my_satellite.tledata, myloc))
                if current_elevation < ROTATOR_MIN_ELEVATION:
                    self.rotator_optimization_val.setText("Parked")
                    self.rotator_optimization_val.setStyleSheet("color: #888888")  # Gray
                    return
            
            # If current elevation is above minimum, show optimization status
            if recommendation['should_preposition']:
                opt_details = recommendation.get('optimization_details', {})
                savings = opt_details.get('savings', 0)
                if savings > 0:
                    status_text = f"Optimized (-{savings:.0f}°)"
                    self.rotator_optimization_val.setStyleSheet("color: green")
                else:
                    status_text = "Pre-positioned"
                    self.rotator_optimization_val.setStyleSheet("color: #FFA500")  # Orange
            else:
                status_text = "Optimal"
                self.rotator_optimization_val.setStyleSheet("color: green")
            self.rotator_optimization_val.setText(status_text)
        except Exception as e:
            logging.error(f"Error updating optimization status: {e}")
            self.rotator_optimization_val.setText("Error")
            self.rotator_optimization_val.setStyleSheet("color: red")

    def on_rotator_parked(self, manual_park=False):
        """Callback when rotator parks - update UI status"""
        if ROTATOR_ENABLED:
            # If manually parked (stop button), always show "Parked"
            if manual_park:
                self.rotator_optimization_val.setText("Parked")
                self.rotator_optimization_val.setStyleSheet("color: #888888")  # Gray
                return
            
            # Use the new method to check and update status based on current conditions
            self.check_and_update_optimization_status()
        else:
            self.rotator_optimization_val.setText("Parked")
            self.rotator_optimization_val.setStyleSheet("color: #888888")  # Gray

    def start_rotator_thread(self):
        if ROTATOR_ENABLED and self.rotator and not self.rotator_thread:
            self.rotator_thread = rotator.RotatorThread(
                self.rotator,
                self.get_current_az_el,
                ROTATOR_MIN_ELEVATION,
                ROTATOR_AZ_PARK,
                ROTATOR_EL_PARK,
                on_park_callback=self.on_rotator_parked,
                best_az_func=self.best_rotator_azimuth,
                az_max=ROTATOR_AZ_MAX
            )
            self.rotator_thread.daemon = True
            self.rotator_thread.start()
            logging.debug("Rotator thread started.")
            self.update_rotator_position()
    def stop_rotator_thread(self):
        if self.rotator_thread:
            self.rotator_thread.stop()
            self.rotator_thread.join(timeout=2)
            self.rotator_thread = None
            logging.debug("Rotator thread stopped.")
    def closeEvent(self, event):
        # Ensure rotator is stopped and parked on exit
        if ROTATOR_ENABLED:
            self.stop_rotator_thread()
            self.park_rotators()
            if self.rotator:
                self.rotator.close()
            self.stop_rotator_position_worker()
            
        # Stop audio monitoring if active
        if hasattr(self, 'audio_monitor_active') and self.audio_monitor_active:
            if hasattr(self, 'audio_monitor_stream') and self.audio_monitor_stream:
                try:
                    self.audio_monitor_stream.stop()
                    self.audio_monitor_stream.close()
                    self.audio_monitor_stream = None
                    self.audio_monitor_active = False
                except Exception as e:
                    logging.error(f"Error stopping audio monitor on exit: {e}")
            
        # Defensive: clear threadpool to avoid QRunnable errors
        try:
            self.threadpool.clear()
        except Exception as e:
            logging.error(f"Error clearing threadpool: {e}")
        event.accept()

    def update_rotator_position(self):
        if self.rotator:
            try:
                # Use cached position to avoid blocking the main thread
                az, el = self.rotator.get_position(use_cache=True)
                if az is not None and el is not None:
                    self.rotator_az_val.setText(f"{az}°")
                    self.rotator_el_val.setText(f"{el}°")
                else:
                    self.rotator_az_val.setText("Pos. error")
                    self.rotator_el_val.setText("Pos. error")
            except Exception as e:
                logging.error(f"Error updating rotator position: {e}")
                self.rotator_az_val.setText("error")
                self.rotator_el_val.setText("error")
        elif ROTATOR_ENABLED:
            self.rotator_az_val.setText("")
            self.rotator_el_val.setText("")

    def start_rotator_position_worker(self):
        if self.rotator:
            # Use configurable poll interval, with intelligent adjustment based on tracking state
            base_interval = ROTATOR_POSITION_POLL_INTERVAL
            if TRACKING_ACTIVE:
                # Poll more frequently when actively tracking
                poll_interval = min(base_interval, 2.0)
            else:
                # Poll less frequently when not tracking
                poll_interval = max(base_interval, 10.0)
            
            self.rotator_position_worker = RotatorPositionWorker(self.rotator, poll_interval=poll_interval)
            self.rotator_position_worker.signals.position.connect(self.handle_rotator_position_update)
            QThreadPool.globalInstance().start(self.rotator_position_worker)

    def stop_rotator_position_worker(self):
        # Defensive: safely stop worker and avoid double-deletion
        if hasattr(self, 'rotator_position_worker') and self.rotator_position_worker:
            try:
                self.rotator_position_worker.stop()
            except Exception as e:
                logging.error(f"Error stopping rotator position worker: {e}")
            self.rotator_position_worker = None
            
    def restart_rotator_position_worker(self):
        """Restart the rotator position worker with appropriate polling interval"""
        if ROTATOR_ENABLED and self.rotator:
            # Stop existing worker
            self.stop_rotator_position_worker()
            
            # Calculate appropriate poll interval based on tracking state
            base_interval = ROTATOR_POSITION_POLL_INTERVAL
            if TRACKING_ACTIVE:
                # Poll more frequently when actively tracking
                poll_interval = min(base_interval, 2.0)
                logging.debug(f"Starting rotator position worker with fast polling: {poll_interval}s (tracking active)")
            else:
                # Poll less frequently when not tracking
                poll_interval = max(base_interval, 10.0)
                logging.debug(f"Starting rotator position worker with slow polling: {poll_interval}s (not tracking)")
            
            # Start new worker
            self.rotator_position_worker = RotatorPositionWorker(self.rotator, poll_interval=poll_interval)
            self.rotator_position_worker.signals.position.connect(self.handle_rotator_position_update)
            QThreadPool.globalInstance().start(self.rotator_position_worker)
            
    def toggle_audio_monitoring(self):
        """Start or stop audio level monitoring"""
        if hasattr(self, 'audio_monitor_active') and self.audio_monitor_active:
            # Stop monitoring
            self.audio_monitor_active = False
            self.passrec_monitor_button.setText("Start Monitoring")
            if hasattr(self, 'audio_monitor_stream') and self.audio_monitor_stream:
                self.audio_monitor_stream.stop()
                self.audio_monitor_stream.close()
                self.audio_monitor_stream = None
        else:
            # Start monitoring
            self.audio_monitor_active = True
            self.passrec_monitor_button.setText("Stop Monitoring")
            
            # Get the selected device using the same logic as recording
            device = None
            selected_idx = self.passrec_soundcard_dropdown.currentIndex()
            if selected_idx >= 0:
                device_name = self.passrec_soundcard_dropdown.itemData(selected_idx, Qt.UserRole + 1)
                
                # Try to find device by name first (more reliable)
                if device_name:
                    devices = sd.query_devices()
                    for i, dev in enumerate(devices):
                        if dev['name'] == device_name and dev['max_input_channels'] > 0:
                            device = i
                            logging.info(f"Found monitoring device by name: {device_name} (index {i})")
                            break
                    
                    # If not found by exact name, try partial match
                    if device is None:
                        for i, dev in enumerate(devices):
                            if device_name in dev['name'] and dev['max_input_channels'] > 0:
                                device = i
                                logging.info(f"Found similar monitoring device: {dev['name']} (index {i})")
                                break
                
                # If not found by name, use the index
                if device is None:
                    device_idx = self.passrec_soundcard_dropdown.itemData(selected_idx)
                    if device_idx is not None:
                        try:
                            device = int(device_idx)
                            logging.info(f"Using monitoring device by index: {device}")
                        except (ValueError, TypeError):
                            logging.warning(f"Could not use device index: {device_idx}")
            
            if device is None:
                logging.info("Using default audio input device for monitoring")
                try:
                    device = sd.default.device[0]  # Default input device
                except Exception as e:
                    logging.error(f"Error getting default device: {e}")
            
            # Create callback for audio processing with debug logging
            def audio_callback(indata, frames, time, status):
                # Only log errors other than overflow 
                if status and status.input_overflow:
                    # Skip logging for input overflow as it's too verbose
                    pass
                elif status:
                    logging.warning(f"Audio monitoring status: {status}")
                
                try:
                    # Calculate RMS amplitude (volume level)
                    level = np.linalg.norm(indata)
                    
                    # Log levels occasionally to help debug
                    if frames % 100 == 0 and logging.getLogger().isEnabledFor(logging.DEBUG):
                        logging.debug(f"Monitor audio level: {level:.4f}")
                    
                    # Scale to percentage (0-100)
                    # Apply a logarithmic scaling to make low levels more visible
                    if level > 0:
                        log_level = 20 * np.log10(level) + 90  # Convert to dB scale (normalized)
                        percentage = min(100, max(0, int(log_level)))
                    else:
                        percentage = 0
                    
                    # Update UI in thread-safe way
                    QMetaObject.invokeMethod(self.passrec_level_meter, "setValue", 
                                            Qt.QueuedConnection, Q_ARG(int, percentage))
                except Exception as e:
                    # Catch any errors to prevent audio stream from crashing
                    logging.error(f"Error in audio monitoring callback: {e}")
            
            # Start the audio stream
            try:
                logging.info(f"Starting audio level monitoring with device: {device}")
                self.audio_monitor_stream = sd.InputStream(
                    device=device,
                    channels=1,
                    callback=audio_callback,
                    blocksize=8192,  # Increased from 1024 to 8192 for better stability
                    samplerate=44100
                )
                self.audio_monitor_stream.start()
                
                # Update UI to confirm monitoring is active
                self.passrec_level_meter.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #3A3939;
                        border-radius: 4px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                                   stop:0 #00FF00, stop:0.6 #FFFF00, stop:0.8 #FF8800, stop:1 #FF0000);
                    }
                """)
            except Exception as e:
                logging.error(f"Error starting audio monitoring: {e}")
                self.audio_monitor_active = False
                self.passrec_monitor_button.setText("Start Monitoring")

    @Slot(object, object)
    def handle_rotator_position_update(self, az, el):
        if az is not None and el is not None:
            self.rotator_az_val.setText(f"{az}°")
            self.rotator_el_val.setText(f"{el}°")
        else:
            self.rotator_az_val.setText("Pos. error")
            self.rotator_el_val.setText("Pos. error")

    def update_passrecorder_status(self):
        if PASS_RECORDER_ENABLED:
            if self.pass_recorder.is_recording():
                self.recording_status_label.setText("✔")
                self.recording_status_label.setStyleSheet("QLabel{font-size: 12pt; font-weight: bold; color: green}")
            else:
                self.recording_status_label.setText("✘")
                self.recording_status_label.setStyleSheet("QLabel{font-size: 12pt; font-weight: bold; color: red}")
    def on_satellite_update(self, elevation, satname):
        try:
            # Ensure elevation is a float
            elev_float = float(elevation)
            
            # Call the pass recorder without logging every elevation update
            self.pass_recorder.update_elevation(elev_float, satname)
            self.update_passrecorder_status()
        except (ValueError, TypeError) as e:
            logging.error(f"Error converting elevation '{elevation}' to float: {e}")
            # Try to get a valid elevation directly from satellite calculations
            try:
                # Get current elevation directly
                current_elevation = float(sat_ele_calc(self.my_satellite.tledata, myloc))
                logging.info(f"Using fallback elevation={current_elevation}")
                self.pass_recorder.update_elevation(current_elevation, satname)
                self.update_passrecorder_status()
            except Exception as e2:
                logging.error(f"Fallback elevation calculation also failed: {e2}")

    def toggle_gps_qth(self, enabled):
        if enabled:
            self.gps_status_label.setText("GPS Status: Starting...")
            self.start_gps_reader()
            self.gps_lock_button.setEnabled(True)
        else:
            self.stop_gps_reader()
            self.gps_lock_button.setEnabled(False)

    def lock_gps_position(self):
        self.stop_gps_reader()
        # Do NOT uncheck the checkbox; leave GPS QTH enabled until restart or user action
        self.gps_lock_button.setEnabled(False)
        self.gps_status_label.setText("GPS Status: Locked at last fix")

    def start_gps_reader(self):
        port = self.gps_serialport_val.currentText()
        if not port:
            self.gps_status_label.setText("GPS Status: No port selected")
            return
        if self.gps_reader:
            self.stop_gps_reader()
        try:
            self.gps_reader = GPSReader(port)
            self.gps_reader.position_update.connect(self.on_gps_position_update)
            self.gps_reader.status_update.connect(self.handle_gps_status_update)
            self.gps_reader.start()
            self.gps_last_port = port
            self.gps_status_label.setText(f"GPS Status: Connecting to {port}")
            self.gps_lock_button.setEnabled(True)
        except Exception as e:
            self.gps_status_label.setText(f"GPS Status: Could not open port: {e}")
            self.gps_enable_checkbox.setChecked(False)

    def stop_gps_reader(self):
        if self.gps_reader:
            self.gps_reader.stop()
            self.gps_reader.wait()
            self.gps_reader = None
        self.gps_status_label.setText("GPS Status: Not connected")
        self.gps_lock_button.setEnabled(False)

    def handle_gps_status_update(self, status):
        # Handle disconnects and no fix
        if "Error" in status or "Disconnected" in status:
            self.gps_status_label.setText(f"GPS Status: {status}")
            self.gps_lock_button.setEnabled(False)
        elif "No fix" in status:
            self.gps_status_label.setText(f"GPS Status: {status}")
            self.gps_lock_button.setEnabled(False)
        else:
            self.gps_status_label.setText(f"GPS Status: {status}")
            self.gps_lock_button.setEnabled(True)

    def on_gps_position_update(self, lat, lon, alt):
        # Update QTH fields and config
        self.qth_settings_lat_edit.setText(str(lat))
        self.qth_settings_long_edit.setText(str(lon))
        self.qth_settings_alt_edit.setText(str(alt))
        configur['qth']['latitude'] = str(lat)
        configur['qth']['longitude'] = str(lon)
        configur['qth']['altitude'] = str(alt)
        with open('config.ini', 'w') as configfile:
            configur.write(configfile)
        self.gps_status_label.setText("GPS Status: Fix received")
        self.gps_lock_button.setEnabled(True)

class WorkerSignals(QObject):
    finished = Signal()
    error = Signal(tuple)
    result = Signal(object)
    progress = Signal(int)
    position = Signal(object, object)  # az, el

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

    @Slot()
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

class RotatorPositionWorker(QRunnable):
    def __init__(self, rotator, poll_interval=5.0):  # Increased from 2.0 to 5.0 seconds
        super().__init__()
        self.rotator = rotator
        self.poll_interval = poll_interval
        self.signals = WorkerSignals()
        self._running = True

    def stop(self):
        self._running = False

    @Slot()
    def run(self):
        while self._running:
            try:
                az, el = self.rotator.get_position(use_cache=True)  # Use cache to reduce serial calls
                self.signals.position.emit(az, el)
            except Exception as e:
                self.signals.position.emit(None, None)
            time.sleep(self.poll_interval)

class AudioLevelMeter(QProgressBar):
    """Custom progress bar for displaying audio input levels"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimum(0)
        self.setMaximum(100)
        self.setValue(0)
        self.setTextVisible(True)
        self.setFormat("%v%")
        # Use a gradient from green to yellow to red
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3A3939;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00FF00, stop:0.5 #FFFF00, stop:1 #FF0000);
            }
        """)

## Starts here:
if RADIO != "9700" and RADIO != "705" and RADIO != "818" and RADIO != "910":
    logging.critical("***  Icom radio not supported: {badmodel}".format(badmodel=RADIO))
    sys.exit()


app = QApplication(sys.argv)
window = MainWindow()
apply_stylesheet(app, theme="dark_lightgreen.xml")
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
        QDoubleSpinBox {
            color: white;
        }
        QLineEdit {
            color: white;
        }
    """
app.setStyleSheet(app.styleSheet()+tooltip_stylesheet)
window.show()
app.exec()


from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit
from configparser import ConfigParser
import os

flask_app = Flask(__name__)
socketio = SocketIO(flask_app, cors_allowed_origins="*")

main_window = None

def register_window(window):
    global main_window
    main_window = window

@flask_app.route('/')
def index():
    return send_file('web_api_client.html')

@socketio.on('connect')
def handle_connect():
    if main_window:
        # Get current status when client connects
        status = {
            'tracking': main_window.Stopbutton.isEnabled(),
            'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
            'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None,
            'rx_offset': main_window.rxoffsetbox.value() if hasattr(main_window, 'rxoffsetbox') else 0
        }
        emit('status', status)

@socketio.on('get_status')
def handle_get_status():
    if main_window:
        # Return current application status
        status = {
            'tracking': main_window.Stopbutton.isEnabled(),
            'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
            'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None,
            'rx_offset': main_window.rxoffsetbox.value() if hasattr(main_window, 'rxoffsetbox') else 0
        }
        
        # Add more detailed satellite information if available
        if hasattr(main_window, 'my_satellite') and main_window.my_satellite.name:
            sat = main_window.my_satellite
            status.update({
                'satellite_info': {
                    'name': sat.name,
                    'downlink_freq': sat.F if hasattr(sat, 'F') else None,
                    'uplink_freq': sat.I if hasattr(sat, 'I') else None,
                    'downlink_mode': sat.downmode if hasattr(sat, 'downmode') else None,
                    'uplink_mode': sat.upmode if hasattr(sat, 'upmode') else None,
                    'tle_age': sat.tle_age if hasattr(sat, 'tle_age') else None
                }
            })
            
            # Add elevation and azimuth if available
            if hasattr(main_window, 'log_sat_status_ele_val') and hasattr(main_window, 'log_sat_status_azi_val'):
                status['satellite_position'] = {
                    'elevation': main_window.log_sat_status_ele_val.text(),
                    'azimuth': main_window.log_sat_status_azi_val.text()
                }
            
            # Add doppler info
            if hasattr(main_window, 'rxdoppler_val') and hasattr(main_window, 'txdoppler_val'):
                status['doppler'] = {
                    'downlink': main_window.rxdoppler_val.text(),
                    'uplink': main_window.txdoppler_val.text()
                }
        
        emit('status', status)

@socketio.on('start_tracking')
def handle_start_tracking():
    if main_window:
        main_window.init_worker()
        emit('status', {'tracking': True}, broadcast=True)

@socketio.on('stop_tracking')
def handle_stop_tracking():
    if main_window:
        main_window.the_stop_button_was_clicked()
        emit('status', {'tracking': False}, broadcast=True)

@socketio.on('select_satellite')
def handle_select_satellite(data):
    if main_window:
        sat_name = data.get('satellite')
        # Stop tracking if active
        was_tracking = main_window.Stopbutton.isEnabled()
        if was_tracking:
            main_window.the_stop_button_was_clicked()
        main_window.sat_changed(sat_name)
        # Start tracking again if it was active
        if was_tracking:
            main_window.init_worker()
        emit('status', {'satellite': sat_name}, broadcast=True)

@socketio.on('select_transponder')
def handle_select_transponder(data):
    if main_window:
        tpx_name = data.get('transponder')
        main_window.tpx_changed(tpx_name)
        emit('status', {'transponder': tpx_name}, broadcast=True)

@socketio.on('set_subtone')
def handle_set_subtone(data):
    if main_window:
        tone = data.get('subtone')
        main_window.tone_changed(tone)
        emit('status', {'subtone': tone}, broadcast=True)

@socketio.on('set_rx_offset')
def handle_set_rx_offset(data):
    if main_window:
        try:
            offset = int(data.get('offset'))
            main_window.rxoffsetbox.setValue(offset)
            emit('status', {'rx_offset': offset}, broadcast=True)
        except Exception as e:
            emit('status', {'error': str(e)})

def run_socketio():
    try:
        # Try to read port from config file
        config = ConfigParser()
        config.read('config.ini')
        port = config.getint('web_api', 'port', fallback=5000)
        debug = config.getboolean('web_api', 'debug', fallback=False)
    except:
        # Default values if config can't be read
        port = 5000
        debug = False
    
    # Start the Flask SocketIO server
    socketio.run(flask_app, port=port, debug=debug, use_reloader=False) 
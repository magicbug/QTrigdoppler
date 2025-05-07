from flask import Flask, request
from flask_socketio import SocketIO, emit

flask_app = Flask(__name__)
socketio = SocketIO(flask_app, cors_allowed_origins="*")

main_window = None

def register_window(window):
    global main_window
    main_window = window

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
    socketio.run(flask_app, port=5000, debug=False, use_reloader=False) 
from flask import Flask, request, send_file
from flask_socketio import SocketIO, emit
from configparser import ConfigParser
import os
import sys
import threading
import time

flask_app = Flask(__name__)
socketio = SocketIO(flask_app, cors_allowed_origins="*")

main_window = None
status_broadcast_thread = None
should_run_status_broadcast = False

# Satellite list cache
satellite_list_cache = None
satellite_list_file = None

# Add a helper function for thread-safe execution of UI operations
def run_on_ui_thread(func, *args, **kwargs):
    """Run the given function on the UI thread safely"""
    # Import here to avoid circular imports
    from PySide6.QtCore import QMetaObject, Qt, QObject
    
    # Check if we're already on the main thread (by checking thread affinity)
    if hasattr(main_window, 'thread') and threading.current_thread() == main_window.thread():
        # If we're already on the main thread, just call the function directly
        return func(*args, **kwargs)
    else:
        # We need a simpler approach that doesn't directly pass the function
        # Using a single-shot timer is a reliable way to execute code on the main thread
        from PySide6.QtCore import QTimer
        
        # Create a mutable container for the result
        result_container = {'result': None, 'completed': False, 'error': None}
        
        # Define a slot that will be called on the main thread
        def callback():
            try:
                result_container['result'] = func(*args, **kwargs)
                result_container['completed'] = True
            except Exception as e:
                result_container['error'] = str(e)
                result_container['completed'] = True
                print(f"Error in UI thread callback: {e}")
                import traceback
                traceback.print_exc()
        
        # Use a single-shot timer to run on the main thread
        timer = QTimer()
        timer.timeout.connect(callback)
        timer.setSingleShot(True)
        timer.start(0)  # 0 ms = run as soon as possible
        
        # Wait for a reasonable time for the operation to complete
        # This is a simple approach - in a production environment, you might want
        # a more sophisticated approach with proper waiting and timeout mechanisms
        max_wait = 10  # Maximum wait time in seconds
        wait_interval = 0.1  # Check interval in seconds
        waited = 0
        
        while not result_container['completed'] and waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
        
        if result_container['error']:
            raise Exception(f"Error in UI thread: {result_container['error']}")
        
        if not result_container['completed']:
            print("Warning: UI thread operation timed out")
            
        return result_container['result']

def register_window(window):
    global main_window
    main_window = window
    load_satellite_list()  # Load satellite list at startup
    # Start periodic status broadcast
    start_status_broadcast_thread()

def status_broadcast_worker():
    """Background worker that periodically broadcasts status to all clients"""
    global should_run_status_broadcast
    should_run_status_broadcast = True
    
    while should_run_status_broadcast:
        try:
            if main_window:
                # Determine broadcast interval based on tracking status
                tracking_active = False
                try:
                    tracking_active = main_window.Stopbutton.isEnabled()
                except AttributeError:
                    pass
                
                # Send the status broadcast
                broadcast_full_status()
                
                # Adjust sleep interval based on tracking status:
                # - When tracking: update every 15 seconds
                # - When not tracking: update much less frequently (every 2 minutes)
                if tracking_active:
                    time.sleep(15)  # 15 seconds when actively tracking
                else:
                    time.sleep(120)  # 2 minutes when idle
        except Exception as e:
            print(f"Error in status broadcast thread: {e}")
            time.sleep(60)  # On error, wait a minute before trying again

def start_status_broadcast_thread():
    """Start a background thread that broadcasts status updates"""
    global status_broadcast_thread, should_run_status_broadcast
    
    # Stop any existing thread
    stop_status_broadcast_thread()
    
    # Start new thread
    should_run_status_broadcast = True
    status_broadcast_thread = threading.Thread(target=status_broadcast_worker, daemon=True)
    status_broadcast_thread.start()
    print("Started status broadcast thread")

def stop_status_broadcast_thread():
    """Stop the background status broadcast thread"""
    global status_broadcast_thread, should_run_status_broadcast
    
    if status_broadcast_thread and status_broadcast_thread.is_alive():
        should_run_status_broadcast = False
        status_broadcast_thread.join(timeout=1.0)
        print("Stopped status broadcast thread")

def safe_emit(event, data):
    """Safely emit events to all clients with error handling"""
    try:
        # Try the standard emit method first
        socketio.emit(event, data)
    except Exception as e1:
        # If it fails, try alternatives
        try:
            print(f"Standard emit failed: {e1}. Trying namespace emit...")
            # Try emitting to the default namespace
            socketio.emit(event, data, namespace='/')
        except Exception as e2:
            print(f"Namespace emit failed: {e2}. Trying direct emit...")
            try:
                # If all else fails, send to all connected clients
                for sid in socketio.server.sockets:
                    socketio.emit(event, data, room=sid)
            except Exception as e3:
                print(f"Direct emit failed: {e3}. Unable to broadcast event: {event}")

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
        
        # Add subtone if available
        if hasattr(main_window, 'combo3'):
            status['subtone'] = main_window.combo3.currentText()
            
        # Use socket directly since this is already in a request context
        emit('status', status)
        
        # Try to send the satellite list
        try:
            handle_get_satellite_list()
        except Exception as e:
            import traceback
            print(f"Error in handle_connect when getting satellite list: {str(e)}\n{traceback.format_exc()}")
            
            # Fallback: try to read directly from doppler.sqf
            try:
                # Try multiple ways to get the SQF file path
                sqffile = None
                
                # Method 1: Direct attribute
                if hasattr(main_window, 'SQFILE'):
                    sqffile = main_window.SQFILE
                    print(f"Fallback: Using SQFILE attribute: {sqffile}")
                
                # Method 2: From global scope of the module
                elif hasattr(main_window, '__module__') and main_window.__module__ in sys.modules:
                    module = sys.modules[main_window.__module__]
                    if hasattr(module, 'SQFILE'):
                        sqffile = module.SQFILE
                        print(f"Fallback: Using SQFILE from module globals: {sqffile}")
                
                # Method 3: From config
                if not sqffile:
                    try:
                        import configparser
                        config = configparser.ConfigParser()
                        config.read('config.ini')
                        sqffile = config.get('satellite', 'sqffile')
                        print(f"Fallback: Using SQFILE from config.ini: {sqffile}")
                    except Exception as config_e:
                        print(f"Fallback: Failed to get sqffile from config: {config_e}")
                
                # Method 4: Default fallback
                if not sqffile:
                    sqffile = 'doppler.sqf'
                    print(f"Fallback: Using default sqffile: {sqffile}")
                
                satlist = []
                with open(sqffile, 'r') as h:
                    sqfdata = h.readlines() 
                    for line in sqfdata:
                        # Skip comment lines
                        if line.strip().startswith(';'):
                            continue
                            
                        if ',' in line:
                            newitem = str(line.split(",")[0].strip())
                            if newitem:
                                satlist.append(newitem)
                
                # Remove duplicates while preserving order
                unique_satlist = []
                for sat in satlist:
                    if sat not in unique_satlist:
                        unique_satlist.append(sat)
                
                # Return the current selection as well
                current_sat = None
                if hasattr(main_window, 'my_satellite'):
                    current_sat = main_window.my_satellite.name
                
                # Use socket directly since this is already in a request context
                emit('satellite_list', {
                    'satellites': unique_satlist,
                    'current': current_sat
                })
                print(f"Successfully loaded {len(unique_satlist)} satellites using fallback method")
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                # Use socket directly since this is already in a request context
                emit('status', {'error': 'Could not load satellite list. Please check the server logs.'})

@socketio.on('get_status')
def handle_get_status():
    if main_window:
        status = {
            'tracking': main_window.Stopbutton.isEnabled(),
            'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
            'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None,
            'rx_offset': main_window.rxoffsetbox.value() if hasattr(main_window, 'rxoffsetbox') else 0
        }
        if hasattr(main_window, 'combo3'):
            status['subtone'] = main_window.combo3.currentText()
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
            if hasattr(main_window, 'log_sat_status_ele_val') and hasattr(main_window, 'log_sat_status_azi_val'):
                status['satellite_position'] = {
                    'elevation': main_window.log_sat_status_ele_val.text(),
                    'azimuth': main_window.log_sat_status_azi_val.text()
                }
            if hasattr(main_window, 'rxdoppler_val') and hasattr(main_window, 'txdoppler_val'):
                status['doppler'] = {
                    'downlink': main_window.rxdoppler_val.text(),
                    'uplink': main_window.txdoppler_val.text()
                }
        # Add rotator enabled flag
        rotator_enabled = getattr(main_window, 'ROTATOR_ENABLED', False)
        status['rotator_enabled'] = rotator_enabled
        # Add rotator info
        if rotator_enabled and hasattr(main_window, 'rotator_az_label') and hasattr(main_window, 'rotator_el_label'):
            def strip_prefix(text, prefix):
                if text.startswith(prefix):
                    return text[len(prefix):].strip()
                return text
            az = main_window.rotator_az_label.text()
            el = main_window.rotator_el_label.text()
            az = strip_prefix(az, 'Azimuth:')
            el = strip_prefix(el, 'Elevation:')
            status['rotator'] = {
                'azimuth': az,
                'elevation': el
            }
        elif not rotator_enabled:
            status['rotator'] = {
                'azimuth': 'Disabled',
                'elevation': 'Disabled'
            }
        emit('status', status)

@socketio.on('start_tracking')
def handle_start_tracking():
    if main_window:
        main_window.web_api_proxy.start_tracking.emit()
        emit('status', {
            'tracking': True,
            'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
            'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None
        })

@socketio.on('stop_tracking')
def handle_stop_tracking():
    if main_window:
        main_window.web_api_proxy.stop_tracking.emit()
        emit('status', {
            'tracking': False,
            'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
            'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None
        })

@socketio.on('select_satellite')
def handle_select_satellite(data):
    if main_window:
        try:
            sat_name = data.get('satellite')
            if not sat_name:
                emit('status', {'error': 'No satellite specified'})
                return
            # Emit signal to main thread
            main_window.web_api_proxy.select_satellite.emit(sat_name)
            emit('status', {'satellite': sat_name})
            handle_get_transponder_list({'satellite': sat_name})
            try:
                broadcast_full_status()
            except Exception as e:
                print(f"Error broadcasting full status after satellite change: {e}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error selecting satellite: {str(e)}\n{error_details}")
            emit('status', {'error': f'Error selecting satellite: {str(e)}'})

@socketio.on('select_transponder')
def handle_select_transponder(data):
    if main_window:
        try:
            tpx_name = data.get('transponder')
            if not tpx_name:
                emit('status', {'error': 'No transponder specified'})
                return
            main_window.web_api_proxy.select_transponder.emit(tpx_name)
            emit('status', {'transponder': tpx_name})
            try:
                broadcast_full_status()
            except Exception as e:
                print(f"Error broadcasting full status after transponder change: {e}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error selecting transponder: {str(e)}\n{error_details}")
            emit('status', {'error': f'Error selecting transponder: {str(e)}'})

@socketio.on('set_subtone')
def handle_set_subtone(data):
    if main_window:
        try:
            tone = data.get('subtone')
            if tone is None:
                emit('status', {'error': 'No subtone specified'})
                return
            main_window.web_api_proxy.set_subtone.emit(tone)
            emit('status', {'subtone': tone})
            try:
                broadcast_full_status()
            except Exception as e:
                print(f"Error broadcasting full status after subtone change: {e}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error setting subtone: {str(e)}\n{error_details}")
            emit('status', {'error': f'Error setting subtone: {str(e)}'})

@socketio.on('set_rx_offset')
def handle_set_rx_offset(data):
    if main_window:
        try:
            offset_str = data.get('offset')
            if offset_str is None:
                emit('status', {'error': 'No RX offset specified'})
                return
            try:
                offset = int(offset_str)
            except (ValueError, TypeError):
                emit('status', {'error': f'Invalid RX offset value: {offset_str}. Must be an integer.'})
                return
            main_window.web_api_proxy.set_rx_offset.emit(offset)
            emit('status', {'rx_offset': offset})
            try:
                broadcast_full_status()
            except Exception as e:
                print(f"Error broadcasting full status after RX offset change: {e}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error setting RX offset: {str(e)}\n{error_details}")
            emit('status', {'error': f'Error setting RX offset: {str(e)}'})

@socketio.on('get_satellite_list')
def handle_get_satellite_list():
    if main_window:
        try:
            # Use the cached satellite list
            unique_satlist = satellite_list_cache if satellite_list_cache is not None else []
            current_sat = main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None
            # Check if we're in a request context
            try:
                from flask import request
                if request:
                    emit('satellite_list', {
                        'satellites': unique_satlist,
                        'current': current_sat
                    })
                    print(f"Emitted satellite list in request context")
            except (RuntimeError, ImportError):
                safe_emit('satellite_list', {
                    'satellites': unique_satlist,
                    'current': current_sat
                })
                print(f"Emitted satellite list using safe_emit")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error getting satellite list: {str(e)}\n{error_details}")
            try:
                from flask import request
                if request:
                    emit('status', {'error': f'Error getting satellite list: {str(e)}'})
            except (RuntimeError, ImportError):
                safe_emit('status', {'error': f'Error getting satellite list: {str(e)}'})

@socketio.on('get_transponder_list')
def handle_get_transponder_list(data):
    if main_window:
        try:
            satellite_name = data.get('satellite')
            if not satellite_name:
                try:
                    # First try using the request-specific emit
                    from flask import request
                    if request:
                        emit('status', {'error': 'No satellite specified for transponder list'})
                except (RuntimeError, ImportError):
                    safe_emit('status', {'error': 'No satellite specified for transponder list'})
                return
                
            # Try multiple ways to get the SQF file path
            sqffile = None
            
            # Method 1: Direct attribute
            if hasattr(main_window, 'SQFILE'):
                sqffile = main_window.SQFILE
                print(f"Using SQFILE attribute: {sqffile}")
            
            # Method 2: From global scope of the module
            elif hasattr(main_window, '__module__') and main_window.__module__ in sys.modules:
                module = sys.modules[main_window.__module__]
                if hasattr(module, 'SQFILE'):
                    sqffile = module.SQFILE
                    print(f"Using SQFILE from module globals: {sqffile}")
            
            # Method 3: From config
            if not sqffile:
                try:
                    import configparser
                    config = configparser.ConfigParser()
                    config.read('config.ini')
                    sqffile = config.get('satellite', 'sqffile')
                    print(f"Using SQFILE from config.ini: {sqffile}")
                except Exception as e:
                    print(f"Failed to get sqffile from config: {e}")
              # Method 4: Default fallback
            if not sqffile:
                sqffile = 'doppler.sqf'
                print(f"Using default sqffile: {sqffile}")
                    
            tpxlist = []
            with open(sqffile, 'r') as h:
                sqfdata = h.readlines()
                for line in sqfdata:
                    # Skip comment lines
                    if line.strip().startswith(';'):
                        continue
                        
                    parts = line.strip().split(',')
                    if len(parts) > 8 and parts[0].strip() == satellite_name:
                        tpx_name = parts[8].strip()
                        if tpx_name:
                            tpxlist.append(tpx_name)
            
            # Remove duplicates while preserving order
            unique_tpxlist = []
            for tpx in tpxlist:
                if tpx not in unique_tpxlist:
                    unique_tpxlist.append(tpx)
            
            # Return the current selection as well
            current_tpx = getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None
            
            # Check if we're in a request context
            try:
                # First try using the request-specific emit
                from flask import request
                if request:
                    # Use socket directly since this is already in a request context
                    emit('transponder_list', {
                        'transponders': unique_tpxlist,
                        'current': current_tpx
                    })
                    print(f"Emitted transponder list in request context")
            except (RuntimeError, ImportError):
                # If not in a request context, use the safe_emit function
                safe_emit('transponder_list', {
                    'transponders': unique_tpxlist,
                    'current': current_tpx
                })
                print(f"Emitted transponder list using safe_emit")
                
            print(f"Successfully loaded {len(unique_tpxlist)} transponders for {satellite_name}")
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error getting transponder list: {str(e)}\n{error_details}")
            try:
                # First try using the request-specific emit
                from flask import request
                if request:
                    # Use socket directly since this is already in a request context
                    emit('status', {'error': f'Error getting transponder list: {str(e)}'})
            except (RuntimeError, ImportError):
                # If not in a request context, use the safe_emit function
                safe_emit('status', {'error': f'Error getting transponder list: {str(e)}'})

@socketio.on('debug_main_window')
def handle_debug_main_window():
    """Debug endpoint to inspect main_window attributes"""
    if main_window:
        try:
            # Get basic attributes
            attrs = []
            for attr in dir(main_window):
                if not attr.startswith('__'):
                    attrs.append(attr)
            
            # Check specific attributes we're using
            sqf_exists = hasattr(main_window, 'SQFILE')
            sqf_value = getattr(main_window, 'SQFILE', 'not found') if sqf_exists else 'not found'
            
            configur_exists = False
            configur_value = 'not found'
            if hasattr(main_window, 'configur'):
                configur_exists = True
                try:
                    configur_value = str(main_window.configur.sections())
                except:
                    configur_value = 'exists but cannot be stringified'
            
            # Check for subtone combo box
            subtone_exists = hasattr(main_window, 'combo3')
            subtone_value = 'not found'
            if subtone_exists:
                try:
                    subtone_value = main_window.combo3.currentText()
                except:
                    subtone_value = 'exists but cannot get value'
            
            # Use socket directly since this is already in a request context
            emit('debug_info', {
                'attributes': attrs,
                'has_SQFILE': sqf_exists,
                'SQFILE_value': sqf_value,
                'has_configur': configur_exists,
                'configur_value': configur_value,
                'has_subtone_combo': subtone_exists,
                'subtone_value': subtone_value
            })
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error in debug handler: {str(e)}\n{error_details}")
            # Use socket directly since this is already in a request context
            emit('status', {'error': f'Error in debug handler: {str(e)}'})

@socketio.on('park_rotator')
def handle_park_rotator():
    if main_window and hasattr(main_window, 'park_rotators'):
        main_window.park_rotators()
        handle_get_status()

@socketio.on('stop_rotator')
def handle_stop_rotator():
    if main_window and hasattr(main_window, 'stop_rotators'):
        main_window.stop_rotators()
        handle_get_status()

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
    socketio.run(flask_app, host='0.0.0.0', port=port, debug=debug, use_reloader=False)

# These functions will be called from the main application when changes occur
def broadcast_satellite_change(satellite_name):
    """Broadcast satellite changes to all web clients"""
    if satellite_name:
        safe_emit('status', {'satellite': satellite_name})
        # Also send updated transponder list
        try:
            handle_get_transponder_list({'satellite': satellite_name})
        except Exception as e:
            print(f"Error getting transponders after satellite change: {e}")
        
        # Also broadcast to remote if available
        try:
            import sys
            if 'lib.remote_client' in sys.modules:
                from lib import remote_client
                remote_client.broadcast_satellite_change(satellite_name)
        except ImportError:
            pass

def broadcast_transponder_change(transponder_name):
    """Broadcast transponder changes to all web clients"""
    if transponder_name:
        safe_emit('status', {'transponder': transponder_name})
        
        # Also broadcast to remote if available
        try:
            import sys
            if 'lib.remote_client' in sys.modules:
                from lib import remote_client
                remote_client.broadcast_transponder_change(transponder_name)
        except ImportError:
            pass

def broadcast_subtone_change(subtone):
    """Broadcast subtone changes to all web clients"""
    if subtone is not None:
        safe_emit('status', {'subtone': subtone})
        
        # Also broadcast to remote if available
        try:
            import sys
            if 'lib.remote_client' in sys.modules:
                from lib import remote_client
                remote_client.broadcast_subtone_change(subtone)
        except ImportError:
            pass

def broadcast_tracking_state(is_tracking):
    """Broadcast tracking state changes to all web clients"""
    safe_emit('status', {'tracking': is_tracking})
    
    # Also broadcast to remote if available
    try:
        import sys
        if 'lib.remote_client' in sys.modules:
            from lib import remote_client
            remote_client.broadcast_tracking_state(is_tracking)
    except ImportError:
        pass

def broadcast_full_status():
    if main_window:
        try:
            status = {
                'tracking': main_window.Stopbutton.isEnabled(),
                'satellite': main_window.my_satellite.name if hasattr(main_window, 'my_satellite') else None,
                'transponder': getattr(main_window, 'my_transponder_name', None) if hasattr(main_window, 'my_transponder_name') else None,
                'rx_offset': main_window.rxoffsetbox.value() if hasattr(main_window, 'rxoffsetbox') else 0
            }
            if hasattr(main_window, 'combo3'):
                status['subtone'] = main_window.combo3.currentText()
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
                if hasattr(main_window, 'log_sat_status_ele_val') and hasattr(main_window, 'log_sat_status_azi_val'):
                    status['satellite_position'] = {
                        'elevation': main_window.log_sat_status_ele_val.text(),
                        'azimuth': main_window.log_sat_status_azi_val.text()
                    }
                if hasattr(main_window, 'rxdoppler_val') and hasattr(main_window, 'txdoppler_val'):
                    status['doppler'] = {
                        'downlink': main_window.rxdoppler_val.text(),
                        'uplink': main_window.txdoppler_val.text()
                    }
            # Add rotator enabled flag
            rotator_enabled = getattr(main_window, 'ROTATOR_ENABLED', False)
            status['rotator_enabled'] = rotator_enabled
            # Add rotator info
            if rotator_enabled and hasattr(main_window, 'rotator_az_label') and hasattr(main_window, 'rotator_el_label'):
                def strip_prefix(text, prefix):
                    if text.startswith(prefix):
                        return text[len(prefix):].strip()
                    return text
                az = main_window.rotator_az_label.text()
                el = main_window.rotator_el_label.text()
                az = strip_prefix(az, 'Azimuth:')
                el = strip_prefix(el, 'Elevation:')
                status['rotator'] = {
                    'azimuth': az,
                    'elevation': el
                }
            elif not rotator_enabled:
                status['rotator'] = {
                    'azimuth': 'Disabled',
                    'elevation': 'Disabled'
                }
            safe_emit('status', status)
            try:
                handle_get_satellite_list()
            except Exception as e:
                print(f"Error getting satellite list for broadcast: {e}")
                
            # Also broadcast to remote if available
            try:
                import sys
                if 'lib.remote_client' in sys.modules:
                    from lib import remote_client
                    remote_client.broadcast_full_status()
            except ImportError:
                pass
        except Exception as e:
            print(f"Error broadcasting full status: {e}")

def load_satellite_list():
    global satellite_list_cache, satellite_list_file
    # Try multiple ways to get the SQF file path
    sqffile = None
    if hasattr(main_window, 'SQFILE'):
        sqffile = main_window.SQFILE
    elif hasattr(main_window, '__module__') and main_window.__module__ in sys.modules:
        module = sys.modules[main_window.__module__]
        if hasattr(module, 'SQFILE'):
            sqffile = module.SQFILE
    if not sqffile:
        try:
            import configparser
            config = configparser.ConfigParser()
            config.read('config.ini')
            sqffile = config.get('satellite', 'sqffile')
        except Exception as e:
            print(f"Error reading config.ini: {e}")
    if not sqffile:
        sqffile = 'doppler.sqf'
    satellite_list_file = sqffile
    satlist = []
    
    try:
        with open(sqffile, 'r') as h:
            sqfdata = h.readlines()
            for line in sqfdata:
                # Skip comment lines
                if line.strip().startswith(';'):
                    continue
                    
                parts = line.strip().split(',')
                if parts and len(parts) > 0:
                    sat_name = parts[0].strip() 
                    if sat_name:
                        satlist.append(sat_name)
        # Remove duplicates while preserving order
        unique_satlist = []
        for sat in satlist:
            if sat not in unique_satlist:
                unique_satlist.append(sat)
        satellite_list_cache = unique_satlist
        print(f"Satellite list loaded: {len(unique_satlist)} satellites from {sqffile}")
    except Exception as e:
        print(f"Error loading satellite list: {e}")
        satellite_list_cache = []

def refresh_satellite_list():
    load_satellite_list() 
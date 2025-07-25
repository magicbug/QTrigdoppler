### Helper functions
## Calculates the tx doppler frequency
import ephem
import math
import numpy as np
from datetime import datetime, timedelta, timezone
import time
C = 299792458.

def tx_dopplercalc(ephemdata, freq_at_sat, myloc):
    ephemdata.compute(myloc)
    doppler = round(freq_at_sat + ephemdata.range_velocity * freq_at_sat / C)
    return doppler
## Calculates the rx doppler frequency
def rx_dopplercalc(ephemdata, freq_at_sat, myloc):
    ephemdata.compute(myloc)
    doppler = round(freq_at_sat - ephemdata.range_velocity * freq_at_sat / C)
    return doppler

## Predictive tx doppler calculation - predicts future doppler based on rate
def tx_dopplercalc_predictive(ephemdata, freq_at_sat, myloc, prediction_seconds=0.25):
    ephemdata.compute(myloc)
    current_doppler = freq_at_sat + ephemdata.range_velocity * freq_at_sat / C
    
    # Calculate doppler rate by computing velocity at a small time offset
    future_time = ephem.Date(myloc.date + prediction_seconds / 86400.0)  # Convert seconds to days
    myloc_future = myloc.copy()
    myloc_future.date = future_time
    ephemdata.compute(myloc_future)
    future_doppler = freq_at_sat + ephemdata.range_velocity * freq_at_sat / C
    
    # Calculate rate and predict
    doppler_rate = (future_doppler - current_doppler) / prediction_seconds
    predicted_doppler = current_doppler + (doppler_rate * prediction_seconds)
    
    return round(predicted_doppler)

## Predictive rx doppler calculation - predicts future doppler based on rate  
def rx_dopplercalc_predictive(ephemdata, freq_at_sat, myloc, prediction_seconds=0.25):
    ephemdata.compute(myloc)
    current_doppler = freq_at_sat - ephemdata.range_velocity * freq_at_sat / C
    
    # Calculate doppler rate by computing velocity at a small time offset
    future_time = ephem.Date(myloc.date + prediction_seconds / 86400.0)  # Convert seconds to days
    myloc_future = myloc.copy()
    myloc_future.date = future_time
    ephemdata.compute(myloc_future)
    future_doppler = freq_at_sat - ephemdata.range_velocity * freq_at_sat / C
    
    # Calculate rate and predict
    doppler_rate = (future_doppler - current_doppler) / prediction_seconds
    predicted_doppler = current_doppler + (doppler_rate * prediction_seconds)
    
    return round(predicted_doppler)
## Calculates the tx doppler error   
def tx_doppler_val_calc(ephemdata, freq_at_sat, myloc):
    ephemdata.compute(myloc)
    doppler = format(float(ephemdata.range_velocity * freq_at_sat / C), '.2f')
    return doppler
## Calculates the rx doppler error   
def rx_doppler_val_calc(ephemdata, freq_at_sat, myloc):
    ephemdata.compute(myloc)
    doppler = format(float(-ephemdata.range_velocity * freq_at_sat / C),'.2f')
    return doppler
## Calculates sat elevation at observer
def sat_ele_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    ele = format(ephemdata.alt/ math.pi * 180.0,'.2f' )
    return ele    
## Calculates sat azimuth at observer
def sat_azi_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    azi = format(ephemdata.az/ math.pi * 180.0,'.2f' )
    return azi
## Calculates sat subpoint latitude
def sat_lat_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    return format(ephemdata.sublat/ math.pi * 180.0,'.1f' )  
## Calculates sat subpoint longitude
def sat_lon_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    return format(ephemdata.sublong/ math.pi * 180.0,'.1f' )
## Calculates sat height at observer
def sat_height_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    height = format(float(ephemdata.elevation)/1000.0,'.2f') 
    return height
## Calculates sat eclipse status
def sat_eclipse_calc(ephemdata, myloc):
    ephemdata.compute(myloc)
    eclipse = ephemdata.eclipsed
    if eclipse:
        return "☾"
    else:
        return "☀︎"
## Calculates sat footprint diameter
def footprint_radius_km(alt_km):
    return 6371 * np.arccos(6371 / (6371 + alt_km))
    
## Calculates next sat pass at observer
def sat_next_event_calc(ephemdata, myloc):
    event_loc = myloc
    event_ephemdata = ephemdata
    event_epoch_time = datetime.now(timezone.utc)
    event_date_val = event_epoch_time.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
    event_loc.date = ephem.Date(event_date_val)
    event_ephemdata.compute(event_loc)
    rise_time,rise_azi,tca_time,tca_alt,los_time,los_azi = event_loc.next_pass(event_ephemdata)
    rise_time = rise_time.datetime().replace(tzinfo=timezone.utc)
    tca_time = tca_time.datetime().replace(tzinfo=timezone.utc)
    los_time = los_time.datetime().replace(tzinfo=timezone.utc)
    ele = format(event_ephemdata.alt/ math.pi * 180.0,'.2f' )
    if float(ele) <= 0.0:
        #Display next rise
        aos_cnt_dwn = rise_time - event_epoch_time
        return "AOS in " + str(time.strftime('%H:%M:%S', time.gmtime(aos_cnt_dwn.total_seconds())))
    else:
        # Display TCA and LOS, as the sat is already on the horion next_pass() ignores the current pass. Therefore we shift the time back by half a orbit period :D
        orbital_period = int(86400/(event_ephemdata.n))
        event_epoch_time = datetime.now(timezone.utc) - timedelta(seconds=int(orbital_period/2))
        event_date_val = event_epoch_time.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
        event_loc.date = ephem.Date(event_date_val)
        event_ephemdata.compute(event_loc)
        ephemdata.compute(myloc) # This is a workaround. Investigation needed
        rise_time,rise_azi,tca_time,tca_alt,los_time,los_azi = event_loc.next_pass(event_ephemdata)
        # Got right TCA and LOS, switch back to current epoch time
        event_epoch_time = datetime.now(timezone.utc)
        event_date_val = event_epoch_time.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3]
        event_loc.date = ephem.Date(event_date_val)
        tca_time = tca_time.datetime().replace(tzinfo=timezone.utc)
        los_time = los_time.datetime().replace(tzinfo=timezone.utc)
        tca_cnt_dwn = tca_time - event_epoch_time
        los_cnt_dwn = los_time - event_epoch_time
        if tca_cnt_dwn.days >= 0:
            return "TCA in " + str(time.strftime('%H:%M:%S', time.gmtime(tca_cnt_dwn.total_seconds())))
        else:
            return "LOS in " + str(time.strftime('%H:%M:%S', time.gmtime(los_cnt_dwn.total_seconds())))
            
    return "Error"

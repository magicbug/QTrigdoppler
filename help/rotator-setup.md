# Rotator Setup Guide

Complete guide to configuring and operating antenna rotators with QTRigdoppler for automatic satellite tracking.

## 📡 Overview

QTRigdoppler supports automatic antenna rotator control to track satellites in real-time. The system automatically points your antenna toward the satellite being tracked, parking the rotator when the satellite is below the minimum elevation threshold.

### Supported Features
- **Automatic Tracking**: Real-time antenna positioning during satellite passes
- **Smart Parking**: Automatic park position when satellite is below minimum elevation
- **Manual Control**: Park, stop, and refresh rotator position commands
- **Frequency Control**: Pause frequency updates while maintaining rotator tracking for manual frequency control
- **Web API Integration**: Remote rotator control via web interface
- **Position Monitoring**: Real-time azimuth and elevation display
- **Safety Limits**: Configurable azimuth and elevation range limits

## 🔧 Hardware Requirements

### Compatible Rotators
QTRigdoppler currently supports **Yaesu rotator protocol**:
- **Yaesu G-5500/G-5400** - Az/El rotator systems
- **Compatible models** - Any Az/El rotator supporting Yaesu GS-232 protocol

### Interface Requirements
- **Serial Connection**: RS-232 or USB-to-serial adapter
- **Control Box**: Yaesu rotator control unit (GS-232 interface)
- **Cables**: Proper serial cable (null modem if required)

## ⚙️ Configuration Setup

### 1. Basic Configuration

Edit your `config.ini` file and locate the `[rotator]` section:

```ini
[rotator]
enabled = False           # Set to True to enable rotator control
serial_port = COM4        # Windows: COM1, COM2, etc. / Linux: /dev/ttyUSB0
baudrate = 4800          # Communication speed (typically 4800 for Yaesu)
az_park = 0              # Parking azimuth position (degrees)
el_park = 0              # Parking elevation position (degrees)
az_min = 0               # Minimum azimuth limit (degrees)
az_max = 450             # Maximum azimuth limit (degrees, >360 allows overlap)
el_min = 0               # Minimum elevation limit (degrees)
el_max = 180             # Maximum elevation limit (degrees)
min_elevation = 5        # Minimum tracking elevation (degrees)
```

### 2. Parameter Descriptions

| Parameter | Description | Typical Values |
|-----------|-------------|----------------|
| `enabled` | Enable/disable rotator control | `True` or `False` |
| `serial_port` | Serial port for rotator communication | `COM1-COM99` (Windows)<br>`/dev/ttyUSB0` (Linux) |
| `baudrate` | Serial communication speed | `4800` (Yaesu standard) |
| `az_park` | Azimuth parking position | `0` (North), `180` (South) |
| `el_park` | Elevation parking position | `0` (Horizontal) |
| `az_min` | Minimum azimuth travel limit | `0` degrees |
| `az_max` | Maximum azimuth travel limit | `450` (allows 90° overlap) |
| `el_min` | Minimum elevation travel limit | `0` degrees |
| `el_max` | Maximum elevation travel limit | `180` degrees |
| `min_elevation` | Minimum satellite elevation for tracking | `5-15` degrees |

### 3. Advanced Settings

#### Azimuth Overlap (az_max > 360)
Setting `az_max` greater than 360° allows the rotator to cross the North point without requiring a full 360° rotation:
- **Standard**: `az_max = 360` - No overlap
- **Overlap**: `az_max = 450` - Allows 90° overlap for smoother tracking

#### Minimum Elevation Considerations
The `min_elevation` setting determines when tracking starts/stops:
- **5°**: Good for most locations, avoids ground/building obstructions
- **10°**: Better for urban environments with obstacles
- **15°**: Ideal for locations with significant horizon obstructions

## 🖥️ Application Settings

### GUI Configuration
1. **Open Settings**: Navigate to Settings → Advanced Settings
2. **Rotator Section**: Locate the "rotator" group box
3. **Configure Parameters**:
   - ✅ **Active**: Enable rotator control
   - **Port**: Select your serial port from dropdown
   - **Baudrate**: Set communication speed (typically 4800)
   - **Park Positions**: Set Az Park and El Park values
   - **Travel Limits**: Configure Az/El Min/Max ranges
   - **Min Elevation**: Set minimum tracking elevation

### Save Configuration
Click **"Save Configuration"** to apply settings and restart the application.

## 📍 Testing and Verification

### 1. Initial Connection Test
After enabling rotator control:
1. **Check Status Display**: Look for rotator position in the main window
2. **Position Display**: Should show current Az/El readings
3. **Error Indicators**: "error" text indicates connection problems

### 2. Manual Control Tests
Use the rotator control buttons to verify operation:

| Button | Function | Expected Result |
|--------|----------|-----------------|
| **Park Rotators** | Move to park position | Rotator moves to configured park Az/El |
| **Stop Rotation** | Stop all movement | Rotator stops immediately |
| **Refresh Position** | Update position display | Current position updates in GUI |

### 3. Tracking Test
1. **Select Satellite**: Choose a satellite with upcoming pass
2. **Start Tracking**: Click "Start Tracking"
3. **Monitor Movement**: Rotator should move to satellite position
4. **Verify Parking**: When elevation drops below minimum, rotator should park

## 🎛️ Operation Guide

### Automatic Tracking
When tracking is active:
- **Above Min Elevation**: Rotator follows satellite in real-time
- **Below Min Elevation**: Rotator moves to park position
- **Position Updates**: Every 1 second during tracking
- **Smart Movement**: Only moves when position changes ≥1 degree

### Manual Control
| Action | Method | Notes |
|--------|--------|-------|
| **Park** | Click "Park Rotators" | Moves to configured park position |
| **Stop** | Click "Stop Rotation" | Emergency stop - halts all movement |
| **Toggle Frequency** | Click "Pause/Resume Frequency Updates" or press **F** | Toggles between paused and active frequency updates while keeping rotator tracking |

### 🎛️ Manual Frequency Control

QTRigdoppler supports pausing frequency updates while maintaining rotator tracking. This is particularly useful for newer satellites requiring manual frequency control.

**📖 For complete frequency control documentation, see the [Frequency Control Guide](frequency-control.md)**

Key features:
- Pause automatic doppler correction while rotator continues tracking
- Manual frequency tuning for complex satellites
- Toggle control via button or **F** key
- Available in desktop and web interfaces

### Web API Control
If Web API is enabled, rotators can be controlled remotely:
- **Park Command**: `park_rotator` via web interface
- **Stop Command**: `stop_rotator` via web interface
- **Status Monitoring**: Real-time position updates

## 🛠️ Troubleshooting

### Common Issues

#### "error" Position Display
**Symptoms**: Position shows "error" instead of degrees
**Causes**:
- Serial port not available or in use
- Incorrect baudrate setting
- Cable connection problems
- Rotator control unit powered off

**Solutions**:
1. Verify serial port in Device Manager (Windows) or `lsusb` (Linux)
2. Check baudrate matches rotator settings (typically 4800)
3. Test serial cable and connections
4. Ensure rotator control unit is powered and operational

#### No Position Updates
**Symptoms**: Position display doesn't change
**Causes**:
- Rotator not responding to position queries
- Communication errors
- Hardware malfunction

**Solutions**:
1. Click "Refresh Position" button
2. Check serial connection integrity
3. Verify rotator control unit operation
4. Test with rotator manufacturer's software

#### Tracking Not Working
**Symptoms**: Rotator doesn't move during tracking
**Causes**:
- Rotator not enabled in configuration
- Satellite elevation below minimum threshold
- Serial communication failure

**Solutions**:
1. Verify `enabled = True` in config.ini
2. Check satellite elevation is above `min_elevation`
3. Test manual control buttons first
4. Review application logs for error messages

#### Rotation Range Issues
**Symptoms**: Rotator stops at unexpected positions
**Causes**:
- Incorrect az_min/az_max settings
- Hardware travel limits
- Cable wrap protection

**Solutions**:
1. Verify azimuth limits in configuration
2. Check rotator hardware limit switches
3. Ensure cables have sufficient slack for rotation
4. Consider azimuth overlap settings (az_max > 360)

### Serial Port Issues

#### Windows Port Detection
```powershell
# List available COM ports
Get-WmiObject -Class Win32_SerialPort | Select-Object Name,DeviceID
```

#### Linux Port Detection
```bash
# List USB serial devices
ls /dev/ttyUSB*
# Check port permissions
ls -l /dev/ttyUSB0
```

### Debug Information
Check application logs for rotator-related messages:
- Connection status
- Position query results
- Movement commands
- Error conditions

## 📋 Best Practices

### Installation
1. **Power Sequence**: Power rotator control unit before starting QTRigdoppler
2. **Cable Management**: Ensure adequate cable slack for full azimuth rotation
3. **Limit Settings**: Configure safe travel limits to prevent mechanical damage
4. **Park Position**: Choose park position away from obstacles (antennas, buildings)

### Operation
1. **Pre-Pass Check**: Verify rotator position before starting tracking
2. **Weather Monitoring**: Park rotator during severe weather
3. **Regular Testing**: Periodically test manual control functions
4. **Maintenance**: Keep rotator mechanics lubricated and calibrated

### Safety
1. **Travel Limits**: Always configure appropriate azimuth and elevation limits
2. **Emergency Stop**: Use "Stop Rotation" button for immediate halt
3. **Manual Override**: Keep rotator control unit accessible for manual operation
4. **Power Protection**: Use surge protection for rotator control systems
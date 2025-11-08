# QTrigdoppler Configuration Guide

Complete reference for configuring QTrigdoppler through the `config.ini` file.

## 📋 Overview

QTrigdoppler uses a configuration file (`config.ini`) to store all application settings. This file is automatically created on first run and can be modified to customize the application behavior according to your setup.

### Quick Start

1. **Copy Example**: Copy `config.ini.example` to `config.ini`
2. **Basic Setup**: Modify the `[qth]` section with your station coordinates
3. **Radio Setup**: Configure the `[icom]` section for your radio
4. **Enable Features**: Configure optional features as needed
5. **Restart**: Restart QTrigdoppler for changes to take effect

## 🗂️ Configuration Sections

### [qth] - Station Location & Radio Settings

Your station's geographic location and basic radio parameters.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `latitude` | float | **Yes** | Station latitude in decimal degrees | `40.7128` |
| `longitude` | float | **Yes** | Station longitude in decimal degrees | `-74.0060` |
| `altitude` | float | **Yes** | Station altitude in meters above sea level | `100.0` |
| `step_rx` | int | No | RX frequency tuning step in Hz | `1` |
| `step_tx` | int | No | TX frequency tuning step in Hz ⚠️ *Not used* | `1` |
| `max_offset_rx` | int | No | Maximum RX doppler offset in Hz | `5000` |
| `max_offset_tx` | int | No | Maximum TX doppler offset in Hz ⚠️ *Not used* | `5000` |
| `gps_port` | string | No | GPS serial port for automatic coordinates | `COM3` |

**Example:**
```ini
[qth]
latitude = 40.7128
longitude = -74.0060
altitude = 100.0
step_rx = 1
max_offset_rx = 5000
gps_port = COM3
```

### [satellite] - Satellite Data Configuration

Configuration for satellite tracking data sources and parameters.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `tle_file` | string | **Yes** | Local TLE (Two-Line Element) file | `mykepler.txt` |
| `tle_url` | string | **Yes** | URL for downloading TLE updates | `https://tle.oscarwatch.org/` |
| `amsatnames` | string | No | AMSAT names file ⚠️ *Not used* | `AmsatNames.txt` |
| `sqffile` | string | **Yes** | Satellite frequency definition file | `doppler.sqf` |
| `doppler_threshold_fm` | int | No | FM mode doppler threshold in Hz | `200` |
| `doppler_threshold_linear` | int | No | Linear transponder threshold in Hz | `50` |
| `predictive_doppler` | bool | No | Enable predictive doppler for linear satellites | `True`/`False` |

**Example:**
```ini
[satellite]
tle_file = mykepler.txt
tle_url = https://tle.oscarwatch.org/
sqffile = doppler.sqf
doppler_threshold_fm = 200
doppler_threshold_linear = 50
predictive_doppler = True
```

#### Satellite Database Updates

QTrigdoppler can automatically update the satellite frequency database (doppler.sqf) from oscarwatch.org:

**UI Location**: Settings → Files → "Update Satellite Database" button

**Update Options**:
- **Replace Complete File**: Downloads and replaces the entire doppler.sqf file
- **Merge New Satellites**: Adds only new satellites while preserving existing entries

**Features**:
- Progress indication during download
- Detailed feedback showing which satellites were added during merge
- Automatic satellite list refresh after update
- Error handling with user-friendly messages
- Logging of all update operations

### [icom] - Radio Configuration

Settings for Icom transceiver control via CI-V interface.

| Setting | Type | Required | Description | Values/Example |
|---------|------|----------|-------------|----------------|
| `radio` | int | **Yes** | Icom radio model number | `910` (IC-910H) |
| `cviaddress` | int | **Yes** | CI-V address in hex | `60` |
| `fullmode` | bool | No | Enable full mode control | `True`/`False` |
| `serialport` | string | **Yes** | Serial port device | `/dev/ttyUSB0` (Linux), `COM1` (Windows) |
| `rig_type` | string | No | Frequency range setting | `EU`/`US`/`JP` |

**Example:**
```ini
[icom]
radio = 910
cviaddress = 60
fullmode = False
serialport = /dev/ttyUSB0
rig_type = EU
```

### [misc] - General Application Settings

Miscellaneous application behavior settings.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `display_map` | bool | No | Show satellite ground track map | `True`/`False` |
| `last_tle_update` | string | No | Last TLE update timestamp (auto-managed) | `2025-01-01 00:00:00` |
| `last_doppler_update` | string | No | Last doppler.sqf update timestamp (auto-managed) | `Never` |
| `tle_update_interval` | int | No | TLE update interval in seconds | `86400` (24 hours) |
| `auto_tle_startup` | bool | No | Auto-update TLE files on startup | `True`/`False` |
| `auto_tle_interval_enabled` | bool | No | Enable periodic TLE updates | `True`/`False` |
| `auto_tle_interval_hours` | int | No | Hours between auto TLE updates | `24` |
| `voice_announcement` | bool | No | Voice announcements ⚠️ *Not used* | `True`/`False` |
| `stylesheet` | string | No | Name of selected UI stylesheet | `dark_blue.xml` |
| `ui_scale` | float | No | Scale for the UI | `1.5` |

**Example:**
```ini
[misc]
display_map = False
auto_tle_startup = True
auto_tle_interval_enabled = True
auto_tle_interval_hours = 24
```

### [logging] - Application Logging

Configure application logging behavior and output.

| Setting | Type | Required | Description | Values |
|---------|------|----------|-------------|--------|
| `level` | string | No | Logging level | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `log_to_file` | bool | No | Enable file logging | `True`/`False` |
| `log_file` | string | No | Log file path (relative to app) | `logs/qtrigdoppler.log` |
| `max_file_size_mb` | int | No | Max log file size before rotation | `10` |
| `backup_count` | int | No | Number of backup log files | `5` |
| `console_output` | bool | No | Show logs in console | `True`/`False` |

**Example:**
```ini
[logging]
level = INFO
log_to_file = True
log_file = logs/qtrigdoppler.log
max_file_size_mb = 10
backup_count = 5
console_output = False
```

### [web_api] - Web API Server

Configuration for the built-in web API server.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable web API server | `True`/`False` |
| `port` | int | No | Web server port | `5000` |
| `debug` | bool | No | Enable debug mode | `True`/`False` |

**Example:**
```ini
[web_api]
enabled = True
port = 5000
debug = False
```

### [remote_server] - Remote Server Connection

Settings for connecting to a remote QTrigdoppler server.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enable` | bool | No | Enable remote server connection | `True`/`False` |
| `url` | string | No | Remote server URL | `http://your-server.com:5001` |
| `port` | int | No | Remote server port | `5001` |
| `debug` | bool | No | Enable debug mode | `True`/`False` |

**Example:**
```ini
[remote_server]
enable = True
url = http://192.168.1.100:5001
port = 5001
debug = False
```

### [offset_profiles] - Frequency Offset Profiles

Predefined frequency offset corrections for specific satellites and transponders.

**Format:** `satellite_name,transponder_name,rx_offset,tx_offset`

| Setting | Type | Description | Example |
|---------|------|-------------|---------|
| `satoffsetN` | string | Offset profile (N = 1,2,3...) | `IO-117,Digipeater,-550,-550` |

**Example:**
```ini
[offset_profiles]
satoffset1 = IO-117,Digipeater,-550,-550
satoffset2 = MESAT-1,TPX,1400,0
satoffset3 = JO-97,SSB Transponder,0,-2000
```

### [rotator] - Antenna Rotator Control

Configuration for automatic antenna rotator control. See [Rotator Setup Guide](rotator-setup.md) for detailed setup instructions.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable rotator control | `True`/`False` |
| `serial_port` | string | No | Rotator serial port | `COM4`/`/dev/ttyUSB1` |
| `baudrate` | int | No | Serial communication speed | `4800` |
| `az_park` | int | No | Parking azimuth position (degrees) | `0` |
| `el_park` | int | No | Parking elevation position (degrees) | `0` |
| `az_min` | int | No | Minimum azimuth limit (degrees) | `0` |
| `az_max` | int | No | Maximum azimuth limit (degrees) | `450` |
| `el_min` | int | No | Minimum elevation limit (degrees) | `0` |
| `el_max` | int | No | Maximum elevation limit (degrees) | `180` |
| `min_elevation` | int | No | Minimum elevation for tracking | `5` |

**Example:**
```ini
[rotator]
enabled = True
serial_port = COM4
baudrate = 4800
az_park = 0
el_park = 0
az_min = 0
az_max = 450
el_min = 0
el_max = 180
min_elevation = 5
```

### [Cloudlog] - Logbook Integration

Automatic logging integration with Cloudlog/Wavelog systems.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable Cloudlog integration | `True`/`False` |
| `api_key` | string | Yes* | Cloudlog/Wavelog API key | `your_api_key_here` |
| `url` | string | Yes* | Cloudlog/Wavelog base URL | `https://your.cloudlog.site` |

*Required when `enabled = True`

**Example:**
```ini
[Cloudlog]
enabled = True
api_key = abcd1234efgh5678
url = https://mylog.example.com
```

### [passrecording] - Automatic Pass Recording

Configuration for automatic audio recording during satellite passes. See [Pass Recording Guide](pass-recording.md) for detailed setup.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable pass recording | `True`/`False` |
| `soundcard` | string | No | Audio input device | `default` or device name |
| `save_dir` | string | No | Recording save directory | `./recordings` |
| `min_elevation` | float | No | Min elevation to start recording | `10.0` |
| `sample_rate` | int | No | Audio sample rate (Hz) | `44100` |
| `channels` | int | No | Audio channels (1=mono, 2=stereo) | `1` |
| `bit_depth` | int | No | Audio bit depth | `16` |

**Example:**
```ini
[passrecording]
enabled = True
soundcard = USB Audio Device
save_dir = ./recordings
min_elevation = 10.0
sample_rate = 44100
channels = 1
bit_depth = 16
```

**Note**: If both Pass Recording and Remote Audio use the same RX soundcard, they automatically share the audio stream. See [Remote Audio Transmission](remote-operation.md#-remote-audio-transmission) for details.

### [remote_audio] - Remote Audio Transmission

Configuration for browser-based two-way audio transmission. See [Remote Operation Guide](remote-operation.md#-remote-audio-transmission) for detailed setup.

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable remote audio transmission | `True`/`False` |
| `tx_soundcard` | string | No | TX audio output device (to radio) | `default` or device name |
| `rx_soundcard` | string | No | RX audio input device (from radio) | `default` or device name |
| `sample_rate` | int | No | Audio sample rate (Hz) | `44100` |
| `channels` | int | No | Audio channels (1=mono, 2=stereo) | `1` |

**Example:**
```ini
[remote_audio]
enabled = True
tx_soundcard = Line Out
rx_soundcard = Line In
sample_rate = 44100
channels = 1
```

**Note**: Requires the Remote Server System (Node.js server) to be enabled. The RX soundcard can be shared with Pass Recording if both use the same device.

## ⚠️ Unused Configuration Items

The following configuration items are present in older config files but are **not currently used** by the application:

- `[qth]` → `step_tx` - TX frequency step
- `[qth]` → `max_offset_tx` - Maximum TX offset
- `[satellite]` → `amsatnames` - AMSAT names file
- `[misc]` → `voice_announcement` - Voice announcements

These items can be safely removed from your configuration file.

## 🔧 Configuration Management

### Automatic Updates

Some configuration values are automatically updated by the application:
- `[misc]` → `last_tle_update` - Updated when TLE files are refreshed
- `[misc]` → `last_doppler_update` - Updated when satellite database (doppler.sqf) is refreshed
- `[offset_profiles]` → `satoffsetN` - New profiles added when offsets are saved
- `[qth]` → `gps_port` - Updated when GPS port is selected

### Settings Storage

Most settings can be modified through the QTrigdoppler GUI:
1. **Feature Settings Tab** - Most configuration options
2. **Settings Menu** - Additional configuration options
3. **Store Settings** - Save changes (requires restart)

### Manual Editing

You can manually edit `config.ini` with any text editor:
1. **Stop Application** - Close QTrigdoppler first
2. **Edit File** - Modify `config.ini` carefully
3. **Check Syntax** - Ensure proper INI format
4. **Restart** - Launch QTrigdoppler to apply changes

### Backup and Recovery

**Create Backups:**
```bash
cp config.ini config.ini.backup
```

**Reset to Defaults:**
1. Delete or rename existing `config.ini`
2. Copy `config.ini.example` to `config.ini`
3. Modify with your settings
4. Restart QTrigdoppler

## 🚀 Quick Setup Examples

### Minimal Setup
```ini
[qth]
latitude = 40.7128
longitude = -74.0060
altitude = 100.0

[satellite]
tle_file = mykepler.txt
tle_url = https://tle.oscarwatch.org/
sqffile = doppler.sqf
predictive_doppler = True

[icom]
radio = 910
cviaddress = 60
serialport = /dev/ttyUSB0
```

### Full Featured Setup
```ini
[qth]
latitude = 40.7128
longitude = -74.0060
altitude = 100.0

[satellite]
tle_file = mykepler.txt
tle_url = https://tle.oscarwatch.org/
sqffile = doppler.sqf
predictive_doppler = True

[icom]
radio = 910
cviaddress = 60
fullmode = True
serialport = /dev/ttyUSB0

[rotator]
enabled = True
serial_port = COM4
min_elevation = 10

[passrecording]
enabled = True
soundcard = USB Audio Device
min_elevation = 10.0

[remote_audio]
enabled = True
tx_soundcard = Line Out
rx_soundcard = Line In
sample_rate = 44100
channels = 1

[web_api]
enabled = True
port = 5000

[Cloudlog]
enabled = True
api_key = your_api_key
url = https://your.cloudlog.site
```

## 📚 Related Documentation

- [Rotator Setup Guide](rotator-setup.md) - Detailed rotator configuration
- [Pass Recording Guide](pass-recording.md) - Audio recording setup
- [Remote Operation Guide](remote-operation.md) - Remote control and audio transmission
- [GPS Integration](gps-integration.md) - GPS coordinate updates
- [Keyboard Shortcuts](keyboard-shortcuts.md) - Application shortcuts

---

*For more help, see the [main documentation](README.md) or check the project repository.*

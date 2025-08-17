# QTrigdoppler Pass Recording Guide

Automatically record satellite passes with high-quality audio capture during your satellite tracking sessions.

## 🎯 Overview

The Pass Recording feature automatically captures audio from your radio during satellite passes, providing a complete record of communications and signals. Recordings start and stop automatically based on satellite elevation, ensuring you never miss important passes while conserving disk space.

### Key Features

- **Automatic Recording**: Starts/stops based on satellite elevation thresholds
- **High-Quality Audio**: Supports multiple sample rates, bit depths, and formats
- **Smart Device Management**: Robust audio device detection and configuration
- **Real-Time Monitoring**: Audio level meters and monitoring capabilities
- **Intelligent File Naming**: UTC timestamped files with satellite names
- **Integration**: Seamlessly integrates with satellite tracking system

## 🚀 Quick Start

### Enable Pass Recording

1. **Navigate to Settings**: Go to **Feature Settings** tab
2. **Enable Recording**: Check **"Enable Pass Recording"**
3. **Select Audio Device**: Choose your radio's audio output device
4. **Set Save Directory**: Choose where recordings will be stored
5. **Configure Elevation**: Set minimum elevation for recording (default: 20°)
6. **Save Settings**: Click **"Store Settings - requires restart"**
7. **Restart Application**: Restart QTrigdoppler for changes to take effect

### Basic Operation

1. **Start Tracking**: Begin tracking a satellite normally
2. **Automatic Recording**: Recording starts when satellite reaches minimum elevation
3. **Monitor Status**: Check the recording indicator (✔ = recording, ✘ = not recording)
4. **Automatic Stop**: Recording stops when satellite drops below minimum elevation
5. **File Saved**: WAV file automatically saved to configured directory

## ⚙️ Configuration

### Essential Settings

| Setting | Description | Default | Recommendation |
|---------|-------------|---------|----------------|
| **Enable Pass Recording** | Master on/off switch | `False` | `True` for automatic recording |
| **Soundcard** | Audio input device | `default` | Select your radio's audio output |
| **Save Directory** | Recording storage location | `./recordings` | Use dedicated folder with ample space |
| **Min Elevation** | Recording start/stop threshold | `20.0°` | `10-30°` based on local conditions |

### Audio Quality Settings

| Setting | Options | Default | Notes |
|---------|---------|---------|-------|
| **Sample Rate** | 8000-192000 Hz | `44100` | `44100` recommended for amateur radio |
| **Channels** | 1 (Mono) or 2 (Stereo) | `1` | Mono sufficient for most amateur radio |
| **Bit Depth** | 8, 16, 24, or 32 bits | `16` | `16-bit` provides excellent quality |

### Recommended Configurations

**Standard Amateur Radio:**
```ini
enabled = True
soundcard = [Your Radio's Audio Device]
min_elevation = 0
sample_rate = 44100
channels = 1
bit_depth = 16
```

**High-Quality Recording:**
```ini
enabled = True
soundcard = [High-Quality Audio Interface]
min_elevation = 0
sample_rate = 48000
channels = 2
bit_depth = 24
```

**Space-Conscious Recording:**
```ini
enabled = True
soundcard = [Your Radio's Audio Device]
min_elevation = 0
sample_rate = 22050
channels = 1
bit_depth = 16
```

## 🔧 Audio Device Setup

### Device Selection Methods

**By Name (Recommended):**
- Select device by its full name from the dropdown
- Most reliable method for consistent device identification
- Names are stored in configuration for reliability

**By Index (Legacy):**
- Numeric device index (0, 1, 2, etc.)
- May change if devices are added/removed
- Only recommended if device names are problematic

**Default Device:**
- Uses system default audio input
- Good for simple setups with one audio device
- May not work correctly in complex audio setups

### Audio Device Requirements

**Compatible Devices:**
- Sound cards with line input
- USB audio interfaces
- Radio-specific audio interfaces (e.g., SignaLink, RigBlaster)
- Virtual audio cables (e.g., VB-Cable, Virtual Audio Cable)

**Connection Examples:**
- **Direct**: Radio audio output → Sound card line input
- **Interface**: Radio ↔ Audio interface ↔ Computer
- **Virtual**: Radio software → Virtual audio cable → QTrigdoppler

### Testing Your Setup

1. **Monitor Audio Levels**: Use the **"Start Monitoring"** button in settings
2. **Check Input Level**: Ensure the audio level meter shows activity
3. **Test Recording**: Enable recording and test with a low elevation threshold
4. **Verify Output**: Check that recordings contain actual audio content

## 🎛️ Audio Monitoring

### Real-Time Level Monitoring

**Audio Level Meter:**
- Located in Pass Recording settings
- Shows real-time input levels
- Green bars indicate good signal
- Red indicates clipping/overload

**Monitor Button:**
- **"Start Monitoring"**: Begin real-time audio monitoring
- **"Stop Monitoring"**: End monitoring session
- Use to verify audio setup before recording

### Optimal Audio Levels

**Target Levels:**
- **Normal Speech**: 50-70% of meter
- **Peak Signals**: 80-90% maximum
- **Avoid**: Consistent 100% (clipping)

**Level Adjustment:**
- **Too Low**: Increase radio output or audio interface gain
- **Too High**: Decrease radio output or use attenuator
- **Clipping**: Reduce input gain immediately

## 📁 File Management

### Automatic File Naming

**Naming Convention:**
```
[SatelliteName]-[YYYYMMDD]-[HHMMSS].wav
```

**Examples:**
- `ISS-20250112-143530.wav` (ISS pass on Jan 12, 2025 at 14:35:30 UTC)
- `RS-44-20250112-203415.wav` (RS-44 pass on Jan 12, 2025 at 20:34:15 UTC)
- `SO-50-20250113-091245.wav` (SO-50 pass on Jan 13, 2025 at 09:12:45 UTC)

### File Location Management

**Default Directory:**
- `./recordings/` (relative to application directory)
- Created automatically if it doesn't exist

**Recommended Practices:**
- **Dedicated Folder**: Use a specific folder for satellite recordings
- **External Storage**: Consider external drive for large recording collections
- **Organization**: Create subfolders by date or satellite if needed
- **Backup**: Regular backup of important recordings

### File Size Estimates

| Configuration | Hourly Size | Daily Size (8 hrs) |
|---------------|-------------|-------------------|
| 44.1kHz/16-bit/Mono | ~300 MB | ~2.4 GB |
| 48kHz/24-bit/Stereo | ~1.0 GB | ~8.0 GB |
| 22kHz/16-bit/Mono | ~150 MB | ~1.2 GB |

## 🔄 Operation Modes

### Automatic Mode (Recommended)

**How It Works:**
1. Pass recording monitors satellite elevation continuously
2. Recording starts when elevation ≥ minimum threshold
3. Recording continues throughout the pass
4. Recording stops when elevation < minimum threshold
5. Files are saved automatically with timestamps

**Requirements:**
- Satellite tracking must be active
- Pass recording must be enabled
- Audio device must be properly configured

### Manual Override

**Starting Recording:**
- Recording only starts automatically during satellite tracking
- Cannot manually start recording without active tracking
- Ensures recordings are properly tagged with satellite information

**Stopping Recording:**
- Recording stops automatically when tracking stops
- Recording stops when satellite drops below threshold
- Manual stop not directly available (stop tracking to stop recording)

## 📊 Status Indicators

### Recording Status Display

**Recording Indicator:**
- **✔ (Green)**: Currently recording
- **✘ (Red)**: Not recording

**Status Messages in Logs:**
```
Recording started: ISS-20250112-143530.wav
Recording audio level: 0.2543, total frames: 441000
Recording stopped: ISS-20250112-143530.wav
```

### Integration with Tracking

**Tracking Status Affects Recording:**
- Recording requires active satellite tracking
- Stops automatically when tracking stops
- Elevation updates drive recording decisions
- Pass optimization doesn't affect recording

## 🆘 Troubleshooting

### Common Issues

#### No Audio Devices Detected

**Symptoms:**
- Empty soundcard dropdown
- "No audio input devices detected" warning in logs

**Solutions:**
1. **Check Physical Connections**: Ensure audio cables are connected
2. **Verify Drivers**: Install/update audio device drivers
3. **Test Other Applications**: Verify device works in other audio software
4. **Run as Administrator**: Try running QTrigdoppler with elevated privileges

#### Device Not Available Error

**Symptoms:**
- "Configured audio device not available" error
- Recording fails to start

**Solutions:**
1. **Device in Use**: Close other applications using the audio device
2. **Reconnect Hardware**: Unplug and reconnect USB audio devices
3. **Select Different Device**: Try alternative audio input device
4. **Restart Application**: Close and restart QTrigdoppler

#### No Audio in Recordings

**Symptoms:**
- WAV files created but contain silence
- Very small file sizes (< 1000 bytes)

**Solutions:**
1. **Check Audio Levels**: Use monitoring feature to verify input levels
2. **Verify Connections**: Ensure audio cable is connected to correct input
3. **Test Audio Source**: Verify radio is producing audio output
4. **Check Device Settings**: Verify input levels in system audio settings

#### Recording Doesn't Start

**Symptoms:**
- Satellite above threshold but no recording starts
- Status remains ✘ (red)

**Solutions:**
1. **Enable Pass Recording**: Verify "Enable Pass Recording" is checked
2. **Check Elevation Threshold**: Verify satellite elevation exceeds minimum
3. **Active Tracking Required**: Ensure satellite tracking is active
4. **Device Configuration**: Verify audio device is properly configured

#### Poor Audio Quality

**Symptoms:**
- Distorted or clipped audio
- Noise in recordings

**Solutions:**
1. **Adjust Input Levels**: Reduce radio output or audio interface gain
2. **Check Connections**: Ensure good quality audio cables
3. **Increase Bit Depth**: Use 24-bit instead of 16-bit for higher dynamic range
4. **Sample Rate**: Try 48kHz instead of 44.1kHz

### Debug Information

**Enable Debug Logging:**
```ini
[logging]
level = DEBUG
```

**Useful Log Messages:**
- Device detection: `"Audio input device X: [Name] | Y channels"`
- Recording start: `"Starting recording for [Satellite] at elevation X"`
- Audio levels: `"Recording audio level: X.XXXX, total frames: XXXXX"`
- Device errors: `"Audio device error: [Description]"`

## 💡 Best Practices

### Pre-Pass Preparation

**Equipment Check:**
1. **Test Audio Path**: Verify complete audio chain works
2. **Monitor Levels**: Use monitoring feature to check levels
3. **Disk Space**: Ensure adequate storage space available
4. **Device Availability**: Confirm audio device isn't in use elsewhere

**Configuration Verification:**
1. **Elevation Threshold**: Set appropriate minimum elevation
2. **Audio Quality**: Configure sample rate and bit depth
3. **File Location**: Verify save directory exists and is writable

### During Operations

**Monitoring:**
- Check recording status indicator during passes
- Monitor application logs for any audio issues
- Verify disk space doesn't run out during long passes

**Audio Management:**
- Avoid adjusting radio volume during recording
- Don't change audio device settings during active recording
- Keep other audio applications closed during passes

### Post-Pass Management

**File Verification:**
- Check recording file sizes are reasonable
- Spot-check audio quality periodically
- Verify timestamps match pass times

**Storage Management:**
- Archive important recordings
- Delete failed or empty recordings
- Organize files by date or satellite

## 🌟 Advanced Features

### Integration with Satellite Tracking

**Automatic Correlation:**
- Recordings automatically tagged with satellite name
- Start/stop times align with elevation data
- Works with all supported satellite tracking modes

**Pass Optimization Compatibility:**
- Recording continues during rotator optimization
- No impact on recording quality or timing
- Works with all rotator control features

### Multi-Pass Recording

**Consecutive Passes:**
- Each pass creates separate recording file
- No overlap or interference between recordings
- Automatic file naming prevents conflicts

**Multiple Satellites:**
- Switch between satellites without stopping recording
- Each satellite gets appropriately named recording
- Seamless operation across different tracking sessions

### Error Recovery

**Device Failures:**
- Automatic recovery from temporary device issues
- Graceful handling of device disconnections
- Continued operation when device becomes available

**Storage Issues:**
- Warning when approaching disk space limits
- Graceful handling of write permission issues
- Error logging for troubleshooting

## 📞 Support and Resources

### Getting Help

**Check These First:**
1. **Application Logs**: Look for error messages in logs
2. **Audio Device Manager**: Verify device status in system settings
3. **Other Applications**: Test audio device in other recording software
4. **Physical Connections**: Check all cable connections

**Reporting Issues:**
- Include relevant log entries
- Specify audio device type and model
- Describe your audio connection setup
- Include configuration file (remove sensitive data)

### Performance Optimization

**Stable Recording:**
- Use dedicated audio interface for best results
- Close unnecessary applications during recording
- Use wired connections instead of wireless when possible
- Ensure adequate system resources

**Quality vs. Storage:**
- Higher sample rates and bit depths improve quality but increase file sizes
- Mono recording sufficient for most amateur radio applications
- Consider compression for archival storage
# Remote Operation Guide

Complete guide to QTRigdoppler's remote operation systems - control your station from anywhere!

## 📡 Overview

QTRigdoppler provides two powerful remote operation systems that allow you to control your satellite tracking station from anywhere:

1. **Built-in Web API** - Direct HTTP/WebSocket connection to your QTRigdoppler instance
2. **Remote Server System** - Standalone Node.js server for independent remote access

Both systems provide full control over satellite tracking, radio settings, and rotator operations through a modern web interface.

## 🌐 System 1: Built-in Web API (Direct Connection)

The built-in Web API provides direct access to your QTRigdoppler instance via HTTP and WebSocket connections.

### Features
- **Real-time Control**: Direct WebSocket connection for instant updates
- **Full Satellite Control**: Select satellites, transponders, and manage tracking
- **Radio Integration**: Control frequency offsets, subtones, and radio settings  
- **Rotator Support**: Park and control antenna rotators
- **Live Status**: Real-time display of satellite position, doppler, and tracking state
- **Zero Dependencies**: No additional server setup required

### Configuration

Add the following section to your `config.ini`:

```ini
[web_api]
enabled = True          # Enable the web API server
port = 5000            # Port for the web interface
debug = False          # Enable debug mode (optional)
```

### Starting the Web API

1. **Enable in Configuration**: Set `enabled = True` in the `[web_api]` section
2. **Start QTRigdoppler**: The web API server starts automatically with the application
3. **Access Interface**: Open your browser to `http://localhost:5000` (or your configured port)

### Network Access

To access from other devices on your network:

1. **Find Your IP Address**: 
   - Windows: `ipconfig`
   - Linux/Mac: `ifconfig` or `ip addr`

2. **Configure Firewall**: Allow incoming connections on your configured port (default 5000)

3. **Access from Remote Device**: 
   - Local network: `http://YOUR_IP_ADDRESS:5000`
   - Example: `http://192.168.1.100:5000`

### Security Considerations

⚠️ **Important**: The built-in Web API has no authentication. Only use on trusted networks.

- **Local Network Only**: Do not expose directly to the internet
- **VPN Recommended**: Use a VPN for secure remote access
- **Firewall Rules**: Restrict access to known devices/networks

## 🚀 System 2: Remote Server System (Independent Server)

The Remote Server System provides a standalone Node.js server that acts as a bridge between remote clients and your QTRigdoppler instance.

### Architecture

```
[QTRigdoppler] ←→ [Remote Server] ←→ [Web Clients]
```

### Features
- **Independent Operation**: Server runs separately from QTRigdoppler
- **Multiple Clients**: Support for multiple simultaneous web clients
- **Heartbeat System**: Automatic reconnection and health monitoring
- **State Caching**: Server maintains application state for instant client updates
- **Cross-Network**: Can run on different machines for distributed setups

### Prerequisites

Install Node.js dependencies in the `nodejs_server` directory:

```bash
cd nodejs_server
npm install
```

### Configuration

#### QTRigdoppler Configuration

Add the following section to your `config.ini`:

```ini
[remote_server]
enable = True                           # Enable remote server connection
url = http://your-server.com:5001      # Remote server URL
port = 5001                            # Remote server port (optional, read from URL)
debug = False                          # Enable debug mode (optional)
```

#### Remote Server Configuration

The remote server reads its configuration from the same `config.ini` file:

```ini
[remote_server]
port = 5001            # Port for the remote server
debug = false          # Enable debug logging
```

### Starting the Remote Server

1. **Start the Remote Server**:
   ```bash
   cd nodejs_server
   npm start
   # or
   node remote_server.js
   ```

2. **Start QTRigdoppler**: With `enable = True` in `[remote_server]` section

3. **Access Web Interface**: Open browser to `http://your-server:5001`

### Deployment Options

#### Option 1: Same Machine
- Run both QTRigdoppler and Remote Server on the same computer
- URL: `http://localhost:5001`
- Best for: Testing, single-user setups

#### Option 2: Separate Server
- Run Remote Server on a dedicated machine (Raspberry Pi, VPS, etc.)
- Configure QTRigdoppler to connect to remote server
- Best for: Multi-user access, always-on remote control

#### Option 3: Cloud Deployment
- Deploy Remote Server to cloud platform (AWS, DigitalOcean, etc.)
- Configure appropriate security groups/firewall rules
- Best for: Internet-wide access, professional installations

### Example Configurations

#### Local Network Setup
```ini
# config.ini
[remote_server]
enable = True
url = http://192.168.1.100:5001
port = 5001
debug = False
```

#### Cloud Server Setup
```ini
# config.ini  
[remote_server]
enable = True
url = http://your-domain.com:5001
port = 5001
debug = False
```

#### VPS/Dedicated Server
```ini
# config.ini
[remote_server]
enable = True
url = http://203.0.113.10:5001
port = 5001
debug = False
```

## 🎛️ Web Interface Features

Both systems provide the same feature-rich web interface:

### Connection Status
- **Visual Indicators**: Green/red connection status
- **Server Type Detection**: Shows "Direct Connection" vs "Remote Server"
- **Auto-Reconnection**: Automatic reconnection on connection loss

### Satellite Control
- **Satellite Selection**: Dropdown list of available satellites
- **Transponder Selection**: Automatic transponder list loading
- **Real-time Updates**: Live satellite position and doppler information
- **TLE Age Display**: Shows age of orbital data

### Tracking Operations
- **Start/Stop Tracking**: One-click tracking control
- **Status Display**: Real-time tracking state
- **Auto-Updates**: Live position and frequency information

### Radio Settings
- **RX Offset Control**: Precise frequency offset adjustment
- **Quick Offset Buttons**: ±10/100/1000 Hz preset adjustments
- **Subtone Selection**: CTCSS/PL tone configuration
- **Real-time Sync**: Settings synchronized across all clients

### Rotator Control
- **Park Rotator**: Send antenna to park position
- **Stop Rotation**: Emergency stop for rotator movement  
- **Position Display**: Live azimuth and elevation readout
- **Enable/Disable Status**: Shows rotator configuration state

### Information Display
- **Frequency Information**: Uplink/downlink frequencies and modes
- **Doppler Compensation**: Live doppler shift values
- **Position Data**: Satellite elevation and azimuth
- **System Status**: Comprehensive status information table

## 🔧 Configuration Details

### Web API Settings

| Setting | Type | Required | Description | Default |
|---------|------|----------|-------------|---------|
| `enabled` | bool | No | Enable web API server | `False` |
| `port` | int | No | Web server port | `5000` |
| `debug` | bool | No | Enable debug logging | `False` |

### Remote Server Settings

| Setting | Type | Required | Description | Default |
|---------|------|----------|-------------|---------|
| `enable` | bool | No | Enable remote server connection | `False` |
| `url` | string | Yes* | Remote server URL | `http://localhost:5001` |
| `port` | int | No | Remote server port (if not in URL) | `5001` |
| `debug` | bool | No | Enable debug logging | `False` |

*Required when `enable = True`

### Port Considerations

- **Default Ports**: Web API uses 5000, Remote Server uses 5001
- **Firewall**: Ensure chosen ports are open in your firewall
- **Conflicts**: Avoid conflicts with other applications
- **Range**: Use ports 1024-65535 for unprivileged operation

## 🛡️ Security and Best Practices

### Network Security
- **Trusted Networks Only**: Only use on networks you trust
- **VPN Access**: Use VPN for secure internet access
- **Firewall Rules**: Implement appropriate firewall restrictions
- **Regular Updates**: Keep Node.js and dependencies updated

### Authentication
⚠️ **Current Limitation**: Neither system includes built-in authentication

- **Network-Level Security**: Rely on network security measures
- **VPN Recommended**: Use VPN for secure remote access
- **Local Access**: Consider limiting to local network only

### Monitoring
- **Connection Logs**: Monitor connection attempts and usage
- **Debug Mode**: Use debug mode for troubleshooting
- **Health Checks**: Remote server provides `/status` endpoint

## 🔍 Troubleshooting

### Common Issues

#### Web API Won't Start
```
Problem: Web API server fails to start
Solutions:
- Check if port is already in use
- Verify enabled = True in config.ini
- Check application logs for errors
- Try different port number
```

#### Can't Connect to Remote Server
```
Problem: QTRigdoppler can't connect to remote server
Solutions:
- Verify remote server is running (check nodejs_server logs)
- Check URL and port configuration
- Verify network connectivity (ping server)
- Check firewall settings on both machines
- Ensure Node.js dependencies are installed
```

#### Web Interface Loads But No Data
```
Problem: Web interface loads but shows no satellite data
Solutions:
- Check QTRigdoppler is running and configured
- Verify SQF file path in configuration
- Check satellite data file (doppler.sqf) exists
- Review application logs for errors
```

#### Remote Server Connection Drops
```
Problem: Connection between QTRigdoppler and remote server unstable
Solutions:
- Check network stability
- Verify heartbeat system is working
- Review remote server logs
- Consider increasing ping timeout values
```

### Debug Mode

Enable debug mode for detailed logging:

```ini
[web_api]
debug = True

[remote_server]
debug = True
```

### Log Files

Monitor these log sources for troubleshooting:
- **QTRigdoppler Logs**: Application log file (configured in `[logging]` section)
- **Remote Server Logs**: Console output from `node remote_server.js`
- **Web Browser Console**: F12 → Console tab for client-side errors

### Network Diagnostics

Test connectivity:
```bash
# Test web API
curl http://localhost:5000

# Test remote server
curl http://your-server:5001/status

# Test from another machine
telnet your-server-ip 5001
```

## 📱 Mobile and Tablet Access

Both systems work well on mobile devices:

### Responsive Design
- **Mobile-Optimized**: Interface adapts to small screens
- **Touch-Friendly**: Large buttons and controls
- **Portrait/Landscape**: Works in both orientations

### Bookmarking
- **Home Screen**: Add to mobile home screen for app-like experience
- **Quick Access**: Bookmark for easy access
- **Multiple Configs**: Bookmark different server addresses

### Performance Tips
- **WiFi Recommended**: Use WiFi for best performance and reliability
- **Background Apps**: Close unnecessary apps for better performance
- **Battery Saving**: Consider impact on device battery life

## 🔄 Advanced Usage

### Multiple Remote Servers
Run multiple remote servers for redundancy:

```bash
# Server 1
PORT=5001 node remote_server.js

# Server 2  
PORT=5002 node remote_server.js
```

### Load Balancing
Use a reverse proxy (nginx, Apache) for load balancing multiple instances.

### Monitoring and Alerts
- Monitor server uptime and connectivity
- Set up alerts for connection failures
- Log usage patterns and performance metrics

### Integration
- **Home Automation**: Integrate with home automation systems
- **Logging Systems**: Send data to external logging systems
- **APIs**: Use REST endpoints for custom integrations

## 📚 API Reference

### WebSocket Events (Both Systems)

#### Client to Server
- `get_status` - Request current status
- `start_tracking` - Begin satellite tracking
- `stop_tracking` - Stop satellite tracking
- `select_satellite` - Choose satellite: `{satellite: "name"}`
- `select_transponder` - Choose transponder: `{transponder: "name"}`
- `set_subtone` - Set CTCSS tone: `{subtone: "67 Hz"}`
- `set_rx_offset` - Set frequency offset: `{offset: 1000}`
- `park_rotator` - Park antenna rotator
- `stop_rotator` - Stop rotator movement
- `pause_frequency_updates` - Pause automatic frequency correction while keeping rotator tracking
- `resume_frequency_updates` - Resume automatic frequency correction
- `get_satellite_list` - Request satellite list
- `get_transponder_list` - Request transponder list: `{satellite: "name"}`

#### Server to Client
- `status` - Current system status
- `satellite_list` - Available satellites: `{satellites: [], current: "name"}`
- `transponder_list` - Available transponders: `{transponders: [], current: "name"}`
- `tle_update_complete` - TLE update notification

### REST Endpoints (Remote Server Only)

- `GET /` - Web interface
- `GET /status` - Server health check

## 🎤 Remote Audio Transmission

QTRigdoppler includes a powerful two-way audio transmission system that allows remote operators to transmit audio to the radio (TX) and receive audio from the radio (RX) through a web browser.

### Overview

The Remote Audio system provides:
- **TX Audio (Browser → Radio)**: Transmit audio from your browser microphone to the radio
- **RX Audio (Radio → Browser)**: Receive audio from the radio and play it in your browser
- **Two-Way Communication**: Full duplex audio for complete remote operation
- **Stream Sharing**: RX audio can be simultaneously used by Pass Recorder and remote clients

### Architecture

```
[Browser Microphone] → [Node.js Server] → [QTRigdoppler] → [TX Soundcard] → [Radio]
[Radio] → [RX Soundcard] → [QTRigdoppler] → [Node.js Server] → [Browser Speakers]
```

### Prerequisites

1. **Remote Server System**: Remote Audio requires the Remote Server System (Node.js server)
2. **Audio Devices**: Configure TX and RX soundcards in QTRigdoppler
3. **Browser Support**: Modern browser with Web Audio API support (Chrome, Firefox, Edge, Safari)

### Configuration

#### QTRigdoppler Configuration

Add the following section to your `config.ini`:

```ini
[remote_audio]
enabled = True                    # Enable remote audio functionality
tx_soundcard = default           # TX soundcard (output device for radio)
rx_soundcard = default           # RX soundcard (input device from radio)
sample_rate = 44100              # Audio sample rate (Hz)
channels = 1                     # Audio channels (1=mono, 2=stereo)
```

#### Soundcard Selection

**TX Soundcard** (Output Device):
- This is the audio output device connected to your radio's microphone input
- Select the device that routes audio to your radio
- Common names: "Line Out", "Headphone Out", "Virtual Audio Cable", etc.

**RX Soundcard** (Input Device):
- This is the audio input device connected to your radio's audio output
- Select the device that receives audio from your radio
- Common names: "Line In", "Microphone", "Virtual Audio Cable", etc.
- **Note**: This same device can be shared with Pass Recorder

#### Audio Format

The system uses:
- **Format**: PCM, 16-bit signed integer
- **Sample Rate**: 44100 Hz (configurable: 8000-192000 Hz)
- **Channels**: Mono (1 channel) recommended for radio use
- **Streaming**: Real-time binary WebSocket streaming

### Setup Instructions

#### Step 1: Configure Audio Devices

1. Open QTRigdoppler → **Feature Settings** tab → **Remote Audio** section
2. Enable **"Enable Remote Audio"** checkbox
3. Select **TX Soundcard** (output device for radio)
4. Select **RX Soundcard** (input device from radio)
5. Configure **Sample Rate** and **Channels** as needed
6. Click **"Store Settings"**

#### Step 2: Verify Server Support

1. Click **"Test Server Connection"** button
2. Wait for test to complete
3. Verify status shows:
   - ✓ Server supports Remote Audio functionality
   - ✓ TX Audio (Browser → Radio): Supported
   - ✓ RX Audio (Radio → Browser): Supported
   - ✓ Two-way Audio: Supported

#### Step 3: Start Remote Server

Ensure the Node.js remote server is running:

```bash
cd nodejs_server
node remote_server.js
```

#### Step 4: Access Web Interface

1. Open browser to your remote server URL (e.g., `http://your-server:5001`)
2. Navigate to the audio controls section
3. Grant microphone permissions when prompted (for TX audio)
4. Grant audio playback permissions (for RX audio)

### Web Interface Usage

#### Transmitting Audio (TX)

1. **Select Microphone**: Choose your microphone device from the dropdown
2. **Start Transmission**: Click "Start TX" or "Enable Microphone"
3. **Monitor Levels**: Watch the audio level meter
4. **Stop Transmission**: Click "Stop TX" or disable microphone

#### Receiving Audio (RX)

1. **Enable Playback**: RX audio starts automatically when remote audio is enabled
2. **Adjust Volume**: Use browser or system volume controls
3. **Monitor Status**: Check connection status indicators

### Integration with Pass Recorder

The Remote Audio system intelligently shares the RX audio stream with Pass Recorder:

- **Automatic Sharing**: If both Remote Audio and Pass Recorder use the same RX soundcard, they automatically share the audio stream
- **No Conflicts**: Both systems can operate simultaneously without device conflicts
- **Efficient**: Single audio input stream is distributed to multiple consumers

**Configuration Example**:
```ini
[passrecording]
enabled = True
soundcard = Line In              # Same device as remote_audio rx_soundcard

[remote_audio]
enabled = True
rx_soundcard = Line In           # Same device - will be shared automatically
```

### Troubleshooting

#### No Audio Transmission

**Problem**: TX audio not reaching radio

**Solutions**:
- Verify TX soundcard is correctly selected
- Check audio levels in browser (microphone level meter)
- Verify soundcard is connected to radio microphone input
- Test soundcard with other applications
- Check Windows/Mac audio mixer settings
- Verify remote server is running latest version with audio support

#### No Audio Reception

**Problem**: RX audio not playing in browser

**Solutions**:
- Verify RX soundcard is correctly selected
- Check radio audio output is connected to soundcard input
- Verify browser audio permissions
- Check browser console for errors (F12)
- Test soundcard with other applications
- Verify remote server supports RX audio (`/capabilities` endpoint)

#### Choppy or Delayed Audio

**Problem**: Audio playback is choppy or has delay

**Solutions**:
- Check network latency and bandwidth
- Reduce sample rate if network is slow
- Close unnecessary browser tabs/applications
- Use wired network connection instead of WiFi
- Check CPU usage on server and client machines
- Verify audio buffer sizes are appropriate

#### Server Test Fails

**Problem**: "Test Server Connection" shows errors

**Solutions**:
- Verify Node.js server is running
- Check server URL is correct in configuration
- Ensure server has `/capabilities` endpoint (update server if needed)
- Check firewall allows connections
- Review server logs for errors
- Verify server version supports remote audio

#### Device Conflicts

**Problem**: Pass Recorder and Remote Audio conflict

**Solutions**:
- Ensure both use the same RX soundcard device name
- Check that stream sharing is working (check logs)
- Verify Remote Audio is enabled before starting Pass Recorder
- Restart QTRigdoppler if conflicts persist

### Audio Format Compatibility

The system supports various audio formats:

| Sample Rate | Channels | Use Case |
|-------------|----------|----------|
| 44100 Hz | 1 (Mono) | **Recommended** - Standard quality, low bandwidth |
| 48000 Hz | 1 (Mono) | High quality, slightly higher bandwidth |
| 22050 Hz | 1 (Mono) | Lower bandwidth, acceptable quality |
| 44100 Hz | 2 (Stereo) | Stereo (if needed), higher bandwidth |

**Recommendation**: Use 44100 Hz mono for best balance of quality and bandwidth.

### Security Considerations

⚠️ **Important**: Remote Audio transmits real audio data over the network

- **Network Security**: Use secure networks or VPN
- **Bandwidth**: Audio streaming uses significant bandwidth
- **Privacy**: Be aware that audio is transmitted over the network
- **Access Control**: Consider network-level access restrictions

### Performance Tips

- **Network**: Use wired connection for best performance
- **Bandwidth**: Ensure adequate upload/download bandwidth
- **Latency**: Local network provides lowest latency
- **CPU**: Monitor CPU usage during audio streaming
- **Browser**: Use modern browsers for best Web Audio API support

### Advanced Configuration

#### Custom Sample Rates

For specialized applications, you can configure custom sample rates:

```ini
[remote_audio]
sample_rate = 48000              # Higher quality
sample_rate = 22050              # Lower bandwidth
```

#### Multiple Remote Clients

Multiple browsers can connect simultaneously:
- Each client can transmit independently
- RX audio is broadcast to all connected clients
- Server handles audio mixing/routing automatically

### API Reference

#### WebSocket Audio Events

**TX Audio (Client → Server)**:
- `tx_audio_start` - Begin audio transmission
- `tx_audio_data` - Audio data chunk (binary)
- `tx_audio_stop` - Stop audio transmission

**RX Audio (Server → Client)**:
- `rx_audio_start` - Begin audio reception
- `rx_audio_data` - Audio data chunk (binary)
- `rx_audio_stop` - Stop audio reception

#### Server Capabilities Endpoint

Check server capabilities:

```bash
curl http://your-server:5001/capabilities
```

Response includes:
```json
{
  "version": "1.0",
  "features": {
    "remote_audio": {
      "enabled": true,
      "tx_audio": true,
      "rx_audio": true,
      "two_way": true
    }
  },
  "audio_formats": {
    "sample_rate": [8000, 16000, 22050, 44100, 48000],
    "channels": [1, 2]
  }
}
```

## 💡 Tips and Best Practices

### Performance
- **Regular Restarts**: Restart servers periodically for optimal performance
- **Resource Monitoring**: Monitor CPU and memory usage
- **Network Quality**: Ensure stable network connections
- **Audio Streaming**: Monitor bandwidth usage during audio transmission

### Reliability  
- **Backup Configurations**: Keep backup copies of working configurations
- **Redundant Systems**: Consider multiple access methods
- **Health Monitoring**: Implement uptime monitoring
- **Audio Device Testing**: Test audio devices before important operations

### User Experience
- **Bookmark URLs**: Save frequently used server addresses
- **Test Connectivity**: Verify connections before important operations
- **Document Setup**: Keep notes on your specific configuration
- **Audio Levels**: Monitor and adjust audio levels for optimal quality

---

**Remote Operation Guide Version**: 1.1  
**Compatible with**: QTRigdoppler v1.0+  
**Last Updated**: January 2025  
**API Version**: WebSocket v1.0, REST v1.0, Audio v1.0

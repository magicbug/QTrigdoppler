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

## 💡 Tips and Best Practices

### Performance
- **Regular Restarts**: Restart servers periodically for optimal performance
- **Resource Monitoring**: Monitor CPU and memory usage
- **Network Quality**: Ensure stable network connections

### Reliability  
- **Backup Configurations**: Keep backup copies of working configurations
- **Redundant Systems**: Consider multiple access methods
- **Health Monitoring**: Implement uptime monitoring

### User Experience
- **Bookmark URLs**: Save frequently used server addresses
- **Test Connectivity**: Verify connections before important operations
- **Document Setup**: Keep notes on your specific configuration

---

**Remote Operation Guide Version**: 1.0  
**Compatible with**: QTRigdoppler v1.0+  
**Last Updated**: January 2025  
**API Version**: WebSocket v1.0, REST v1.0

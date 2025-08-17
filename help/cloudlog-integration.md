# Cloudlog/Wavelog Integration

Complete guide to automatic logging integration with Cloudlog and Wavelog logbook software.

## 📡 Overview

QTRigdoppler provides seamless integration with [Cloudlog](https://cloudlog.co.uk/) and [Wavelog](https://www.wavelog.org/) logbook software through their REST APIs. This feature automatically sends frequency, mode, and satellite information to your logbook whenever you select a new transponder during satellite operations.

### Features
- **Automatic Logging**: Sends data when transponders are selected
- **Frequency Synchronization**: Transmits both TX and RX frequencies
- **Mode Conversion**: Automatically converts modes for compatibility
- **Real-time Updates**: Immediate logging during satellite passes
- **Error Handling**: Comprehensive logging and error reporting
- **API Compatibility**: Works with both Cloudlog and Wavelog APIs

## 🔧 Configuration

### Basic Setup

Add the following section to your `config.ini` file:

```ini
[Cloudlog]
enabled = True                          # Enable/disable integration
api_key = YOUR_API_KEY_HERE            # Your API key
url = https://your.cloudlog.site       # Your logbook URL
```

### Configuration Parameters

| Setting | Type | Required | Description | Example |
|---------|------|----------|-------------|---------|
| `enabled` | bool | Yes | Enable Cloudlog integration | `True`/`False` |
| `api_key` | string | Yes | Your API key from Cloudlog/Wavelog | `abc123def456` |
| `url` | string | Yes | Base URL of your installation | `https://log.example.com` |

### Obtaining Your API Key

#### For Cloudlog
1. **Log into Cloudlog**: Access your Cloudlog installation
2. **Navigate to Settings**: Go to Account Settings or API Settings
3. **Generate API Key**: Create or find your existing API key
4. **Copy Key**: Copy the key to your `config.ini`

#### For Wavelog
1. **Log into Wavelog**: Access your Wavelog installation
2. **Account Settings**: Navigate to your account settings
3. **API Configuration**: Find the API key section
4. **Generate/Copy Key**: Create or copy your API key

### Example Configurations

#### Cloudlog Setup
```ini
[Cloudlog]
enabled = True
api_key = cloudlog_abc123def456ghi789
url = https://mycallsign.cloudlog.co.uk
```

#### Wavelog Setup
```ini
[Cloudlog]
enabled = True
api_key = wavelog_xyz789abc123def456
url = https://log.mycallsign.com
```

#### Self-Hosted Setup
```ini
[Cloudlog]
enabled = True
api_key = local_api_key_here
url = https://192.168.1.100/cloudlog
```

## 🚀 How It Works

### Automatic Data Transmission

The integration automatically sends data when:
- **Transponder Selection**: When you select a new transponder
- **Satellite Changes**: When switching between satellites
- **Mode Changes**: When transponder modes are different

### Data Sent to Logbook

The following information is transmitted:

| Field | Description | Source |
|-------|-------------|--------|
| **TX Frequency** | Uplink frequency in Hz | Satellite database + doppler |
| **RX Frequency** | Downlink frequency in Hz | Satellite database + doppler |
| **TX Mode** | Uplink mode | Transponder configuration |
| **RX Mode** | Downlink mode | Transponder configuration |
| **Satellite Name** | Current satellite | Selected satellite |
| **Timestamp** | Current date/time | System time |

### Mode Conversion

QTRigdoppler automatically converts modes for compatibility:

| QTRigdoppler Mode | Sent to Logbook | Description |
|-------------------|-----------------|-------------|
| `FMN` | `FM` | Narrow FM becomes standard FM |
| `USB` | `USB` | Upper sideband (unchanged) |
| `LSB` | `LSB` | Lower sideband (unchanged) |
| `CW` | `CW` | Continuous wave (unchanged) |
| `FM` | `FM` | Standard FM (unchanged) |

### API Endpoint

The integration uses the standard Cloudlog/Wavelog API endpoint:
- **URL Pattern**: `{your_url}/index.php/api/radio`
- **Method**: POST
- **Content-Type**: application/x-www-form-urlencoded

## 📊 Usage Examples

### Typical Workflow

1. **Start QTRigdoppler**: Application loads with Cloudlog integration enabled
2. **Select Satellite**: Choose a satellite from the list
3. **Select Transponder**: Choose specific transponder/mode
4. **Automatic Logging**: Data is automatically sent to your logbook
5. **Confirmation**: Check application logs for successful transmission

### What Gets Logged

When you select the "Mode V/U" transponder on AO-7:

```
Sent to Cloudlog:
- TX Freq: 145,950,000 Hz (2m)
- RX Freq: 435,150,000 Hz (70cm) 
- TX Mode: USB
- RX Mode: USB
- Satellite: AO-7
- Time: 2025-01-15 14:30:00 UTC
```

### Integration with Satellite Operations

The logging happens seamlessly during normal operations:

1. **Pre-Pass Setup**: Select satellite and transponder before AOS
2. **Automatic Logging**: Frequencies logged when transponder selected
3. **Real-time Updates**: Changes logged if you switch transponders
4. **Post-Pass**: Log entries available in your logbook immediately

## 🔍 Monitoring and Troubleshooting

### Log Monitoring

Cloudlog integration activity is logged in the application logs:

```
[INFO] Cloudlog API: Sending data for AO-7 Mode V/U
[INFO] Cloudlog API: Successfully logged to Cloudlog
[ERROR] Cloudlog API: Failed to send data - Check API key
```

### Common Issues and Solutions

#### Authentication Errors
```
Problem: "401 Unauthorized" or "Invalid API key"
Solutions:
- Verify API key is correct in config.ini
- Check API key hasn't expired in Cloudlog/Wavelog
- Ensure no extra spaces in API key
- Regenerate API key if necessary
```

#### Network Connectivity Issues
```
Problem: "Connection timeout" or "Network unreachable"
Solutions:
- Check internet connectivity
- Verify URL is correct and accessible
- Check firewall settings
- Test URL in browser: https://your.cloudlog.site
```

#### SSL Certificate Problems
```
Problem: "SSL certificate verification failed"
Solutions:
- Ensure URL uses HTTPS for SSL sites
- Check certificate validity
- Contact logbook host if certificate issues persist
```

#### Data Format Errors
```
Problem: "Invalid data format" or "Missing required fields"
Solutions:
- Check satellite data file (doppler.sqf) format
- Verify transponder definitions are complete
- Review application logs for specific field errors
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```ini
[logging]
level = DEBUG
console_output = True
```

This will show detailed API requests and responses in the console.

### Testing Configuration

Test your configuration:

1. **Enable Integration**: Set `enabled = True`
2. **Select Test Satellite**: Choose a well-known satellite like AO-7
3. **Select Transponder**: Choose any transponder mode
4. **Check Logs**: Look for success/error messages
5. **Verify in Logbook**: Check if entry appears in Cloudlog/Wavelog

## 🛡️ Security Considerations

### API Key Security
- **Keep Private**: Never share your API key publicly
- **Config File Permissions**: Secure your `config.ini` file permissions
- **Regular Rotation**: Consider rotating API keys periodically
- **Backup Safely**: Store API key backups securely

### Network Security
- **HTTPS Recommended**: Use HTTPS URLs when possible
- **Firewall Rules**: Configure appropriate firewall rules
- **VPN Access**: Consider VPN for enhanced security
- **Monitor Access**: Monitor API access logs in your logbook

## 🔧 Advanced Configuration

### Custom API Endpoints

For custom installations, you may need to adjust the API endpoint:

```ini
[Cloudlog]
enabled = True
api_key = your_key_here
url = https://custom.logbook.site/custom/path
```

### Rate Limiting

The integration respects API rate limits:
- **Single Request per Transponder**: One API call per transponder selection
- **No Bulk Updates**: Avoids overwhelming the API
- **Error Backoff**: Delays retries on errors

### Integration with Other Tools

The Cloudlog integration works alongside other QTRigdoppler features:
- **Web API**: Remote control doesn't interfere with logging
- **Pass Recording**: Audio recording works independently
- **Rotator Control**: Antenna positioning integrated seamlessly

## 📚 API Reference

### Request Format

The integration sends POST requests with the following data:

```
POST /index.php/api/radio
Content-Type: application/x-www-form-urlencoded

key=YOUR_API_KEY
&radio_freq_tx=145950000
&radio_freq_rx=435150000
&radio_mode_tx=USB
&radio_mode_rx=USB
&sat_name=AO-7
```

### Response Handling

The integration handles these API responses:

| Response Code | Meaning | Action |
|---------------|---------|--------|
| 200 | Success | Log successful transmission |
| 401 | Unauthorized | Log API key error |
| 403 | Forbidden | Log permission error |
| 404 | Not Found | Log endpoint error |
| 500 | Server Error | Log server error |

## 💡 Tips and Best Practices

### Optimization
- **Pre-Configure**: Set up integration before operating sessions
- **Test Connectivity**: Verify connection before important operations
- **Monitor Logs**: Regular log monitoring for issues

### Workflow Integration
- **Contest Operation**: Automatic logging during contests
- **DXpedition Support**: Seamless logging for DXpeditions
- **Multi-Operator**: Shared logbook for multi-operator stations

### Data Management
- **Regular Backups**: Backup your logbook data regularly
- **Data Verification**: Periodically verify logged data accuracy
- **Duplicate Prevention**: Monitor for duplicate entries

### Performance
- **Network Quality**: Ensure stable internet connection
- **API Limits**: Respect logbook service API limits
- **Error Recovery**: Handle temporary network outages gracefully

## 🔄 Integration Workflow

### Setup Phase
1. **Install Cloudlog/Wavelog**: Set up your logbook software
2. **Obtain API Key**: Generate API key in logbook settings
3. **Configure QTRigdoppler**: Add configuration to `config.ini`
4. **Test Integration**: Verify connectivity and data flow

### Operational Phase
1. **Start Session**: Begin satellite operations
2. **Select Operations**: Choose satellites and transponders
3. **Monitor Logging**: Watch for successful API calls
4. **Review Logs**: Check logbook for accurate entries

### Maintenance Phase
1. **Monitor Performance**: Regular performance monitoring
2. **Update Credentials**: Rotate API keys as needed
3. **Software Updates**: Keep both systems updated
4. **Backup Data**: Regular data backups

---

**Cloudlog/Wavelog Integration Guide Version**: 1.0  
**Compatible with**: Cloudlog 2.x+, Wavelog 1.x+  
**Last Updated**: January 2025  
**API Compatibility**: Cloudlog REST API v1

# QTRigdoppler Keyboard Shortcuts

This document describes all available keyboard shortcuts in QTRigdoppler for improved accessibility and efficiency.

## 🚀 Tracking Control

| Key | Action | Description | Requirements |
|-----|--------|-------------|--------------|
| **T** | Start Tracking | Begins satellite doppler tracking | • Satellite selected<br>• Transponder selected<br>• TLE data available<br>• Not already tracking |
| **S** | Stop Tracking | Stops current tracking session | • Currently tracking |
| **Esc** | Stop Tracking | Alternative way to stop tracking | • Currently tracking |
| **Space** | Toggle Tracking | Start if stopped, stop if tracking | • Satellite/transponder configured for start |

## 📡 System Operations

| Key | Action | Description | Requirements |
|-----|--------|-------------|--------------|
| **R** | Refresh TLE Data | Updates satellite orbital data | • Network connection<br>• TLE URL configured |
| **M** | Memory to VFO | Syncs stored frequencies to radio | • Satellite selected<br>• Not tracking |
| **F5** | Refresh Status | Updates all status displays | • None |

## 🎛️ Rotator Control

| Key | Action | Description | Requirements |
|-----|--------|-------------|--------------|
| **P** | Park Rotators | Parks antenna rotators safely | • Rotator system enabled |
| **F** | Toggle Frequency Pause | Pause/resume frequency updates while keeping rotator tracking | • Rotator system enabled<br>• Currently tracking |

## ⚙️ Configuration

| Key | Action | Description | Requirements |
|-----|--------|-------------|--------------|
| **Ctrl+S** | Save Settings | Saves current configuration | • None |

## 📋 How to Use Keyboard Shortcuts

### Quick Start Workflow

1. **Select a Satellite**: Choose your target satellite from the dropdown menu
2. **Select a Transponder**: Choose the appropriate transponder/frequency
3. **Press 'T' or 'Space'**: Start tracking with either key
4. **Press 'S', 'Esc', or 'Space'**: Stop tracking when done

### Common Operations

- **Start Tracking**: Press **T** or **Space** when satellite/transponder selected
- **Stop Tracking**: Press **S**, **Esc**, or **Space** while tracking
- **Quick Toggle**: Use **Space** to toggle between start/stop states
- **Update Data**: Press **R** to refresh TLE orbital data
- **Sync Radio**: Press **M** to sync memory frequencies to VFO
- **Save Work**: Press **Ctrl+S** to save current settings
- **Refresh Display**: Press **F5** to update all status indicators
- **Park Rotators**: Press **P** to safely park antenna rotators

All shortcuts include intelligent validation and will only work when appropriate conditions are met. Check the application logs for helpful feedback messages.

## 🔧 Accessibility Features

### Visual Feedback
- Log messages provide clear feedback when shortcuts are used
- Error messages explain why a shortcut cannot be executed

### Screen Reader Compatibility
- All keyboard shortcuts work with standard screen reader software
- Log messages are accessible to assistive technologies

## 🌟 Advanced Usage Tips

### Power User Workflows

- **Quick Satellite Change**: Select new satellite → Press **R** to update TLE → Press **T** to start
- **Emergency Stop**: **Esc** provides quick emergency stop for tracking
- **Status Check**: **F5** refreshes all displays if something looks outdated
- **Save Before Exit**: **Ctrl+S** to save settings before closing application

### Rotator Operations

- **Safe Parking**: **P** parks rotators when satellite goes below horizon
- **Manual Control**: Use **P** to park rotators manually when needed
- **Frequency Pause**: **F** pauses frequency updates while keeping rotator tracking for manual frequency control on newer satellites

### Memory Management

- **Frequency Sync**: **M** syncs stored frequencies back to radio VFO
- **Setting Backup**: **Ctrl+S** saves current configuration including offsets

## 🆘 Troubleshooting

### Keyboard Shortcuts Not Working?

If keyboard shortcuts don't respond, check these common issues:

#### Start Tracking (T, Space)
1. **Satellite Selected**: Make sure you've selected a satellite from the dropdown
2. **Transponder Selected**: Ensure a transponder is chosen
3. **TLE Data**: Verify TLE data is loaded (check TLE status indicator)
4. **Already Tracking**: You cannot start tracking if already in progress
5. **Radio Connection**: Ensure your radio is connected

#### Stop Tracking (S, Esc, Space)
1. **Not Tracking**: Must be actively tracking to stop
2. **System Ready**: Wait for tracking to fully initialize before stopping

#### Other Operations
1. **Window Focus**: Click on the main window to ensure keyboard focus
2. **Button State**: Check if the corresponding button is enabled in the GUI
3. **System State**: Some shortcuts require specific system conditions (rotator enabled, etc.)

### Getting Help

- **Log Messages**: Check the application logs for detailed feedback
- **Status Indicators**: Monitor the status displays for system state
- **Documentation**: Refer to the main README.md for setup help

## 🌟 Tips for Efficient Use

1. **Lightning Fast Workflow**: Select satellite → Select transponder → Press **T** or **Space**
2. **Quick Stop**: Use **Esc** for emergency stops, **S** for normal stops
3. **Toggle Mode**: **Space** bar intelligently starts or stops based on current state
4. **Data Updates**: **R** to refresh TLE data, **F5** to refresh all displays
5. **Keyboard Navigation**: Use Tab to navigate between controls, shortcuts for actions
6. **Focus Management**: Click on the main window to ensure keyboard focus for shortcuts
7. **Rotator Efficiency**: **P** to quickly park rotators when needed
8. **Save Frequently**: **Ctrl+S** to save settings, especially after configuration changes
9. **Log Monitoring**: Keep an eye on log messages for detailed shortcut feedback

## 📞 Accessibility Support

QTRigdoppler is committed to accessibility. If you encounter any issues with keyboard shortcuts or need additional accessibility features:

- Check the [project issues](https://github.com/magicbug/QTrigdoppler/issues) for known accessibility topics
- Create a new issue for accessibility improvements
- Refer to the TODO.md file for planned accessibility enhancements

---

**Version**: 1.0  
**Last Updated**: 2025  
**Compatibility**: All supported QTRigdoppler versions 
# Enhanced Rotator Control with 450° Optimization

## Overview

The enhanced rotator control system for QTrigDoppler adds intelligent look-ahead capabilities and 450-degree azimuth optimization to improve satellite tracking performance. This system automatically predicts satellite passes and optimizes rotator movement to minimize mechanical wear and provide smoother tracking.

## Key Features

### 🔄 450-Degree Azimuth Support
- Full support for rotators with 450° azimuth range
- Intelligent path planning that considers the extended range
- Automatic selection of optimal routing (direct vs. wraparound)

### 🔮 Look-Ahead Prediction
- Predicts satellite passes up to 20 minutes in advance
- Calculates optimal rotator positioning before tracking starts
- Pre-positions rotator for maximum efficiency

### 🎯 Route Optimization
- Tests multiple routing strategies for each pass
- Selects the path that minimizes total rotation
- Considers current rotator position in optimization

### 🤖 Automatic Operation
- No user intervention required
- Integrates seamlessly with existing tracking workflow
- Real-time status updates in the UI

## How It Works

### 1. Pass Prediction
When tracking starts, the system:
- **Only optimizes when satellite is visible or approaching horizon** (≥-3° elevation)
- Calculates satellite position every 10 seconds for the next 20 minutes (configurable)
- Filters for the visible portion of the pass (above minimum elevation)
- Creates a timeline of azimuth/elevation coordinates
- **Automatically re-predicts** if no optimization exists and satellite is approaching horizon (-3° to 0°)
- **Triggers prediction at -3° elevation** when satellite approaches minimum elevation threshold
- **Clears optimization data** when satellite goes below -10° elevation

### 2. Route Optimization
The optimizer tests different strategies:
- **Forward (natural)**: Start at the first azimuth position (0-360°)
- **Reverse (450°)**: Begin at first_azimuth + 360° (if within 450° range)
- Considers current rotator position for pre-positioning calculations
- Generates optimized route segments with azimuths that may exceed 360°

### 3. Strategy Selection
The system selects the strategy that minimizes:
- Total rotation distance during the pass
- Pre-positioning distance from current position
- Combined movement for the entire tracking session

### 4. Pre-positioning
If beneficial (>10 degrees difference from current position), the rotator moves to the optimal starting position.

### 5. Real-time Tracking
During tracking, the system:
- Uses optimized route segments when available
- Falls back to raw satellite azimuth when no optimization data exists
- Applies 450° logic only to unoptimized azimuths (0-360° range)
- **Maintains 1° tracking accuracy** for both azimuth and elevation
- **Optimizes route timing** by predicting at -3° elevation for maximum accuracy
- **Pre-positioning window**: Only uses optimized start azimuth when satellite is between -3° and minimum elevation
- **Below horizon**: Uses raw satellite azimuth when satellite is below -3° elevation
- **Efficient optimization**: Only generates route segments when satellite is ≥-3° elevation
- **Memory management**: Clears optimization data when satellite goes below -10° elevation

## Example Scenarios

### Scenario 1: Traditional vs. Optimized
**Satellite pass**: 30° → 200° (typical west-to-east pass)
**Current position**: 350°

**Traditional approach**:
- 350° → 30° = 40° rotation
- Track normally through pass
- Total: ~210° rotation

**Optimized approach**:
- Pre-position to 390° (30° + 360°)
- Track smoothly: 390° → 560° (200° + 360°)
- Total: ~170° rotation
- **Savings**: 40° less rotation
- **Key**: Rotator receives optimized azimuths >360° directly

### Scenario 2: North-South Pass
**Satellite pass**: 350° → 10° (crossing north)
**Current position**: 180°

**Traditional approach**:
- Multiple direction changes
- Inefficient wraparound movements

**Optimized approach**:
- Single smooth arc using 450° range
- Minimal direction changes
- Reduced mechanical stress

## Configuration

### config.ini Settings
```ini
[rotator]
enabled = true
az_max = 450
az_min = 0
el_max = 180
el_min = 0
min_elevation = 5
position_poll_interval = 5.0
```

### Required Hardware
- Rotator capable of 450° azimuth rotation
- Compatible with Yaesu rotator protocol
- Proper calibration for extended range

## User Interface

### Status Indicators
The UI displays optimization status:
- **"Parked"**: Rotator in park position (gray)
- **"Optimized (-X°)"**: Route optimized, X degrees saved (green)
- **"Pre-positioned"**: Rotator moved to optimal start position (orange)
- **"Optimal"**: Current position already optimal (green)
- **"Tracking"**: Satellite above minimum elevation, tracking normally (green)
- **"No Pass"**: No visible pass predicted (gray)
- **"Error"**: Optimization failed (red)

### Visual Feedback
- Real-time azimuth/elevation display
- Optimization status with color coding:
  - Green: Optimal/optimized/Tracking
  - Orange: Pre-positioned
  - Gray: Parked/No Pass
  - Red: Error
- Status updates automatically based on satellite elevation changes

## Benefits

### Mechanical Advantages
- **Reduced wear**: Minimized rotation distance
- **Smoother operation**: Fewer direction changes
- **Extended life**: Less mechanical stress

### Operational Benefits
- **Better tracking**: Smoother satellite following
- **Automatic optimization**: No manual intervention
- **Improved efficiency**: Optimal use of rotator capabilities
- **Reduced serial traffic**: Intelligent position polling reduces unnecessary communication

### User Experience
- **Transparent operation**: Works automatically
- **Clear feedback**: Status updates in UI
- **Reliable tracking**: Predictable rotator behavior
- **Configurable polling**: Adjustable position check frequency

## Technical Implementation

### Core Components

1. **RotatorOptimizer Class** (`lib/rotator_optimizer.py`)
   - Pass prediction algorithms (15-minute default look-ahead)
   - Route optimization logic with Forward/Reverse strategies
   - Pre-positioning recommendations (>10° threshold)
   - 450° azimuth range calculations

2. **Enhanced MainWindow** (`QTrigdoppler.py`)
   - Integration with existing tracking system
   - UI updates and status display
   - Automatic optimization triggers on tracking start
   - Real-time optimization status updates
   - **Intelligent position polling** based on tracking state

3. **Improved Rotator Control** (`lib/rotator.py`)
   - 450° range support with position caching
   - Intelligent azimuth calculation using optimizer
   - Enhanced position management with thread safety
   - Real-time route segment lookup for optimized tracking
   - **Adaptive position checking** frequency based on movement and satellite visibility

### Algorithm Details

#### Pass Prediction
```python
def predict_satellite_pass(ephemdata, myloc, duration_minutes=15, interval_seconds=5):
    # Calculate satellite positions over time
    # Filter for visible elevations
    # Return time-series of azimuth/elevation
```

#### Route Optimization
```python
def optimize_pass_route(visible_predictions, current_rotator_az=None):
    # Test Forward (natural) and Reverse (450°) strategies
    # Calculate total rotation for each including pre-positioning
    # Select minimum-rotation path
```

#### Pre-positioning Logic
```python
def get_pre_positioning_recommendation(predictions, current_az):
    # Determine if pre-positioning is beneficial
    # Calculate optimal starting position
    # Consider time until AOS
```

## Example Usage

### Basic Operation
1. Configure rotator for 450° range in `config.ini`
2. Select satellite and transponder
3. Click "Start Tracking"
4. System automatically optimizes and tracks (20-minute look-ahead, 10-second intervals)
5. **If no pass is predicted, system re-checks every 5 minutes**
6. **When satellite reaches -3° elevation, system triggers fresh prediction before AOS**

### Monitoring
- Watch optimization status in UI
- Check logs for detailed optimization information
- Monitor rotator position display

### Troubleshooting
- Ensure rotator supports 450° range
- Verify configuration settings
- Check serial communication
- Review log files for errors
- **If no pass is detected, wait 5 minutes for automatic re-check**
- **Check logs for "🔄 Re-running satellite pass prediction..." messages**
- **Check logs for "🛰 Satellite at -3.0° - triggering route prediction before AOS" messages**
- **Monitor position polling frequency in logs for performance optimization**

## Compatibility

### Supported Rotators
- Yaesu rotators with 450° azimuth capability
- Compatible rotators using Yaesu protocol
- Custom rotators with appropriate interface

## Support

### Getting Help
- Check configuration settings
- Review log files for errors
- Verify rotator hardware compatibility
- Test with demonstration script

### Common Issues
- **Rotator not responding**: Check serial connection
- **Optimization not working**: Verify 450° support
- **Incorrect positioning**: Calibrate rotator range
- **Status not updating**: Check UI refresh rate

## Position Polling Optimization

### Intelligent Polling Strategy

The system uses **adaptive position polling** to minimize serial communication while maintaining responsive tracking:

#### Polling Intervals
- **UI Position Worker**: Configurable base interval (default: 5 seconds)
  - **When tracking**: Polls every 2 seconds maximum
  - **When not tracking**: Polls every 10 seconds minimum
- **Rotator Thread**: Adaptive based on satellite visibility and movement
  - **Satellite visible (≥5°)**: Polls every 1 second
  - **Satellite approaching horizon (-10° to 5°)**: Polls every 3 seconds
  - **Satellite well below horizon (<-10°)**: Polls every 10 seconds
  - **Rotator moving**: Polls every 0.5 seconds
  - **Rotator stationary**: Polls every 2 seconds

#### Position Caching
- **Cache timeout**: 500ms to reduce serial calls
- **Cache invalidation**: After position commands or cache timeout
- **Fallback queries**: Individual AZ/EL queries if combined query fails

#### Configuration
```ini
[rotator]
position_poll_interval = 5.0  # Base polling interval in seconds
```

### Performance Benefits
- **Reduced serial traffic**: Up to 80% fewer position queries when not tracking
- **Responsive tracking**: Fast polling when satellite is visible
- **Battery friendly**: Slower polling when rotator is stationary
- **Configurable**: Adjust polling frequency based on hardware capabilities
- **Reduced log noise**: Intelligent logging that only reports significant changes

## Conclusion

The enhanced rotator control system brings intelligent automation to satellite tracking, optimizing rotator movement for better performance and longer equipment life. By leveraging 450-degree azimuth capability and predictive algorithms, it provides a superior tracking experience with minimal user intervention.

The system is designed to be transparent and automatic, working seamlessly with existing QTrigDoppler workflows while providing significant improvements in tracking efficiency and rotator longevity.
import ephem
import math
from datetime import datetime, timedelta, timezone
import logging
import numpy as np
from .sat_utils import sat_azi_calc, sat_ele_calc

class RotatorOptimizer:
    """
    Optimizes rotator movement for satellite passes with 450-degree support
    """
    
    def __init__(self, az_min=0, az_max=450, min_elevation=5):
        self.az_min = az_min
        self.az_max = az_max
        self.min_elevation = min_elevation
        
    def detect_pass_characteristics(self, ephemdata, myloc, scan_duration_minutes=90, scan_interval_seconds=60):
        """
        Perform a quick scan to detect pass characteristics for adaptive optimization
        
        Args:
            ephemdata: Satellite ephemeris data
            myloc: Observer location
            scan_duration_minutes: How far ahead to scan (default 90 minutes)
            scan_interval_seconds: Scan interval for quick detection (default 60 seconds)
            
        Returns:
            Dictionary with pass characteristics or None if no pass detected
        """
        try:
            # Quick scan with coarse intervals to find the full pass
            predictions = self._predict_satellite_positions(
                ephemdata, myloc, 
                duration_minutes=scan_duration_minutes,
                interval_seconds=scan_interval_seconds
            )
            
            visible_predictions = self.filter_visible_pass(predictions)
            
            if not visible_predictions:
                return None
            
            # Calculate pass characteristics
            aos_time = visible_predictions[0][0]
            los_time = visible_predictions[-1][0]
            pass_duration = (los_time - aos_time).total_seconds() / 60  # minutes
            max_elevation = max(pred[2] for pred in visible_predictions)
            
            # Calculate azimuth range to detect north crossings
            azimuths = [pred[1] for pred in visible_predictions]
            az_range = max(azimuths) - min(azimuths)
            crosses_north = any(abs(self.normalize_azimuth(azimuths[i]) - self.normalize_azimuth(azimuths[i-1])) > 180 
                               for i in range(1, len(azimuths)))
            
            return {
                'aos_time': aos_time,
                'los_time': los_time,
                'duration_minutes': pass_duration,
                'max_elevation': max_elevation,
                'azimuth_range': az_range,
                'crosses_north': crosses_north,
                'visible_predictions': visible_predictions
            }
            
        except Exception as e:
            logging.error(f"Error detecting pass characteristics: {e}")
            return None

    def get_adaptive_prediction_params(self, pass_characteristics=None):
        """
        Calculate adaptive prediction parameters based on pass characteristics
        
        Args:
            pass_characteristics: Dictionary from detect_pass_characteristics()
            
        Returns:
            Dictionary with duration_minutes and interval_seconds
        """
        # Default fallback parameters (current behavior)
        default_params = {
            'duration_minutes': 20,
            'interval_seconds': 10,
            'reason': 'Using default parameters (no pass characteristics available)'
        }
        
        if not pass_characteristics:
            return default_params
        
        duration = pass_characteristics['duration_minutes']
        max_elevation = pass_characteristics['max_elevation']
        crosses_north = pass_characteristics['crosses_north']
        
        # Adaptive duration: Add buffer based on pass length
        if duration < 5:  # Very short pass
            prediction_duration = max(8, duration + 4)  # Minimum 8 minutes, add 4 min buffer
            interval = 5  # High precision for short passes
            reason = f"Short pass ({duration:.1f}min): Using high precision tracking"
        elif duration < 10:  # Short pass
            prediction_duration = duration + 6  # Add 6 min buffer
            interval = 6  # Good precision
            reason = f"Short pass ({duration:.1f}min): Using enhanced precision"
        elif duration < 18:  # Medium pass
            prediction_duration = duration + 8  # Add 8 min buffer
            interval = 8  # Standard precision
            reason = f"Medium pass ({duration:.1f}min): Using standard precision"
        else:  # Long pass
            prediction_duration = duration + 10  # Add 10 min buffer
            interval = 10  # Coarser intervals for efficiency
            reason = f"Long pass ({duration:.1f}min): Using efficient tracking"
        
        # Adjust for elevation - high elevation passes need more precision
        if max_elevation > 60:
            interval = max(3, interval - 3)  # Finer intervals for high passes
            reason += f" + high elevation ({max_elevation:.1f}°): increased precision"
        elif max_elevation < 15:
            interval = min(15, interval + 5)  # Coarser for very low passes
            reason += f" + low elevation ({max_elevation:.1f}°): reduced precision"
        
        # Adjust for north crossings - need finer intervals for smooth tracking
        if crosses_north:
            interval = max(5, interval - 2)  # Finer intervals for north crossings
            reason += " + north crossing: enhanced precision"
        
        # Ensure reasonable bounds
        prediction_duration = max(8, min(45, prediction_duration))  # 8-45 minute range
        interval = max(3, min(15, interval))  # 3-15 second range
        
        return {
            'duration_minutes': prediction_duration,
            'interval_seconds': interval,
            'reason': reason
        }

    def predict_satellite_pass_adaptive(self, ephemdata, myloc):
        """
        Predict satellite pass using adaptive parameters based on pass characteristics
        
        Args:
            ephemdata: Satellite ephemeris data
            myloc: Observer location
            
        Returns:
            List of (time, azimuth, elevation) tuples with adaptive precision
        """
        # Step 1: Detect pass characteristics
        pass_characteristics = self.detect_pass_characteristics(ephemdata, myloc)
        
        # Step 2: Get adaptive parameters
        adaptive_params = self.get_adaptive_prediction_params(pass_characteristics)
        
        # Step 3: Log the adaptive decision
        logging.info(f"🎯 Adaptive prediction: {adaptive_params['reason']}")
        logging.debug(f"   Parameters: {adaptive_params['duration_minutes']:.1f}min window, {adaptive_params['interval_seconds']}s intervals")
        
        # Step 4: Run high-precision prediction with adaptive parameters
        return self._predict_satellite_positions(
            ephemdata, myloc,
            duration_minutes=adaptive_params['duration_minutes'],
            interval_seconds=adaptive_params['interval_seconds']
        )

    def _predict_satellite_positions(self, ephemdata, myloc, duration_minutes=15, interval_seconds=5):
        """
        Internal method to predict satellite positions over time
        (Renamed from predict_satellite_pass to avoid confusion with adaptive version)
        
        Args:
            ephemdata: Satellite ephemeris data
            myloc: Observer location
            duration_minutes: How far ahead to predict
            interval_seconds: Prediction interval
            
        Returns:
            List of (time, azimuth, elevation) tuples
        """
        predictions = []
        current_time = datetime.now(timezone.utc)
        
        for i in range(0, int(duration_minutes * 60), int(interval_seconds)):
            future_time = current_time + timedelta(seconds=i)
            
            # Set location time
            temp_loc = myloc.copy()
            temp_loc.date = ephem.Date(future_time.strftime('%Y/%m/%d %H:%M:%S.%f')[:-3])
            
            # Calculate satellite position
            ephemdata.compute(temp_loc)
            
            az = ephemdata.az * 180.0 / math.pi
            el = ephemdata.alt * 180.0 / math.pi
            
            predictions.append((future_time, az, el))
            
        return predictions

    def predict_satellite_pass(self, ephemdata, myloc, duration_minutes=15, interval_seconds=5):
        """
        Predict satellite position over time (legacy method for backward compatibility)
        
        For new code, consider using predict_satellite_pass_adaptive() for better performance
        
        Args:
            ephemdata: Satellite ephemeris data
            myloc: Observer location
            duration_minutes: How far ahead to predict (default 15 minutes)
            interval_seconds: Prediction interval (default 5 seconds)
            
        Returns:
            List of (time, azimuth, elevation) tuples
        """
        return self._predict_satellite_positions(ephemdata, myloc, duration_minutes, interval_seconds)
    
    def filter_visible_pass(self, predictions):
        """
        Filter predictions to only include when satellite is above minimum elevation
        
        Args:
            predictions: List of (time, azimuth, elevation) tuples
            
        Returns:
            List of (time, azimuth, elevation) tuples for visible portion
        """
        visible = []
        for time, az, el in predictions:
            if el >= self.min_elevation:
                visible.append((time, az, el))
        return visible
    
    def normalize_azimuth(self, azimuth):
        """Normalize azimuth to 0-360 range"""
        return azimuth % 360
    
    def calculate_rotation_distance(self, from_az, to_az):
        """
        Calculate the shortest rotation distance between two azimuths
        considering 450-degree capability.

        Args:
            from_az: Starting azimuth (current rotator position, can be > 360)
            to_az: Target azimuth (from satellite prediction, 0-360)

        Returns:
            Tuple of (actual_distance, optimal_target_azimuth)
        """
        # The target azimuth from ephem is always 0-360. We need to find the
        # equivalent angle in our rotator's full range that is closest to from_az.
        possible_targets = [to_az]
        
        # Check wraparound target forwards (e.g., 10 deg -> 370 deg)
        if (to_az + 360) <= self.az_max:
            possible_targets.append(to_az + 360)
            
        # Check wraparound target backwards (e.g., 350 deg -> -10 deg)
        if (to_az - 360) >= self.az_min:
            possible_targets.append(to_az - 360)

        # Find the target that requires the minimum rotation from current position
        distances = [(abs(target - from_az), target) for target in possible_targets]
        
        # Return the one with the shortest distance
        return min(distances, key=lambda x: x[0])
    
    def optimize_pass_route(self, visible_predictions, current_rotator_az=None):
        """
        Optimize the rotator route for the entire satellite pass, considering both directions (forward and reverse) and 450-degree support.
        Always prefer wraparound (Reverse 450°) if the pass crosses north (azimuths cross 0°/360°).
        """
        if not visible_predictions:
            return {
                'optimal_start_az': None,
                'total_rotation': 0,
                'route_segments': [],
                'recommendation': 'No visible pass predicted'
            }
        azimuths = [pred[1] for pred in visible_predictions]
        if len(azimuths) < 2:
            return {
                'optimal_start_az': azimuths[0],
                'total_rotation': 0,
                'route_segments': visible_predictions,
                'recommendation': 'Single point pass'
            }
        strategies = []
        # Forward (natural) direction
        start_az = azimuths[0]  # Use original azimuth, don't normalize
        total_rotation_fwd = self._calculate_total_rotation(azimuths, start_az)
        strategies.append({
            'strategy': 'Forward (natural)',
            'start_az': start_az,
            'total_rotation': total_rotation_fwd
        })
        # Reverse direction (using 450°)
        reverse_strategy = None
        if self.az_max > 360:
            start_az_rev = azimuths[0] + 360
            if start_az_rev <= self.az_max:
                total_rotation_rev = self._calculate_total_rotation(azimuths, start_az_rev)
                reverse_strategy = {
                    'strategy': 'Reverse (450°)',
                    'start_az': start_az_rev,
                    'total_rotation': total_rotation_rev
                }
                strategies.append(reverse_strategy)
        
        # --- North-crossing detection ---
        # If azimuths cross 0/360, always prefer Reverse (450°) for smoothness
        crosses_north = False
        north_crossing_points = []
        for i in range(1, len(azimuths)):
            diff = abs(self.normalize_azimuth(azimuths[i]) - self.normalize_azimuth(azimuths[i-1]))
            if diff > 180:
                crosses_north = True
                north_crossing_points.append(i)
        
        # Smart north-crossing strategy: If reverse strategy doesn't work, try to use 450° range more intelligently
        smart_strategy = None
        if crosses_north and reverse_strategy is None and self.az_max > 360:
            # Create a strategy that uses 450° range for the end portion of the pass
            smart_strategy = self._create_smart_north_crossing_strategy(azimuths, north_crossing_points)
            if smart_strategy:
                strategies.append(smart_strategy)
                
        # If we know current rotator position, factor that in
        if current_rotator_az is not None:
            for strategy in strategies:
                pre_rotation = abs(strategy['start_az'] - current_rotator_az)
                strategy['total_with_pre_rotation'] = strategy['total_rotation'] + pre_rotation
        # Log strategies only at DEBUG level (was too verbose)
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Testing rotator strategies for pass starting at {azimuths[0]:.1f}°:")
            for strategy in strategies:
                if 'total_with_pre_rotation' in strategy:
                    logging.debug(f"  {strategy['strategy']}: start={strategy['start_az']:.1f}°, rotation={strategy['total_rotation']:.1f}°, total={strategy['total_with_pre_rotation']:.1f}°")
                else:
                    logging.debug(f"  {strategy['strategy']}: start={strategy['start_az']:.1f}°, rotation={strategy['total_rotation']:.1f}°")
        
        # Strategy selection with priority for north-crossing avoidance
        best_strategy = None
        if crosses_north:
            # Priority 1: Reverse strategy (if available)
            if reverse_strategy is not None:
                best_strategy = reverse_strategy
                logging.info("[Optimizer] Pass crosses north: using Reverse (450°) wraparound for smooth tracking.")
            # Priority 2: Smart north-crossing strategy (if available)
            elif smart_strategy is not None:
                best_strategy = smart_strategy
                logging.info("[Optimizer] Pass crosses north: using Smart (450°) strategy to avoid boundary crossing.")
            # Priority 3: Fall back to best total rotation strategy
            else:
                best_strategy = min(strategies, key=lambda x: x.get('total_with_pre_rotation', x['total_rotation']))
                logging.info("[Optimizer] Pass crosses north but no 450° strategy available: using best rotation strategy.")
        else:
            # Choose the best strategy (default: minimum total rotation)
            best_strategy = min(strategies, key=lambda x: x.get('total_with_pre_rotation', x['total_rotation']))
            
        logging.info(f"Selected strategy: {best_strategy['strategy']} with start azimuth {best_strategy['start_az']:.1f}°")
        
        # Generate route segments using the selected strategy
        route_segments = self._generate_route_segments_with_strategy(visible_predictions, best_strategy)
        
        # Debug: Log route segments only at DEBUG level to reduce verbosity
        if route_segments and logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(f"Generated {len(route_segments)} route segments (first 3):")
            for i, seg in enumerate(route_segments[:3]):  # Only show first 3 instead of 5
                logging.debug(f"  Route segment {i}: {seg['time'].strftime('%H:%M:%S')} -> {seg['target_az']:.1f}°")
            if len(route_segments) > 3:
                logging.debug(f"  ... and {len(route_segments)-3} more segments")
        return {
            'optimal_start_az': best_strategy['start_az'],
            'total_rotation': best_strategy['total_rotation'],
            'route_segments': route_segments,
            'strategies_tested': strategies,
            'recommendation': f"Use {best_strategy['strategy']} - saves rotation",
            'savings': self._calculate_savings(strategies, best_strategy)
        }
    
    def _calculate_total_rotation(self, azimuths, start_az):
        """Calculate total rotation needed for a sequence of azimuths"""
        total = 0
        current_az = start_az
        
        for target_az in azimuths:
            # Find best way to reach target
            distance, optimal_az = self.calculate_rotation_distance(current_az, target_az)
            total += distance
            current_az = optimal_az  # Use the actual optimal azimuth for next calculation
            
        return total
    
    def _generate_route_segments(self, visible_predictions, start_az):
        """Generate optimized route segments"""
        segments = []
        current_az = start_az
        
        for time, target_az, el in visible_predictions:
            distance, optimal_az = self.calculate_rotation_distance(current_az, target_az)
            
            segments.append({
                'time': time,
                'target_az': optimal_az,
                'elevation': el,
                'rotation_distance': distance,
                'cumulative_rotation': sum(s['rotation_distance'] for s in segments) + distance
            })
            
            current_az = optimal_az  # Use the actual optimal azimuth for next calculation
            
        return segments
    
    def _calculate_savings(self, strategies, best_strategy):
        """Calculate rotation savings compared to worst strategy"""
        if len(strategies) <= 1:
            return 0
            
        worst_rotation = max(s['total_rotation'] for s in strategies)
        best_rotation = best_strategy['total_rotation']
        
        return worst_rotation - best_rotation
    
    def get_pre_positioning_recommendation(self, visible_predictions, current_rotator_az=None):
        """
        Get recommendation for pre-positioning the rotator before tracking starts
        
        Args:
            visible_predictions: List of (time, azimuth, elevation) tuples
            current_rotator_az: Current rotator azimuth
            
        Returns:
            Dictionary with pre-positioning recommendation
        """
        if not visible_predictions:
            return {
                'should_preposition': False,
                'recommended_az': None,
                'reason': 'No visible pass predicted'
            }
        
        optimization = self.optimize_pass_route(visible_predictions, current_rotator_az)
        
        if optimization['optimal_start_az'] is None:
            return {
                'should_preposition': False,
                'recommended_az': None,
                'reason': 'No optimization possible'
            }
        
        # Determine if pre-positioning is beneficial
        should_preposition = False
        reason = "Rotator already optimally positioned"
        
        if current_rotator_az is not None:
            distance_to_optimal = abs(optimization['optimal_start_az'] - current_rotator_az)
            
            if distance_to_optimal > 10:  # More than 10 degrees difference
                should_preposition = True
                reason = f"Pre-positioning saves {optimization.get('savings', 0):.1f}° of rotation"
        else:
            should_preposition = True
            reason = "Current rotator position unknown, pre-positioning recommended"
        
        return {
            'should_preposition': should_preposition,
            'recommended_az': optimization['optimal_start_az'],
            'reason': reason,
            'time_until_aos': visible_predictions[0][0] - datetime.now(timezone.utc) if visible_predictions else None,
            'optimization_details': optimization
        }
    
    def _create_smart_north_crossing_strategy(self, azimuths, north_crossing_points):
        """
        Create a smart strategy for north-crossing passes that uses 450° range intelligently
        """
        try:
            # Find the first major north crossing point
            first_crossing = north_crossing_points[0] if north_crossing_points else None
            if first_crossing is None:
                return None
                
            # Create modified azimuth list that uses 450° range after the crossing
            modified_azimuths = azimuths.copy()
            
            # For azimuths after the crossing, try to use the 450° range to avoid boundary crossing
            for i in range(first_crossing, len(modified_azimuths)):
                original_az = modified_azimuths[i]
                # If this azimuth is small (e.g., < 180°), try adding 360° to avoid crossing
                if original_az < 180 and (original_az + 360) <= self.az_max:
                    modified_azimuths[i] = original_az + 360
            
            # Check if this strategy is valid (doesn't exceed rotator limits)
            if max(modified_azimuths) > self.az_max:
                return None
                
            # Calculate total rotation for this strategy
            total_rotation = self._calculate_total_rotation(modified_azimuths, azimuths[0])
            
            return {
                'strategy': 'Smart (450°)',
                'start_az': azimuths[0],
                'total_rotation': total_rotation,
                'modified_azimuths': modified_azimuths
            }
            
        except Exception as e:
            logging.debug(f"Error creating smart north-crossing strategy: {e}")
            return None
    
    def _generate_route_segments_with_strategy(self, visible_predictions, strategy):
        """Generate route segments using the selected strategy"""
        segments = []
        current_az = strategy['start_az']
        
        # Use modified azimuths if this is a smart strategy
        if 'modified_azimuths' in strategy:
            modified_azimuths = strategy['modified_azimuths']
            for i, (time, original_az, el) in enumerate(visible_predictions):
                target_az = modified_azimuths[i]
                distance = abs(target_az - current_az)
                
                segments.append({
                    'time': time,
                    'target_az': target_az,
                    'elevation': el,
                    'rotation_distance': distance,
                    'cumulative_rotation': sum(s['rotation_distance'] for s in segments) + distance
                })
                
                current_az = target_az
        else:
            # Use the original route segment generation
            for time, target_az, el in visible_predictions:
                distance, optimal_az = self.calculate_rotation_distance(current_az, target_az)
                
                segments.append({
                    'time': time,
                    'target_az': optimal_az,
                    'elevation': el,
                    'rotation_distance': distance,
                    'cumulative_rotation': sum(s['rotation_distance'] for s in segments) + distance
                })
                
                current_az = optimal_az
                
        return segments
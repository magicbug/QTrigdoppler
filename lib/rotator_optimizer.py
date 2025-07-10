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
        
    def predict_satellite_pass(self, ephemdata, myloc, duration_minutes=15, interval_seconds=5):
        """
        Predict satellite position over time
        
        Args:
            ephemdata: Satellite ephemeris data
            myloc: Observer location
            duration_minutes: How far ahead to predict (default 15 minutes)
            interval_seconds: Prediction interval (default 5 seconds)
            
        Returns:
            List of (time, azimuth, elevation) tuples
        """
        predictions = []
        current_time = datetime.now(timezone.utc)
        
        for i in range(0, duration_minutes * 60, interval_seconds):
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
        considering 450-degree capability
        
        Args:
            from_az: Starting azimuth
            to_az: Target azimuth
            
        Returns:
            Tuple of (distance, target_azimuth_to_use)
        """
        # Don't normalize inputs - preserve actual azimuth values
        # Only normalize for distance calculations
        
        # Calculate direct distance (normalized for comparison)
        from_az_norm = self.normalize_azimuth(from_az)
        to_az_norm = self.normalize_azimuth(to_az)
        direct_dist = abs(to_az_norm - from_az_norm)
        target_direct = to_az  # Use original target azimuth
        
        # Calculate distances using 450-degree capability
        distances = [(direct_dist, target_direct)]
        
        if self.az_max > 360:
            # Try going the long way (crossing 0/360)
            if to_az_norm > from_az_norm:
                # Going backwards through 0
                long_dist = from_az_norm + (360 - to_az_norm)
                target_long = to_az - 360
            else:
                # Going forwards through 360
                long_dist = (360 - from_az_norm) + to_az_norm
                target_long = to_az + 360
                
            # Only add if the target is within our 450° range
            if target_long <= self.az_max and target_long >= self.az_min:
                distances.append((long_dist, target_long))
        
        # Return the shortest distance option
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
            rev_azimuths = list(reversed(azimuths))
            start_az_rev = azimuths[0] + 360
            if start_az_rev <= self.az_max:
                total_rotation_rev = self._calculate_total_rotation(rev_azimuths, start_az_rev)
                reverse_strategy = {
                    'strategy': 'Reverse (450°)',
                    'start_az': start_az_rev,
                    'total_rotation': total_rotation_rev
                }
                strategies.append(reverse_strategy)
        # If we know current rotator position, factor that in
        if current_rotator_az is not None:
            for strategy in strategies:
                pre_rotation = abs(strategy['start_az'] - current_rotator_az)
                strategy['total_with_pre_rotation'] = strategy['total_rotation'] + pre_rotation
        # Log the strategies being tested
        logging.debug(f"Testing rotator strategies for pass starting at {azimuths[0]:.1f}°:")
        for strategy in strategies:
            if 'total_with_pre_rotation' in strategy:
                logging.debug(f"  {strategy['strategy']}: start={strategy['start_az']:.1f}°, rotation={strategy['total_rotation']:.1f}°, total={strategy['total_with_pre_rotation']:.1f}°")
            else:
                logging.debug(f"  {strategy['strategy']}: start={strategy['start_az']:.1f}°, rotation={strategy['total_rotation']:.1f}°")
        # --- North-crossing detection ---
        # If azimuths cross 0/360, always prefer Reverse (450°) for smoothness
        crosses_north = False
        for i in range(1, len(azimuths)):
            diff = abs(self.normalize_azimuth(azimuths[i]) - self.normalize_azimuth(azimuths[i-1]))
            if diff > 180:
                crosses_north = True
                break
        if crosses_north and reverse_strategy is not None:
            best_strategy = reverse_strategy
            logging.info("[Optimizer] Pass crosses north: forcing Reverse (450°) wraparound for smooth tracking.")
        else:
            # Choose the best strategy (default: minimum total rotation)
            best_strategy = min(strategies, key=lambda x: x.get('total_with_pre_rotation', x['total_rotation']))
        logging.debug(f"Selected strategy: {best_strategy['strategy']} with start azimuth {best_strategy['start_az']:.1f}°")
        # Generate route segments
        if best_strategy['strategy'] == 'Reverse (450°)':
            route_segments = self._generate_route_segments(list(reversed(visible_predictions)), best_strategy['start_az'])
        else:
            route_segments = self._generate_route_segments(visible_predictions, best_strategy['start_az'])
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
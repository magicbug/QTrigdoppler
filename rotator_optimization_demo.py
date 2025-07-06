#!/usr/bin/env python3
"""
Demonstration of Enhanced Rotator Control with 450-degree Optimization
======================================================================

This script demonstrates the improved rotator control system that:
1. Predicts satellite passes using orbital mechanics
2. Optimizes rotator movement using 450-degree capability
3. Pre-positions rotator for optimal tracking

Example scenario: Satellite starts at 30° and ends at 200°
- Without optimization: Multiple direction changes, inefficient movement
- With optimization: Smooth path using 450° range, minimized rotation
"""

import sys
import math
from datetime import datetime, timedelta, timezone
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def simulate_satellite_pass():
    """Simulate a satellite pass from 30° to 200°"""
    print("🛰️ SATELLITE PASS SIMULATION")
    print("=" * 50)
    
    # Example satellite pass: starts at 30°, ends at 200°
    # This is a typical scenario where 450° optimization helps
    
    pass_data = [
        (datetime.now(timezone.utc) + timedelta(seconds=30), 30.0, 10.0),   # AOS
        (datetime.now(timezone.utc) + timedelta(seconds=60), 45.0, 15.0),
        (datetime.now(timezone.utc) + timedelta(seconds=90), 60.0, 20.0),
        (datetime.now(timezone.utc) + timedelta(seconds=120), 90.0, 25.0),
        (datetime.now(timezone.utc) + timedelta(seconds=150), 120.0, 30.0),
        (datetime.now(timezone.utc) + timedelta(seconds=180), 150.0, 25.0),
        (datetime.now(timezone.utc) + timedelta(seconds=210), 180.0, 20.0),
        (datetime.now(timezone.utc) + timedelta(seconds=240), 200.0, 15.0),  # LOS
    ]
    
    print("Pass Timeline:")
    for time, az, el in pass_data:
        print(f"  {time.strftime('%H:%M:%S')}: Az={az:6.1f}°, El={el:4.1f}°")
    
    return pass_data

def demonstrate_optimization_scenarios():
    """Demonstrate different optimization scenarios"""
    print("\n🔄 OPTIMIZATION SCENARIOS")
    print("=" * 50)
    
    # Test scenarios with different current positions
    scenarios = [
        {"name": "Scenario 1: Starting from 90°", "current_pos": 90.0},
        {"name": "Scenario 2: Starting from 350°", "current_pos": 350.0},
        {"name": "Scenario 3: Starting from 180°", "current_pos": 180.0},
    ]
    
    target_sequence = [30.0, 45.0, 60.0, 90.0, 120.0, 150.0, 180.0, 200.0]
    
    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 40)
        
        current_pos = scenario['current_pos']
        
        # Test both traditional and optimized approaches
        print(f"Current rotator position: {current_pos}°")
        print(f"Target sequence: {target_sequence}")
        
        # Traditional approach (limited to 360°)
        traditional_rotation = calculate_traditional_rotation(current_pos, target_sequence)
        print(f"Traditional approach: {traditional_rotation:.1f}° total rotation")
        
        # Optimized approach (450° capability)
        optimized_rotation, optimal_sequence = calculate_optimized_rotation(current_pos, target_sequence)
        print(f"Optimized approach: {optimized_rotation:.1f}° total rotation")
        print(f"Optimal sequence: {optimal_sequence}")
        
        savings = traditional_rotation - optimized_rotation
        print(f"💡 Savings: {savings:.1f}° ({savings/traditional_rotation*100:.1f}%)")

def calculate_traditional_rotation(start_pos, target_sequence):
    """Calculate rotation using traditional 360° approach"""
    total_rotation = 0
    current_pos = start_pos
    
    for target in target_sequence:
        # Traditional shortest path within 360°
        direct_distance = abs(target - current_pos)
        wrap_distance = 360 - direct_distance
        
        rotation = min(direct_distance, wrap_distance)
        total_rotation += rotation
        current_pos = target
    
    return total_rotation

def calculate_optimized_rotation(start_pos, target_sequence):
    """Calculate rotation using 450° optimization"""
    
    # Test different starting strategies
    strategies = []
    
    # Strategy 1: Start direct
    strategy1 = test_strategy(start_pos, target_sequence, 0)
    strategies.append(("Direct", strategy1))
    
    # Strategy 2: Start +360 (if target allows)
    if target_sequence[0] + 360 <= 450:
        strategy2 = test_strategy(start_pos, [t + 360 for t in target_sequence], 360)
        strategies.append(("Start +360", strategy2))
    
    # Strategy 3: Start -360 (if target allows)
    if target_sequence[0] - 360 >= 0:
        strategy3 = test_strategy(start_pos, [t - 360 for t in target_sequence], -360)
        strategies.append(("Start -360", strategy3))
    
    # Choose best strategy
    best_strategy = min(strategies, key=lambda x: x[1]['total_rotation'])
    return best_strategy[1]['total_rotation'], best_strategy[1]['sequence']

def test_strategy(start_pos, target_sequence, offset):
    """Test a specific strategy"""
    total_rotation = 0
    current_pos = start_pos
    sequence = []
    
    for target in target_sequence:
        # Calculate shortest path considering 450° range
        distance, optimal_target = calculate_shortest_path(current_pos, target, 450)
        total_rotation += distance
        current_pos = optimal_target
        sequence.append(optimal_target)
    
    return {
        'total_rotation': total_rotation,
        'sequence': sequence,
        'offset': offset
    }

def calculate_shortest_path(from_pos, to_pos, max_range):
    """Calculate shortest path considering rotator range"""
    # Normalize positions
    from_norm = from_pos % 360
    to_norm = to_pos % 360
    
    # Calculate direct distance
    direct_dist = abs(to_norm - from_norm)
    
    # Calculate wraparound distances
    paths = [(direct_dist, to_norm)]
    
    if max_range > 360:
        # Try going the long way
        if to_norm > from_norm:
            long_dist = from_norm + (360 - to_norm)
            long_target = to_norm - 360
        else:
            long_dist = (360 - from_norm) + to_norm
            long_target = to_norm + 360
        
        # Check if long path target is within range
        if 0 <= long_target <= max_range:
            paths.append((long_dist, long_target))
    
    # Return shortest path
    return min(paths, key=lambda x: x[0])

def demonstrate_real_world_example():
    """Demonstrate with real satellite pass example"""
    print("\n🌍 REAL-WORLD EXAMPLE")
    print("=" * 50)
    
    print("Satellite: ISS (International Space Station)")
    print("Pass: West to East crossing")
    print("Observer: Northern hemisphere")
    print()
    
    # Simulate typical ISS pass
    iss_pass = [
        (280.0, 5.0),   # AOS - West
        (320.0, 15.0),  # Rising
        (0.0, 25.0),    # Crossing North
        (40.0, 35.0),   # Maximum elevation
        (80.0, 25.0),   # Descending
        (120.0, 15.0),  # East
        (160.0, 5.0),   # LOS
    ]
    
    print("Pass profile:")
    for i, (az, el) in enumerate(iss_pass):
        print(f"  Step {i+1}: Az={az:6.1f}°, El={el:4.1f}°")
    
    # Current rotator position: 90° (pointing East)
    current_pos = 90.0
    print(f"\nCurrent rotator position: {current_pos}°")
    
    # Calculate optimizations
    azimuths = [az for az, el in iss_pass]
    
    traditional = calculate_traditional_rotation(current_pos, azimuths)
    optimized, optimal_seq = calculate_optimized_rotation(current_pos, azimuths)
    
    print(f"\nTraditional approach: {traditional:.1f}° rotation")
    print(f"Optimized approach: {optimized:.1f}° rotation")
    print(f"Improvement: {traditional - optimized:.1f}° saved")
    
    # Show optimal sequence
    print(f"\nOptimal rotator sequence:")
    for i, pos in enumerate(optimal_seq):
        print(f"  Step {i+1}: {pos:6.1f}° (El={iss_pass[i][1]:4.1f}°)")

def print_usage_instructions():
    """Print usage instructions for the actual system"""
    print("\n📋 USAGE INSTRUCTIONS")
    print("=" * 50)
    
    print("To use the enhanced rotator control in QTrigDoppler:")
    print()
    print("1. Ensure your rotator supports 450° azimuth range")
    print("2. Set az_max=450 in config.ini under [rotator] section")
    print("3. Select your satellite and transponder")
    print("4. Click 'Start Tracking'")
    print()
    print("The system will automatically:")
    print("• Predict the satellite pass for the next 20 minutes")
    print("• Calculate optimal rotator positioning")
    print("• Pre-position rotator if beneficial (>30s before AOS)")
    print("• Display optimization status in the UI")
    print()
    print("Status indicators:")
    print("• 'Optimized (-X°)' - Route optimized, X degrees saved")
    print("• 'Pre-positioned' - Rotator moved to optimal starting position")
    print("• 'Optimal' - Current position is already optimal")
    print("• 'Ready' - System ready, no optimization needed")
    print()
    print("Benefits:")
    print("• Reduced mechanical wear on rotator")
    print("• Smoother satellite tracking")
    print("• Better use of 450° rotator capability")
    print("• Automatic optimization without user intervention")

def main():
    """Main demonstration"""
    print("🚀 ENHANCED ROTATOR CONTROL DEMONSTRATION")
    print("=" * 60)
    print("450-Degree Azimuth Optimization with Look-Ahead")
    print("=" * 60)
    
    # Run demonstrations
    simulate_satellite_pass()
    demonstrate_optimization_scenarios()
    demonstrate_real_world_example()
    print_usage_instructions()
    
    print("\n✅ DEMONSTRATION COMPLETE")
    print("The enhanced rotator control system is now integrated into QTrigDoppler!")

if __name__ == "__main__":
    main()
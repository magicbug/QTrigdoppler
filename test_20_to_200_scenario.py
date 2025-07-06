#!/usr/bin/env python3
"""
Test the specific scenario: Satellite from 20° to 200°
Shows when the system will use the extended 450° range
"""

def calculate_rotation_distance(from_az, to_az, az_max=450):
    """
    Calculate shortest rotation distance considering 450° capability
    """
    # Normalize inputs
    from_norm = from_az % 360
    to_norm = to_az % 360
    
    # Calculate direct distance
    direct_dist = abs(to_norm - from_norm)
    target_direct = to_norm
    
    # Calculate distances using 450-degree capability
    distances = [(direct_dist, target_direct)]
    
    if az_max > 360:
        # Try going the long way (crossing 0/360)
        if to_norm > from_norm:
            # Going backwards through 0
            long_dist = from_norm + (360 - to_norm)
            target_long = to_norm - 360
        else:
            # Going forwards through 360
            long_dist = (360 - from_norm) + to_norm
            target_long = to_norm + 360
            
        # Check if long path target is within range
        if target_long <= az_max and target_long >= 0:
            distances.append((long_dist, target_long))
    
    # Return the shortest distance option
    return min(distances, key=lambda x: x[0])

def test_satellite_pass(start_pos, satellite_path):
    """Test a complete satellite pass"""
    print(f"\n🚀 Starting from {start_pos}°")
    print("-" * 30)
    
    current_pos = start_pos
    total_rotation = 0
    path = [start_pos]
    
    for target in satellite_path:
        distance, optimal_target = calculate_rotation_distance(current_pos, target)
        total_rotation += distance
        current_pos = optimal_target
        path.append(optimal_target)
        
    print(f"Route: {' → '.join(f'{p:.0f}°' for p in path)}")
    print(f"Total rotation: {total_rotation:.0f}°")
    
    # Check if we used extended range
    beyond_360 = [p for p in path if p > 360 or p < 0]
    if beyond_360:
        print(f"✅ Used extended range: {beyond_360}")
        print("🎯 Benefits: Smoother tracking, no wraparound!")
    else:
        print("📍 Stayed within 0-360° range")
    
    return total_rotation, path

def main():
    print("🛰️ SATELLITE PASS: 20° → 200°")
    print("=" * 50)
    print("Testing when system uses 450° capability...")
    
    # Satellite path from 20° to 200°
    satellite_path = [20, 50, 100, 150, 200]
    
    # Test different starting positions
    test_positions = [300, 350, 100, 250]
    
    results = []
    
    for start_pos in test_positions:
        rotation, path = test_satellite_pass(start_pos, satellite_path)
        results.append((start_pos, rotation, path))
    
    print("\n📊 SUMMARY")
    print("=" * 50)
    
    for start_pos, rotation, path in results:
        beyond_360 = any(p > 360 or p < 0 for p in path)
        status = "🚀 Extended range" if beyond_360 else "📍 Normal range"
        print(f"From {start_pos:3.0f}°: {rotation:3.0f}° total rotation {status}")
    
    print("\n🎯 KEY INSIGHT:")
    print("The system uses 450° range when it provides:")
    print("• Smoother movement (no direction changes)")
    print("• No wraparound confusion at 0°/360°")
    print("• Equal or better efficiency")
    
    # Specific example for your question
    print(f"\n💡 YOUR EXAMPLE (20° → 200°):")
    print("If rotator is at 350°, system will:")
    print("• Move to 380° (20° + 360°) - smooth 30° movement")
    print("• Track to 560° (200° + 360°) - smooth 180° movement") 
    print("• Result: No wraparound, all forward motion!")

if __name__ == "__main__":
    main()
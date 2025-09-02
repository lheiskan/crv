#!/usr/bin/env python3
"""
Visualize car service timeline and cost analysis
"""

import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import pandas as pd
import numpy as np


def load_service_data(filename="service_history.json"):
    """Load service data from JSON file"""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Convert date strings to datetime objects
    for record in data:
        record['service_date'] = datetime.strptime(record['service_date'], '%Y-%m-%d')
    
    return data


def clean_odometer_data(data):
    """Clean and fix odometer readings"""
    # There seems to be inconsistent odometer readings (some with extra digit)
    # Let's identify and fix them
    
    sorted_data = sorted(data, key=lambda x: x['service_date'])
    
    # Identify two groups of odometer readings
    readings = [r['odometer_km'] for r in sorted_data]
    
    # Group 1: Normal readings (around 200k-400k)
    # Group 2: Erroneous readings (around 2M+)
    
    for record in sorted_data:
        if record['odometer_km'] > 1000000:  # Likely erroneous
            # Remove the leading '2' digit
            fixed_km = int(str(record['odometer_km'])[1:])
            if 200000 < fixed_km < 500000:  # Reasonable range
                record['odometer_km'] = fixed_km
                print(f"Fixed odometer: {record['service_date'].strftime('%Y-%m-%d')} from {record['odometer_km'] + 2000000} to {fixed_km}")
    
    return sorted_data


def create_visualizations(data):
    """Create comprehensive visualization of service history"""
    
    # Clean the data first
    data = clean_odometer_data(data)
    
    # Filter out zero odometer readings (incomplete data)
    data = [r for r in data if r['odometer_km'] > 0]
    
    # Sort by date
    data = sorted(data, key=lambda x: x['service_date'])
    
    # Extract data for plotting
    dates = [r['service_date'] for r in data]
    costs = [r['total_with_vat'] for r in data]
    odometer = [r['odometer_km'] for r in data]
    
    # Create figure with subplots
    fig = plt.figure(figsize=(15, 12))
    
    # 1. Service Cost Timeline
    ax1 = plt.subplot(3, 2, 1)
    ax1.bar(dates, costs, width=20, alpha=0.7, color='steelblue', edgecolor='navy')
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cost (€)')
    ax1.set_title('Service Costs Over Time')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    
    # Add average line
    avg_cost = np.mean(costs)
    ax1.axhline(y=avg_cost, color='red', linestyle='--', alpha=0.5, 
                label=f'Average: €{avg_cost:.2f}')
    ax1.legend()
    
    # 2. Cumulative Cost
    ax2 = plt.subplot(3, 2, 2)
    cumulative_costs = np.cumsum(costs)
    ax2.plot(dates, cumulative_costs, marker='o', linewidth=2, markersize=6, 
             color='darkgreen')
    ax2.fill_between(dates, cumulative_costs, alpha=0.3, color='lightgreen')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Cumulative Cost (€)')
    ax2.set_title(f'Total Spent: €{cumulative_costs[-1]:,.2f}')
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    
    # 3. Odometer Reading Progress
    ax3 = plt.subplot(3, 2, 3)
    ax3.plot(dates, [km/1000 for km in odometer], marker='o', linewidth=2, 
             markersize=6, color='purple')
    ax3.set_xlabel('Date')
    ax3.set_ylabel('Odometer (x1000 km)')
    ax3.set_title('Vehicle Mileage Over Time')
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45)
    
    # 4. Cost per Service Distribution
    ax4 = plt.subplot(3, 2, 4)
    ax4.hist(costs, bins=15, alpha=0.7, color='coral', edgecolor='darkred')
    ax4.set_xlabel('Cost (€)')
    ax4.set_ylabel('Number of Services')
    ax4.set_title('Distribution of Service Costs')
    ax4.grid(True, alpha=0.3, axis='y')
    ax4.axvline(x=avg_cost, color='red', linestyle='--', alpha=0.5, 
                label=f'Average: €{avg_cost:.2f}')
    ax4.axvline(x=np.median(costs), color='blue', linestyle='--', alpha=0.5,
                label=f'Median: €{np.median(costs):.2f}')
    ax4.legend()
    
    # 5. Service Intervals (km between services)
    ax5 = plt.subplot(3, 2, 5)
    if len(odometer) > 1:
        intervals = []
        interval_dates = []
        for i in range(1, len(odometer)):
            interval = odometer[i] - odometer[i-1]
            if interval > 0:  # Only positive intervals
                intervals.append(interval)
                interval_dates.append(dates[i])
        
        if intervals:
            ax5.bar(interval_dates, [km/1000 for km in intervals], width=20, 
                   alpha=0.7, color='teal', edgecolor='darkslategray')
            ax5.set_xlabel('Date')
            ax5.set_ylabel('Interval (x1000 km)')
            ax5.set_title('Distance Between Services')
            ax5.grid(True, alpha=0.3)
            ax5.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.xticks(rotation=45)
            
            avg_interval = np.mean(intervals)
            ax5.axhline(y=avg_interval/1000, color='red', linestyle='--', alpha=0.5,
                       label=f'Average: {avg_interval/1000:.1f}k km')
            ax5.legend()
    
    # 6. Service Cost vs Odometer
    ax6 = plt.subplot(3, 2, 6)
    ax6.scatter([km/1000 for km in odometer], costs, alpha=0.7, s=50, 
                color='indigo', edgecolor='black')
    ax6.set_xlabel('Odometer (x1000 km)')
    ax6.set_ylabel('Cost (€)')
    ax6.set_title('Service Cost vs Vehicle Age')
    ax6.grid(True, alpha=0.3)
    
    # Add trend line
    z = np.polyfit([km/1000 for km in odometer], costs, 1)
    p = np.poly1d(z)
    ax6.plot([km/1000 for km in odometer], p([km/1000 for km in odometer]), 
             "r--", alpha=0.5, label='Trend')
    ax6.legend()
    
    plt.suptitle(f'Honda CR-V Service History Analysis\n({data[0]["vehicle_reg"]})', 
                 fontsize=16, fontweight='bold')
    plt.tight_layout()
    
    # Save the figure
    plt.savefig('service_timeline.png', dpi=150, bbox_inches='tight')
    print("\n✓ Timeline visualization saved to service_timeline.png")
    # plt.show()  # Commented out for non-interactive mode
    
    # Generate statistics report
    print("\n" + "="*60)
    print("DETAILED STATISTICS")
    print("="*60)
    
    total_days = (dates[-1] - dates[0]).days
    years = total_days / 365.25
    
    print(f"\nTime Period: {dates[0].strftime('%Y-%m-%d')} to {dates[-1].strftime('%Y-%m-%d')}")
    print(f"Duration: {years:.1f} years ({total_days} days)")
    print(f"Total Services: {len(data)}")
    print(f"Total Cost: €{sum(costs):,.2f}")
    print(f"Average Cost per Service: €{avg_cost:.2f}")
    print(f"Median Cost: €{np.median(costs):.2f}")
    print(f"Most Expensive Service: €{max(costs):.2f}")
    print(f"Least Expensive: €{min(costs):.2f}")
    
    if len(odometer) > 1:
        total_km = odometer[-1] - odometer[0]
        print(f"\nTotal Distance Covered: {total_km:,} km")
        print(f"Average km per Year: {total_km/years:,.0f}")
        print(f"Cost per 1000 km: €{sum(costs)/(total_km/1000):.2f}")
        print(f"Average Service Interval: {np.mean(intervals):,.0f} km")
    
    # Most common service items
    all_items = []
    for record in data:
        for item in record['service_items']:
            all_items.append(item['description'])
    
    from collections import Counter
    item_counts = Counter(all_items)
    
    print("\n" + "-"*60)
    print("MOST COMMON SERVICE ITEMS:")
    print("-"*60)
    for item, count in item_counts.most_common(10):
        print(f"  {item}: {count} times")
    
    # Service provider breakdown
    providers = [r['service_provider'] for r in data]
    provider_counts = Counter(providers)
    
    print("\n" + "-"*60)
    print("SERVICE PROVIDERS:")
    print("-"*60)
    for provider, count in provider_counts.most_common():
        provider_costs = sum(r['total_with_vat'] for r in data if r['service_provider'] == provider)
        print(f"  {provider}: {count} services, €{provider_costs:,.2f} total")


def main():
    """Main function"""
    # Load the data
    data = load_service_data("service_history.json")
    
    if not data:
        print("No data found in service_history.json")
        return
    
    # Create visualizations
    create_visualizations(data)


if __name__ == "__main__":
    main()
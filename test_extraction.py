#!/usr/bin/env python3
"""
Quick test script to validate extraction is working correctly.
Run this after making changes to ensure nothing is broken.
"""

import json
from pathlib import Path
from datetime import datetime


def validate_extraction():
    """Validate extracted data quality"""
    
    print("Receipt Extraction Validation Report")
    print("="*50)
    
    # Check if files exist
    files_to_check = [
        "service_history.json",
        "complex_receipts.json",
        "service_timeline.png"
    ]
    
    for file in files_to_check:
        if Path(file).exists():
            print(f"✓ {file} exists")
        else:
            print(f"✗ {file} missing")
    
    # Validate service_history.json
    if Path("service_history.json").exists():
        with open("service_history.json", 'r') as f:
            data = json.load(f)
        
        print(f"\nSimple receipts: {len(data)} extracted")
        
        # Check for data quality
        issues = []
        for i, receipt in enumerate(data):
            # Check odometer sequence
            if receipt['odometer_km'] > 1000000:
                issues.append(f"Receipt {i}: Suspicious odometer {receipt['odometer_km']}")
            
            # Check date range
            try:
                date = datetime.strptime(receipt['service_date'], '%Y-%m-%d')
                if date.year < 2000 or date.year > 2030:
                    issues.append(f"Receipt {i}: Suspicious date {receipt['service_date']}")
            except:
                issues.append(f"Receipt {i}: Invalid date format")
            
            # Check vehicle reg
            if receipt.get('vehicle_reg') not in ['LTI-509', 'IKB-981', None]:
                issues.append(f"Receipt {i}: Unknown vehicle {receipt.get('vehicle_reg')}")
        
        if issues:
            print("\nData Quality Issues:")
            for issue in issues[:5]:  # Show first 5 issues
                print(f"  - {issue}")
        else:
            print("✓ No data quality issues found")
    
    # Check JSON files in receipts_json
    if Path("receipts_json").exists():
        json_files = list(Path("receipts_json").glob("*.json"))
        print(f"\nIndividual JSON files: {len(json_files)}")
        
        # Show sample filenames
        if json_files:
            print("Sample files:")
            for file in json_files[:3]:
                print(f"  - {file.name}")
    
    # Summary statistics
    if Path("service_history.json").exists():
        with open("service_history.json", 'r') as f:
            data = json.load(f)
        
        if data:
            total_cost = sum(r['total_with_vat'] for r in data if r.get('total_with_vat'))
            dates = [r['service_date'] for r in data if r.get('service_date')]
            
            print(f"\nSummary Statistics:")
            print(f"  Total services: {len(data)}")
            print(f"  Total cost: €{total_cost:,.2f}")
            if dates:
                print(f"  Date range: {min(dates)} to {max(dates)}")
            
            # Check extraction rate
            original_count = 35  # Known number of PDFs in receipts/
            success_rate = (len(data) / original_count) * 100
            print(f"  Extraction rate: {success_rate:.1f}%")


if __name__ == "__main__":
    validate_extraction()
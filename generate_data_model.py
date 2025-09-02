#!/usr/bin/env python3
"""
Generate a unified data model from all receipt JSON files for web visualization.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import hashlib


def fix_odometer(km: int) -> int:
    """Fix erroneous odometer readings with extra '2' prefix"""
    if km and km > 1000000:
        # Remove leading '2' from readings like 2,387,551 -> 387,551
        km_str = str(km)
        if km_str.startswith('2') and len(km_str) == 7:
            fixed_km = int(km_str[1:])
            if 200000 < fixed_km < 500000:  # Reasonable range
                return fixed_km
    return km


def load_all_receipts() -> List[Dict]:
    """Load and combine all receipt data"""
    all_receipts = []
    
    # Load simple receipts
    if Path("service_history.json").exists():
        with open("service_history.json", 'r', encoding='utf-8') as f:
            simple_receipts = json.load(f)
            for receipt in simple_receipts:
                receipt['source'] = 'simple'
                receipt['id'] = hashlib.md5(
                    f"{receipt.get('invoice_number', '')}_{receipt.get('service_date', '')}".encode()
                ).hexdigest()[:8]
                
                # Fix odometer readings
                if receipt.get('odometer_km'):
                    receipt['odometer_km'] = fix_odometer(receipt['odometer_km'])
                
                all_receipts.append(receipt)
    
    # Load complex receipts
    if Path("complex_receipts.json").exists():
        with open("complex_receipts.json", 'r', encoding='utf-8') as f:
            complex_receipts = json.load(f)
            for receipt in complex_receipts:
                receipt['source'] = 'complex'
                receipt['id'] = hashlib.md5(
                    f"{receipt.get('invoice_number', '')}_{receipt.get('service_date', '')}_{receipt.get('page_number', '')}".encode()
                ).hexdigest()[:8]
                
                # Normalize field names
                if 'total_amount' in receipt and 'total_with_vat' not in receipt:
                    receipt['total_with_vat'] = receipt['total_amount']
                    
                all_receipts.append(receipt)
    
    return all_receipts


def calculate_statistics(receipts: List[Dict]) -> Dict:
    """Calculate summary statistics"""
    
    # Filter receipts with valid dates and amounts
    valid_receipts = [
        r for r in receipts 
        if r.get('service_date') and r.get('total_with_vat')
    ]
    
    if not valid_receipts:
        return {}
    
    # Sort by date
    valid_receipts.sort(key=lambda x: x['service_date'])
    
    total_cost = sum(r.get('total_with_vat', 0) for r in valid_receipts)
    
    # Calculate monthly spending
    monthly_spending = {}
    for receipt in valid_receipts:
        date_str = receipt['service_date']
        if date_str:
            month_key = date_str[:7]  # YYYY-MM
            if month_key not in monthly_spending:
                monthly_spending[month_key] = 0
            monthly_spending[month_key] += receipt.get('total_with_vat', 0)
    
    # Calculate yearly spending
    yearly_spending = {}
    for receipt in valid_receipts:
        date_str = receipt['service_date']
        if date_str:
            year = date_str[:4]
            if year not in yearly_spending:
                yearly_spending[year] = 0
            yearly_spending[year] += receipt.get('total_with_vat', 0)
    
    # Service provider breakdown
    provider_stats = {}
    for receipt in valid_receipts:
        provider = receipt.get('service_provider') or receipt.get('company', 'Unknown')
        if provider not in provider_stats:
            provider_stats[provider] = {'count': 0, 'total': 0}
        provider_stats[provider]['count'] += 1
        provider_stats[provider]['total'] += receipt.get('total_with_vat', 0)
    
    # Common service items
    all_items = []
    for receipt in receipts:
        if 'service_items' in receipt:
            for item in receipt['service_items']:
                all_items.append(item.get('description', 'Unknown'))
    
    # Count item frequencies
    item_counts = {}
    for item in all_items:
        item_counts[item] = item_counts.get(item, 0) + 1
    
    # Top service items
    top_items = sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        'total_services': len(valid_receipts),
        'total_cost': round(total_cost, 2),
        'average_cost': round(total_cost / len(valid_receipts), 2) if valid_receipts else 0,
        'date_range': {
            'start': valid_receipts[0]['service_date'] if valid_receipts else None,
            'end': valid_receipts[-1]['service_date'] if valid_receipts else None
        },
        'monthly_spending': monthly_spending,
        'yearly_spending': yearly_spending,
        'provider_stats': provider_stats,
        'top_service_items': [{'item': item, 'count': count} for item, count in top_items]
    }


def prepare_chart_data(receipts: List[Dict]) -> Dict:
    """Prepare data specifically for chart visualization"""
    
    # Filter and sort
    valid_receipts = [
        r for r in receipts 
        if r.get('service_date') and r.get('total_with_vat')
    ]
    valid_receipts.sort(key=lambda x: x['service_date'])
    
    # Time series data for line chart
    time_series = []
    cumulative_cost = 0
    
    for receipt in valid_receipts:
        cumulative_cost += receipt.get('total_with_vat', 0)
        time_series.append({
            'date': receipt['service_date'],
            'cost': round(receipt.get('total_with_vat', 0), 2),
            'cumulative': round(cumulative_cost, 2),
            'provider': receipt.get('service_provider') or receipt.get('company', 'Unknown'),
            'odometer': receipt.get('odometer_km', 0)
        })
    
    # Cost distribution for histogram
    cost_ranges = {
        '0-50€': 0,
        '51-100€': 0,
        '101-200€': 0,
        '201-300€': 0,
        '301-500€': 0,
        '500€+': 0
    }
    
    for receipt in valid_receipts:
        cost = receipt.get('total_with_vat', 0)
        if cost <= 50:
            cost_ranges['0-50€'] += 1
        elif cost <= 100:
            cost_ranges['51-100€'] += 1
        elif cost <= 200:
            cost_ranges['101-200€'] += 1
        elif cost <= 300:
            cost_ranges['201-300€'] += 1
        elif cost <= 500:
            cost_ranges['301-500€'] += 1
        else:
            cost_ranges['500€+'] += 1
    
    return {
        'time_series': time_series,
        'cost_distribution': cost_ranges
    }


def generate_data_model():
    """Generate complete data model for web visualization"""
    
    print("Generating data model...")
    
    # Load all receipts
    receipts = load_all_receipts()
    print(f"  Loaded {len(receipts)} receipts")
    
    # Calculate statistics
    stats = calculate_statistics(receipts)
    
    # Prepare chart data
    charts = prepare_chart_data(receipts)
    
    # Build complete data model
    data_model = {
        'generated_at': datetime.now().isoformat(),
        'vehicle': {
            'make': 'Honda',
            'model': 'CR-V',
            'registration': 'LTI-509',
            'image_placeholder': 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cmVjdCB3aWR0aD0iODAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2NjY2NjYyIvPgogIDx0ZXh0IHg9IjQwMCIgeT0iMTUwIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSIyNCIgZmlsbD0iIzY2NiIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZG9taW5hbnQtYmFzZWxpbmU9ImNlbnRyYWwiPkNhciBQaG90byBQbGFjZWhvbGRlcjwvdGV4dD4KICA8dGV4dCB4PSI0MDAiIHk9IjE4MCIgZm9udC1mYW1pbHk9InNhbnMtc2VyaWYiIGZvbnQtc2l6ZT0iMTgiIGZpbGw9IiM5OTkiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJjZW50cmFsIj5Ib25kYSBDUi1WPC90ZXh0Pgo8L3N2Zz4K'
        },
        'statistics': stats,
        'charts': charts,
        'receipts': sorted(
            [r for r in receipts if r.get('service_date')],
            key=lambda x: x['service_date'],
            reverse=True
        )
    }
    
    # Save data model
    output_file = "service_data_model.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data_model, f, ensure_ascii=False, indent=2)
    
    print(f"✓ Data model saved to {output_file}")
    print(f"  - {stats.get('total_services', 0)} services")
    print(f"  - €{stats.get('total_cost', 0):,.2f} total cost")
    print(f"  - {len(stats.get('provider_stats', {}))} service providers")
    
    return data_model


if __name__ == "__main__":
    generate_data_model()
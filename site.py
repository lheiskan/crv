#!/usr/bin/env python3
"""
site.py - Car Service History Site Operations

Commands:
    python site.py build       # Generate complete static site
    python site.py serve       # Serve site locally
    python site.py clean       # Clean generated files
    python site.py validate    # Validate source data
"""

import os
import sys
import json
import glob
import shutil
import base64
import argparse
import http.server
import socketserver
from datetime import datetime, timedelta
from pathlib import Path


class ServiceHistorySiteManager:
    def __init__(self):
        self.verified_dir = "verified/"
        self.extracted_dir = "extracted/"
        self.receipts_dir = "receipts/"
        self.site_dir = "site/"
        self.service_data = []
        
        # Statistics Finland fuel prices (€/liter)
        self.fuel_prices_finland = {
            2009: 1.25, 2010: 1.35, 2011: 1.50, 2012: 1.62, 2013: 1.58,
            2014: 1.45, 2015: 1.28, 2016: 1.32, 2017: 1.42, 2018: 1.52,
            2019: 1.48, 2020: 1.35, 2021: 1.58, 2022: 1.85, 2023: 1.72,
            2024: 1.68, 2025: 1.75
        }
        
        # Honda CR-V consumption assumption
        self.consumption_l_per_100km = 8.5

    def build_site(self, force=False):
        """Main build process"""
        print("🚀 Building Car Service History Site...")
        
        if force and os.path.exists(self.site_dir):
            print(f"🧹 Cleaning existing site directory...")
            shutil.rmtree(self.site_dir)
        
        if not self.validate_source_data():
            print("❌ Validation failed. Cannot build site.")
            return False
            
        self.create_site_structure()
        self.process_and_rename_files()
        analytics = self.calculate_analytics()
        self.generate_main_page(analytics)
        self.generate_receipt_pages()
        self.copy_static_assets()
        
        print(f"✅ Static site generated in {self.site_dir}")
        print("🌐 Serve with: python site.py serve")
        return True

    def validate_source_data(self):
        """Validate source data with date checking"""
        print("🔍 Validating source data...")
        
        valid_count = 0
        invalid_count = 0
        
        pdf_files = glob.glob(f"{self.receipts_dir}*.pdf")
        if not pdf_files:
            print(f"❌ No PDF files found in {self.receipts_dir}")
            return False
        
        for pdf_file in pdf_files:
            pdf_basename = os.path.basename(pdf_file)
            verified_path = f"{self.verified_dir}{pdf_basename}/verified.json"
            
            if not os.path.exists(verified_path):
                print(f"⚠️  Warning: No verified.json for {pdf_basename}")
                invalid_count += 1
                continue
                
            try:
                # Use the same loading mechanism to get merged data
                data = self.load_service_data_with_overrides(pdf_basename)
                    
                date = data.get("ground_truth", {}).get("date")
                if not date:
                    print(f"❌ Error: No date in verified.json for {pdf_basename} - EXCLUDING from site")
                    invalid_count += 1
                    continue
                    
                # Validate date format
                datetime.strptime(date, "%Y-%m-%d")
                valid_count += 1
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"❌ Error processing {pdf_basename}: {e} - EXCLUDING from site")
                invalid_count += 1
                
        print(f"📊 Validation complete: {valid_count} valid, {invalid_count} invalid receipts")
        return valid_count > 0

    def create_site_structure(self):
        """Create site directory structure"""
        print("📁 Creating site structure...")
        
        directories = [
            self.site_dir,
            f"{self.site_dir}assets/",
            f"{self.site_dir}receipts/",
            f"{self.site_dir}data/",
            f"{self.site_dir}data/ocr/",
            f"{self.site_dir}pdfs/"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def load_service_data_with_overrides(self, pdf_basename):
        """Load verified data and apply overrides if they exist"""
        verified_path = f"{self.verified_dir}{pdf_basename}/verified.json"
        
        with open(verified_path, 'r', encoding='utf-8') as f:
            verified_data = json.load(f)
        
        # Check for override.json
        override_path = f"{self.verified_dir}{pdf_basename}/override.json"
        overridden_fields = {}
        
        if os.path.exists(override_path):
            with open(override_path, 'r', encoding='utf-8') as f:
                override_data = json.load(f)
            
            # Store original values and apply overrides
            original_ground_truth = verified_data["ground_truth"].copy()
            override_ground_truth = override_data.get("ground_truth", {})
            
            for field, new_value in override_ground_truth.items():
                original_value = original_ground_truth.get(field)
                if original_value != new_value:
                    overridden_fields[field] = {
                        "original": original_value,
                        "override": new_value
                    }
                    verified_data["ground_truth"][field] = new_value
            
            # Add override metadata
            verified_data["override_info"] = {
                "has_overrides": True,
                "overridden_fields": overridden_fields,
                "reason": override_data.get("reason")  # Optional reason
            }
        else:
            verified_data["override_info"] = {
                "has_overrides": False,
                "overridden_fields": {},
                "reason": None
            }
        
        return verified_data

    def process_and_rename_files(self):
        """Process files and rename using dates from verified.json"""
        print("📄 Processing and renaming files...")
        
        self.service_data = []
        date_conflicts = {}
        
        for pdf_file in glob.glob(f"{self.receipts_dir}*.pdf"):
            pdf_basename = os.path.basename(pdf_file)
            
            # Skip if no verified.json (already warned in validation)
            verified_path = f"{self.verified_dir}{pdf_basename}/verified.json"
            if not os.path.exists(verified_path):
                continue
                
            try:
                # Load verified data with overrides applied
                verified_data = self.load_service_data_with_overrides(pdf_basename)
                    
                date = verified_data.get("ground_truth", {}).get("date")
                if not date:
                    continue
                    
                # Handle date conflicts (multiple receipts on same date)
                original_date = date
                counter = 1
                while date in date_conflicts:
                    counter += 1
                    date = f"{original_date}-{counter}"
                    
                date_conflicts[date] = pdf_basename
                
                # Create service record
                ground_truth = verified_data.get("ground_truth", {})
                service_record = {
                    "date": date,
                    "original_filename": pdf_basename,
                    "renamed_filename": f"{date}.pdf",
                    "verified_data": verified_data,
                    **ground_truth
                }
                
                # Load extraction data if available
                extracted_path = f"{self.extracted_dir}{pdf_basename}/data.json"
                if os.path.exists(extracted_path):
                    with open(extracted_path, 'r', encoding='utf-8') as f:
                        service_record["extraction_data"] = json.load(f)
                
                self.service_data.append(service_record)
                
                # Copy and rename PDF
                shutil.copy2(pdf_file, f"{self.site_dir}pdfs/{date}.pdf")
                
                # Process OCR data if available
                self.process_ocr_data(service_record, date)
                
            except Exception as e:
                print(f"⚠️  Error processing {pdf_basename}: {e}")
                continue
        
        # Sort by date
        self.service_data.sort(key=lambda x: x["date"])
        
        # Save processed data
        with open(f"{self.site_dir}data/service-history.json", "w", encoding='utf-8') as f:
            json.dump(self.service_data, f, indent=2, ensure_ascii=False)
            
        print(f"📊 Processed {len(self.service_data)} valid service records")

    def process_ocr_data(self, service_record, date):
        """Extract and decode OCR data"""
        extraction_data = service_record.get("extraction_data", {})
        
        for step in extraction_data.get("processing_steps", []):
            if step.get("step_name") == "ocr":
                ocr_text = step.get("output", {}).get("text", "")
                if ocr_text:
                    try:
                        # Decode base64 OCR text
                        decoded_text = base64.b64decode(ocr_text).decode('utf-8')
                        # Save as text file
                        with open(f"{self.site_dir}data/ocr/{date}.txt", "w", encoding='utf-8') as f:
                            f.write(decoded_text)
                    except Exception as e:
                        print(f"⚠️  Warning: Could not decode OCR for {date}: {e}")
                break

    def calculate_analytics(self):
        """Calculate comprehensive analytics"""
        print("📊 Calculating analytics...")
        
        # Group by year
        yearly_data = {}
        for service in self.service_data:
            year = service['date'][:4]
            if year not in yearly_data:
                yearly_data[year] = []
            yearly_data[year].append(service)
        
        # Calculate maintenance costs
        maintenance = self.calculate_maintenance_costs(yearly_data)
        
        # Calculate mileage
        mileage = self.calculate_yearly_mileage()
        
        # Calculate fuel costs
        fuel_costs = self.estimate_fuel_costs(mileage)
        
        # Summary statistics
        summary = self.calculate_summary_stats()
        
        analytics = {
            "maintenance": maintenance,
            "mileage": mileage,
            "fuel": fuel_costs,
            "summary": summary
        }
        
        # Save analytics data
        with open(f"{self.site_dir}data/analytics.json", "w", encoding='utf-8') as f:
            json.dump(analytics, f, indent=2, ensure_ascii=False)
        
        return analytics

    def calculate_maintenance_costs(self, yearly_data):
        """Calculate maintenance cost analytics with moving averages"""
        # First, determine the full year range
        if not yearly_data:
            return {"yearly_costs": {}, "moving_average_3yr": {}}
        
        year_keys = [int(year) for year in yearly_data.keys()]
        start_year = min(year_keys)
        end_year = max(year_keys)
        
        # Initialize all years in range with 0 cost
        yearly_costs = {}
        for year in range(start_year, end_year + 1):
            yearly_costs[str(year)] = 0.0
        
        # Fill in actual costs where we have data
        for year, services in yearly_data.items():
            total_cost = sum(s.get('amount', 0) or 0 for s in services)
            yearly_costs[year] = round(total_cost, 2)
        
        # Calculate 3-year moving average (including zero years)
        years = sorted(yearly_costs.keys())
        moving_avg = {}
        
        for i, year in enumerate(years):
            if i >= 2:  # Need at least 3 years
                prev_years = years[i-2:i+1]
                avg_cost = sum(yearly_costs[y] for y in prev_years) / 3
                moving_avg[year] = round(avg_cost, 2)
        
        return {
            "yearly_costs": yearly_costs,
            "moving_average_3yr": moving_avg
        }

    def calculate_yearly_mileage(self):
        """Calculate yearly mileage from odometer readings"""
        # Get services with odometer readings, sorted by date
        services_with_odo = [s for s in self.service_data if s.get('odometer_km')]
        services_with_odo.sort(key=lambda x: x['date'])
        
        yearly_km = {}
        
        if len(services_with_odo) < 2:
            return {"yearly": yearly_km, "moving_average_3yr": {}}
        
        for i in range(1, len(services_with_odo)):
            current = services_with_odo[i]
            previous = services_with_odo[i-1]
            
            # Calculate km between readings
            km_driven = current['odometer_km'] - previous['odometer_km']
            
            if km_driven > 0:
                # Distribute km proportionally across years
                self.distribute_km_across_years(
                    previous['date'], current['date'], km_driven, yearly_km
                )
        
        # Fill in missing years with interpolated values
        if yearly_km:
            year_keys = [int(year) for year in yearly_km.keys()]
            start_year = min(year_keys)
            end_year = max(year_keys)
            
            # For missing years, use average of surrounding years or 0
            for year in range(start_year, end_year + 1):
                year_str = str(year)
                if year_str not in yearly_km:
                    # Find closest years with data
                    prev_year = next((y for y in range(year-1, start_year-1, -1) if str(y) in yearly_km), None)
                    next_year = next((y for y in range(year+1, end_year+1) if str(y) in yearly_km), None)
                    
                    if prev_year and next_year:
                        # Average of surrounding years
                        yearly_km[year_str] = round((yearly_km[str(prev_year)] + yearly_km[str(next_year)]) / 2, 0)
                    elif prev_year:
                        # Use previous year's value
                        yearly_km[year_str] = yearly_km[str(prev_year)]
                    elif next_year:
                        # Use next year's value
                        yearly_km[year_str] = yearly_km[str(next_year)]
                    else:
                        yearly_km[year_str] = 0
        
        # Calculate 3-year moving averages
        years = sorted(yearly_km.keys())
        moving_avg = {}
        
        for i, year in enumerate(years):
            if i >= 2:
                avg = sum(yearly_km[years[j]] for j in range(i-2, i+1)) / 3
                moving_avg[year] = round(avg, 0)
        
        return {
            "yearly": yearly_km,
            "moving_average_3yr": moving_avg
        }

    def distribute_km_across_years(self, start_date, end_date, km_driven, yearly_km):
        """Distribute kilometers proportionally across years"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end - start).days
        
        if total_days <= 0:
            return
        
        current_date = start
        while current_date.year <= end.year:
            year = str(current_date.year)
            
            # Calculate days in this year for this period
            year_start = max(current_date, datetime(current_date.year, 1, 1))
            year_end = min(end, datetime(current_date.year, 12, 31))
            
            if year_start <= year_end:
                days_in_year = (year_end - year_start).days + 1
                proportion = days_in_year / total_days
                km_for_year = km_driven * proportion
                
                yearly_km[year] = yearly_km.get(year, 0) + round(km_for_year, 0)
            
            current_date = datetime(current_date.year + 1, 1, 1)

    def estimate_fuel_costs(self, mileage_data):
        """Estimate fuel costs based on mileage and historical prices"""
        fuel_costs = {}
        
        for year, km in mileage_data["yearly"].items():
            year_int = int(year)
            # Include all years, even with 0 cost if no mileage
            if year_int in self.fuel_prices_finland:
                if km > 0:
                    liters_consumed = (km * self.consumption_l_per_100km) / 100
                    estimated_cost = liters_consumed * self.fuel_prices_finland[year_int]
                    fuel_costs[year] = round(estimated_cost, 2)
                else:
                    fuel_costs[year] = 0.0  # Include zero-cost years
        
        return fuel_costs

    def calculate_summary_stats(self):
        """Calculate summary statistics"""
        if not self.service_data:
            return {}
        
        # Basic stats
        total_services = len(self.service_data)
        total_cost = sum(s.get('amount', 0) or 0 for s in self.service_data)
        
        # Date range
        dates = [s['date'] for s in self.service_data]
        first_service = min(dates)
        last_service = max(dates)
        
        # Odometer stats
        odometer_readings = [s.get('odometer_km') for s in self.service_data if s.get('odometer_km')]
        
        summary = {
            "total_services": total_services,
            "total_cost": round(total_cost, 2),
            "average_cost": round(total_cost / total_services, 2) if total_services > 0 else 0,
            "first_service": first_service,
            "last_service": last_service,
            "years_span": int(last_service[:4]) - int(first_service[:4]) + 1
        }
        
        if odometer_readings:
            summary.update({
                "total_km": max(odometer_readings) - min(odometer_readings),
                "cost_per_km": round(total_cost / (max(odometer_readings) - min(odometer_readings)), 4) if max(odometer_readings) > min(odometer_readings) else 0
            })
        
        return summary

    def generate_main_page(self, analytics):
        """Generate the main index.html page"""
        print("🏠 Generating main page...")
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Honda CR-V Service History</title>
    <link rel="stylesheet" href="assets/style.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="car-info">
                <div class="car-image-placeholder">
                    <img src="assets/car-placeholder.jpg" alt="Honda CR-V" onerror="this.style.display='none';">
                    <div class="car-image-fallback">🚗</div>
                </div>
                <div class="car-details">
                    <h1>Honda CR-V Service History</h1>
                    <p class="car-specs">Registration: LTI-509 | Model: CR-V 2.0 AUT</p>
                </div>
            </div>
        </div>
    </header>

    <main class="container">
        <section class="summary-cards">
            <div class="stat-card">
                <h3>Total Services</h3>
                <span class="stat-number">{analytics['summary'].get('total_services', 0)}</span>
                <span class="stat-period">{analytics['summary'].get('first_service', '')[:4]} - {analytics['summary'].get('last_service', '')[:4]}</span>
            </div>
            <div class="stat-card">
                <h3>Total Cost</h3>
                <span class="stat-number">€{analytics['summary'].get('total_cost', 0):,.2f}</span>
                <span class="stat-period">Maintenance only</span>
            </div>
            <div class="stat-card">
                <h3>Average Annual</h3>
                <span class="stat-number">€{analytics['summary'].get('total_cost', 0) / max(analytics['summary'].get('years_span', 1), 1):,.0f}</span>
                <span class="stat-period">Per year</span>
            </div>
            <div class="stat-card">
                <h3>Cost per km</h3>
                <span class="stat-number">€{analytics['summary'].get('cost_per_km', 0):.3f}</span>
                <span class="stat-period">Maintenance</span>
            </div>
        </section>

        <section class="analytics-section">
            <h2>Annual Maintenance Costs</h2>
            <div class="chart-container">
                <canvas id="maintenanceChart"></canvas>
                <div class="chart-controls">
                    <label><input type="checkbox" checked id="showAbsolute"> Yearly Costs</label>
                    <label><input type="checkbox" checked id="showMovingAvg"> 3-Year Moving Average</label>
                </div>
            </div>
        </section>

        <section class="analytics-section">
            <h2>Usage & Estimated Fuel Costs</h2>
            <div class="dual-chart-container">
                <div class="chart-half">
                    <canvas id="mileageChart"></canvas>
                    <h4>Annual Kilometers</h4>
                </div>
                <div class="chart-half">
                    <canvas id="fuelChart"></canvas>
                    <h4>Estimated Fuel Costs</h4>
                </div>
            </div>
            <div class="fuel-methodology">
                <details>
                    <summary>Fuel Cost Calculation Method</summary>
                    <ul>
                        <li><strong>Consumption:</strong> {self.consumption_l_per_100km}L/100km (Honda CR-V assumption)</li>
                        <li><strong>Prices:</strong> Statistics Finland historical gasoline prices</li>
                        <li><strong>Mileage:</strong> From odometer readings (gaps filled with time-based averages)</li>
                    </ul>
                </details>
            </div>
        </section>

        <section class="service-history">
            <h2>Service History</h2>
            <div class="table-container">
                <table class="service-table" id="serviceTable">
                    <thead>
                        <tr>
                            <th onclick="sortTable(0)">Date 📅</th>
                            <th onclick="sortTable(1)">Company</th>
                            <th onclick="sortTable(2)">Odometer</th>
                            <th onclick="sortTable(3)">Cost 💰</th>
                            <th onclick="sortTable(4)">Invoice</th>
                            <th>Source File</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        # Add service rows
        for service in reversed(self.service_data):  # Most recent first
            odometer = f"{service.get('odometer_km'):,} km" if service.get('odometer_km') else "N/A"
            amount = f"€{service.get('amount'):,.2f}" if service.get('amount') else "N/A"
            invoice = service.get('invoice_number', 'N/A')
            
            # Check if this service has overrides
            override_info = service.get('verified_data', {}).get('override_info', {})
            has_overrides = override_info.get('has_overrides', False)
            override_indicator = ' 🔧' if has_overrides else ''
            row_class = 'clickable-row has-overrides' if has_overrides else 'clickable-row'
            
            html_content += f"""
                        <tr onclick="openReceipt('{service['date']}')" class="{row_class}" title="{'Has manual corrections' if has_overrides else ''}">
                            <td>{service['date']}{override_indicator}</td>
                            <td>{service.get('company', 'Unknown')}</td>
                            <td>{odometer}</td>
                            <td>{amount}</td>
                            <td>{invoice}</td>
                            <td class="source-file">{service['original_filename']}</td>
                        </tr>"""
        
        html_content += """
                    </tbody>
                </table>
            </div>
        </section>
    </main>

    <footer>
        <p>Generated by Car Service History Tool | Data from verified receipts</p>
    </footer>

    <script src="assets/script.js"></script>
    <script>
        // Load analytics data and initialize charts
        const analyticsData = """ + json.dumps(analytics) + """;
        initializeCharts(analyticsData);
    </script>
</body>
</html>"""
        
        with open(f"{self.site_dir}index.html", "w", encoding='utf-8') as f:
            f.write(html_content)

    def generate_receipt_pages(self):
        """Generate individual receipt detail pages"""
        print("📄 Generating receipt detail pages...")
        
        for service in self.service_data:
            date = service['date']
            
            # Check if OCR data exists
            ocr_file = f"{self.site_dir}data/ocr/{date}.txt"
            ocr_content = ""
            if os.path.exists(ocr_file):
                with open(ocr_file, 'r', encoding='utf-8') as f:
                    ocr_content = f.read()
            
            extraction_data = service.get('extraction_data', {})
            
            # Get override information
            override_info = service.get('verified_data', {}).get('override_info', {})
            has_overrides = override_info.get('has_overrides', False)
            overridden_fields = override_info.get('overridden_fields', {})
            override_reason = override_info.get('reason')
            
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Service Record: {date}</title>
    <link rel="stylesheet" href="../assets/style.css">
</head>
<body>
    <header class="receipt-header">
        <div class="container">
            <a href="../index.html" class="back-link">← Back to Service History</a>
            <h1>Service Record: {date}</h1>
            <div class="file-info">
                <span class="original-file">Original: {service['original_filename']}</span>
                <span class="renamed-file">Renamed: {service['renamed_filename']}</span>
            </div>
        </div>
    </header>

    <main class="receipt-detail">
        <div class="pdf-viewer">
            <embed src="../pdfs/{date}.pdf" type="application/pdf" width="100%" height="800px">
            <div class="pdf-fallback">
                <p>PDF viewer not supported. <a href="../pdfs/{date}.pdf" target="_blank">Download PDF</a></p>
            </div>
        </div>

        <div class="extraction-details">"""
            
            # Add override banner if there are overrides
            if has_overrides:
                override_fields_count = len(overridden_fields)
                html_content += f"""
            <div class="override-banner">
                ⚠️ This receipt contains manually corrected data
                <details class="override-details">
                    <summary>View corrections ({override_fields_count} field{'s' if override_fields_count != 1 else ''})</summary>"""
                
                if override_reason:
                    html_content += f"""
                    <p><strong>Reason:</strong> {override_reason}</p>"""
                
                html_content += """
                    <ul>"""
                
                for field, values in overridden_fields.items():
                    original = values.get('original', 'None')
                    override = values.get('override', 'None')
                    html_content += f"""
                        <li><strong>{field}:</strong> {original} → {override}</li>"""
                
                html_content += """
                    </ul>
                </details>
            </div>"""
            
            html_content += """
            <div class="verified-data">
                <h2>Verified Service Data</h2>
                <div class="field-grid">
                    <div class="field-item{' field-overridden' if 'date' in overridden_fields else ''}">
                        <label>Date:{' <span class="override-badge">Fixed</span>' if 'date' in overridden_fields else ''}</label>
                        <span>{service.get('date', 'N/A')}</span>
                    </div>
                    <div class="field-item{' field-overridden' if 'company' in overridden_fields else ''}">
                        <label>Company:{' <span class="override-badge">Fixed</span>' if 'company' in overridden_fields else ''}</label>
                        <span>{service.get('company', 'N/A')}</span>
                    </div>
                    <div class="field-item{' field-overridden' if 'amount' in overridden_fields else ''}">
                        <label>Amount:{' <span class="override-badge">Fixed</span>' if 'amount' in overridden_fields else ''}</label>
                        <span>{f"€{service.get('amount'):,.2f}" if service.get('amount') else "N/A"}</span>
                    </div>
                    <div class="field-item{' field-overridden' if 'vat_amount' in overridden_fields else ''}">
                        <label>VAT Amount:{' <span class="override-badge">Fixed</span>' if 'vat_amount' in overridden_fields else ''}</label>
                        <span>{f"€{service.get('vat_amount'):,.2f}" if service.get('vat_amount') else "N/A"}</span>
                    </div>
                    <div class="field-item{' field-overridden' if 'odometer_km' in overridden_fields else ''}">
                        <label>Odometer:{' <span class="override-badge">Fixed</span>' if 'odometer_km' in overridden_fields else ''}</label>
                        <span>{f"{service.get('odometer_km'):,} km" if service.get('odometer_km') else "N/A"}</span>
                    </div>
                    <div class="field-item{' field-overridden' if 'invoice_number' in overridden_fields else ''}">
                        <label>Invoice Number:{' <span class="override-badge">Fixed</span>' if 'invoice_number' in overridden_fields else ''}</label>
                        <span>{service.get('invoice_number', 'N/A')}</span>
                    </div>
                </div>
            </div>
"""
            
            if ocr_content:
                html_content += f"""
            <details class="ocr-section">
                <summary>Raw OCR Text ({len(ocr_content)} characters)</summary>
                <pre class="ocr-text">{ocr_content}</pre>
            </details>
"""
            
            if extraction_data:
                processing_steps = extraction_data.get('processing_steps', [])
                if processing_steps:
                    html_content += """
            <details class="processing-steps">
                <summary>Processing Details</summary>
                <div class="steps-list">
"""
                    for step in processing_steps:
                        step_name = step.get('step_name', 'unknown')
                        duration = step.get('duration_ms', 0)
                        html_content += f"""
                    <div class="step-item">
                        <strong>{step_name.title()}:</strong> {duration}ms
                    </div>
"""
                    html_content += """
                </div>
            </details>
"""
            
            html_content += """
        </div>
    </main>
</body>
</html>"""
            
            with open(f"{self.site_dir}receipts/{date}.html", "w", encoding='utf-8') as f:
                f.write(html_content)

    def copy_static_assets(self):
        """Copy CSS, JS and other static assets"""
        print("🎨 Creating static assets...")
        
        # Create CSS
        css_content = """
/* Car Service History Site Styles */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header */
.site-header {
    background: linear-gradient(135deg, #2c3e50, #3498db);
    color: white;
    padding: 2rem 0;
}

.car-info {
    display: flex;
    align-items: center;
    gap: 2rem;
}

.car-image-placeholder {
    width: 100px;
    height: 70px;
    background: rgba(255,255,255,0.1);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
}

.car-image-placeholder img {
    max-width: 100%;
    max-height: 100%;
    border-radius: 8px;
}

.car-image-fallback {
    font-size: 2rem;
}

.car-details h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

.car-specs {
    opacity: 0.9;
    font-size: 1.1rem;
}

/* Summary Cards */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin: 2rem 0;
}

.stat-card {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    text-align: center;
    transition: transform 0.2s;
}

.stat-card:hover {
    transform: translateY(-2px);
}

.stat-card h3 {
    color: #666;
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 0.5rem;
}

.stat-number {
    font-size: 2rem;
    font-weight: bold;
    color: #2c3e50;
    display: block;
    margin-bottom: 0.25rem;
}

.stat-period {
    font-size: 0.8rem;
    color: #888;
}

/* Analytics Sections */
.analytics-section {
    background: white;
    margin: 2rem 0;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.analytics-section h2 {
    margin-bottom: 1.5rem;
    color: #2c3e50;
}

.chart-container {
    position: relative;
    height: 400px;
    margin-bottom: 1rem;
}

.chart-controls {
    text-align: center;
    margin-top: 1rem;
}

.chart-controls label {
    margin: 0 1rem;
    cursor: pointer;
}

.dual-chart-container {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2rem;
}

.chart-half {
    text-align: center;
}

.chart-half canvas {
    max-height: 300px;
}

.chart-half h4 {
    margin-top: 1rem;
    color: #666;
}

/* Fuel methodology */
.fuel-methodology {
    margin-top: 1.5rem;
}

.fuel-methodology details {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
}

.fuel-methodology summary {
    cursor: pointer;
    font-weight: 500;
    color: #666;
}

.fuel-methodology ul {
    margin-top: 1rem;
    margin-left: 1rem;
}

.fuel-methodology li {
    margin-bottom: 0.5rem;
}

/* Service History Table */
.service-history {
    background: white;
    margin: 2rem 0;
    padding: 2rem;
    border-radius: 12px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.table-container {
    overflow-x: auto;
}

.service-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
}

.service-table th {
    background: #f8f9fa;
    padding: 1rem;
    text-align: left;
    border-bottom: 2px solid #dee2e6;
    cursor: pointer;
    user-select: none;
}

.service-table th:hover {
    background: #e9ecef;
}

.service-table td {
    padding: 1rem;
    border-bottom: 1px solid #dee2e6;
}

.clickable-row {
    cursor: pointer;
    transition: background-color 0.2s;
}

.clickable-row:hover {
    background-color: #f8f9fa;
}

.source-file {
    font-family: monospace;
    font-size: 0.8rem;
    color: #666;
}

/* Receipt Detail Pages */
.receipt-header {
    background: #2c3e50;
    color: white;
    padding: 1.5rem 0;
}

.back-link {
    color: white;
    text-decoration: none;
    display: inline-block;
    margin-bottom: 1rem;
}

.back-link:hover {
    text-decoration: underline;
}

.file-info {
    margin-top: 1rem;
    font-size: 0.9rem;
    opacity: 0.8;
}

.original-file,
.renamed-file {
    display: block;
    margin-bottom: 0.25rem;
}

.receipt-detail {
    display: grid;
    grid-template-columns: 1fr 400px;
    gap: 2rem;
    margin: 2rem auto;
    max-width: 1400px;
    padding: 0 20px;
}

.pdf-viewer {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.pdf-fallback {
    padding: 2rem;
    text-align: center;
    color: #666;
}

.extraction-details {
    background: white;
    padding: 2rem;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    height: fit-content;
}

.field-grid {
    display: grid;
    gap: 1rem;
    margin-top: 1rem;
}

.field-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem;
    background: #f8f9fa;
    border-radius: 6px;
}

.field-item label {
    font-weight: 500;
    color: #666;
}

.ocr-section,
.processing-steps {
    margin-top: 2rem;
}

.ocr-section details,
.processing-steps details {
    background: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
}

.ocr-section summary,
.processing-steps summary {
    cursor: pointer;
    font-weight: 500;
    margin-bottom: 1rem;
}

.ocr-text {
    font-family: monospace;
    font-size: 0.8rem;
    line-height: 1.4;
    background: white;
    padding: 1rem;
    border-radius: 6px;
    max-height: 300px;
    overflow-y: auto;
}

.steps-list {
    margin-top: 1rem;
}

.step-item {
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: white;
    border-radius: 6px;
}

/* Override Indicators */
.has-overrides {
    border-left: 3px solid #f39c12;
}

.override-indicator {
    font-size: 0.9em;
    margin-left: 4px;
    opacity: 0.8;
}

.field-overridden {
    background-color: #fff3cd;
    border-left: 3px solid #f39c12;
}

.override-banner {
    background: #fff3cd;
    border: 1px solid #f39c12;
    padding: 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    color: #856404;
}

.override-banner details {
    margin-top: 0.5rem;
}

.override-banner summary {
    cursor: pointer;
    font-weight: 500;
}

.override-banner ul {
    margin-top: 0.5rem;
    margin-left: 1rem;
}

.override-badge {
    background: #f39c12;
    color: white;
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: 3px;
    margin-left: 4px;
    font-weight: normal;
}

/* Footer */
footer {
    text-align: center;
    padding: 2rem;
    color: #666;
    border-top: 1px solid #dee2e6;
    margin-top: 3rem;
}

/* Responsive */
@media (max-width: 768px) {
    .car-info {
        flex-direction: column;
        text-align: center;
    }
    
    .dual-chart-container {
        grid-template-columns: 1fr;
    }
    
    .receipt-detail {
        grid-template-columns: 1fr;
    }
    
    .summary-cards {
        grid-template-columns: 1fr;
    }
}
"""
        
        with open(f"{self.site_dir}assets/style.css", "w", encoding='utf-8') as f:
            f.write(css_content)
        
        # Create JavaScript
        js_content = """
// Car Service History Site Scripts

let maintenanceChart = null;
let mileageChart = null;
let fuelChart = null;

function initializeCharts(analyticsData) {
    createMaintenanceChart(analyticsData.maintenance);
    createMileageChart(analyticsData.mileage);
    createFuelChart(analyticsData.fuel);
    
    // Add chart controls
    setupChartControls();
}

function createMaintenanceChart(maintenanceData) {
    const ctx = document.getElementById('maintenanceChart').getContext('2d');
    
    const years = Object.keys(maintenanceData.yearly_costs).sort();
    const yearlyCosts = years.map(year => maintenanceData.yearly_costs[year]);
    const movingAverage = years.map(year => maintenanceData.moving_average_3yr[year] || null);
    
    maintenanceChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: years,
            datasets: [
                {
                    label: 'Annual Cost (€)',
                    data: yearlyCosts,
                    borderColor: '#e74c3c',
                    backgroundColor: 'rgba(231, 76, 60, 0.1)',
                    fill: true,
                    tension: 0.1,
                    pointBackgroundColor: '#e74c3c',
                    pointBorderColor: '#c0392b',
                    pointRadius: 5
                },
                {
                    label: '3-Year Moving Average (€)',
                    data: movingAverage,
                    borderColor: '#3498db',
                    backgroundColor: 'transparent',
                    borderWidth: 3,
                    fill: false,
                    tension: 0.1,
                    pointBackgroundColor: '#3498db',
                    pointBorderColor: '#2980b9',
                    pointRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '€' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    callbacks: {
                        label: function(context) {
                            return context.dataset.label + ': €' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            },
            interaction: {
                mode: 'nearest',
                axis: 'x',
                intersect: false
            }
        }
    });
}

function createMileageChart(mileageData) {
    const ctx = document.getElementById('mileageChart').getContext('2d');
    
    const years = Object.keys(mileageData.yearly).sort();
    const yearlyKm = years.map(year => mileageData.yearly[year]);
    
    mileageChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [{
                label: 'km/year',
                data: yearlyKm,
                backgroundColor: '#27ae60',
                borderColor: '#229954',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString() + ' km';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return context.parsed.y.toLocaleString() + ' km';
                        }
                    }
                }
            }
        }
    });
}

function createFuelChart(fuelData) {
    const ctx = document.getElementById('fuelChart').getContext('2d');
    
    const years = Object.keys(fuelData).sort();
    const fuelCosts = years.map(year => fuelData[year]);
    
    fuelChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: years,
            datasets: [{
                label: 'Estimated €/year',
                data: fuelCosts,
                backgroundColor: '#f39c12',
                borderColor: '#e67e22',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return '€' + value.toLocaleString();
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return 'Est. €' + context.parsed.y.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

function setupChartControls() {
    const absoluteCheckbox = document.getElementById('showAbsolute');
    const movingAvgCheckbox = document.getElementById('showMovingAvg');
    
    if (absoluteCheckbox && movingAvgCheckbox && maintenanceChart) {
        absoluteCheckbox.addEventListener('change', function() {
            maintenanceChart.data.datasets[0].hidden = !this.checked;
            maintenanceChart.update();
        });
        
        movingAvgCheckbox.addEventListener('change', function() {
            maintenanceChart.data.datasets[1].hidden = !this.checked;
            maintenanceChart.update();
        });
    }
}

function openReceipt(date) {
    window.location.href = `receipts/${date}.html`;
}

// Table sorting functionality
let sortDirection = {};

function sortTable(columnIndex) {
    const table = document.getElementById('serviceTable');
    const tbody = table.getElementsByTagName('tbody')[0];
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    const isNumeric = columnIndex === 2 || columnIndex === 3; // Odometer or Cost
    const isDate = columnIndex === 0;
    
    // Toggle sort direction
    sortDirection[columnIndex] = sortDirection[columnIndex] === 'asc' ? 'desc' : 'asc';
    
    rows.sort((a, b) => {
        let aValue = a.cells[columnIndex].textContent.trim();
        let bValue = b.cells[columnIndex].textContent.trim();
        
        if (isDate) {
            aValue = new Date(aValue);
            bValue = new Date(bValue);
        } else if (isNumeric) {
            aValue = parseFloat(aValue.replace(/[€,km\\s]/g, '')) || 0;
            bValue = parseFloat(bValue.replace(/[€,km\\s]/g, '')) || 0;
        }
        
        if (aValue < bValue) return sortDirection[columnIndex] === 'asc' ? -1 : 1;
        if (aValue > bValue) return sortDirection[columnIndex] === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Clear tbody and append sorted rows
    while (tbody.firstChild) {
        tbody.removeChild(tbody.firstChild);
    }
    
    rows.forEach(row => tbody.appendChild(row));
    
    // Update header indicators
    updateSortIndicators(columnIndex);
}

function updateSortIndicators(activeColumn) {
    const headers = document.querySelectorAll('#serviceTable th');
    headers.forEach((header, index) => {
        const text = header.textContent.replace(/[↑↓]/g, '').trim();
        if (index === activeColumn) {
            header.textContent = text + (sortDirection[activeColumn] === 'asc' ? ' ↑' : ' ↓');
        } else {
            header.textContent = text;
        }
    });
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Any additional initialization can go here
    console.log('Car Service History site loaded');
});
"""
        
        with open(f"{self.site_dir}assets/script.js", "w", encoding='utf-8') as f:
            f.write(js_content)
        
        # Create placeholder car image (simple SVG)
        placeholder_svg = """<svg width="100" height="70" xmlns="http://www.w3.org/2000/svg">
  <rect width="100" height="70" rx="8" fill="rgba(255,255,255,0.2)"/>
  <text x="50" y="40" font-family="Arial" font-size="24" fill="white" text-anchor="middle">🚗</text>
</svg>"""
        
        with open(f"{self.site_dir}assets/car-placeholder.svg", "w", encoding='utf-8') as f:
            f.write(placeholder_svg)

    def serve_site(self, port=8000):
        """Serve the site locally"""
        if not os.path.exists(self.site_dir):
            print(f"❌ Site directory {self.site_dir} does not exist. Run 'python site.py build' first.")
            return
        
        os.chdir(self.site_dir)
        
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            print(f"🌐 Serving site at http://localhost:{port}")
            print("Press Ctrl+C to stop the server")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\n🛑 Server stopped")

    def clean_site(self):
        """Clean generated site files"""
        if os.path.exists(self.site_dir):
            shutil.rmtree(self.site_dir)
            print(f"🧹 Cleaned site directory: {self.site_dir}")
        else:
            print(f"ℹ️  Site directory {self.site_dir} does not exist")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description="Car Service History Site Operations")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Generate complete static site')
    build_parser.add_argument('--force', action='store_true', help='Force rebuild even if site exists')
    
    # Serve command
    serve_parser = subparsers.add_parser('serve', help='Serve site locally')
    serve_parser.add_argument('--port', type=int, default=8000, help='Port to serve on (default: 8000)')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate source data')
    
    # Clean command
    clean_parser = subparsers.add_parser('clean', help='Clean generated files')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    site_manager = ServiceHistorySiteManager()
    
    if args.command == 'build':
        success = site_manager.build_site(force=args.force)
        sys.exit(0 if success else 1)
    elif args.command == 'serve':
        site_manager.serve_site(args.port)
    elif args.command == 'validate':
        success = site_manager.validate_source_data()
        sys.exit(0 if success else 1)
    elif args.command == 'clean':
        site_manager.clean_site()


if __name__ == "__main__":
    main()
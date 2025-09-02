#!/usr/bin/env python3
"""
Generate static HTML site from the data model for service history visualization.
"""

import json
from pathlib import Path
from datetime import datetime


def generate_html(data_model: dict) -> str:
    """Generate the complete HTML page with embedded CSS and JavaScript"""
    
    html_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vehicle_make} {vehicle_model} Service History</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .vehicle-image {{
            width: 100%;
            max-width: 600px;
            height: 300px;
            object-fit: cover;
            border-radius: 10px;
            margin: 20px auto;
            display: block;
            background: #f0f0f0;
        }}
        
        h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }}
        
        .charts-section {{
            padding: 30px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            height: 280px; /* Fixed height for chart containers */
            display: flex;
            flex-direction: column;
        }}
        
        .chart-title {{
            font-size: 1.5em;
            margin-bottom: 20px;
            color: #333;
        }}
        
        #costChart, #cumulativeChart, #distributionChart {{
            max-width: 100%;
            flex: 1;
            min-height: 0; /* Important for flex child to shrink */
        }}
        
        .table-section {{
            padding: 30px;
        }}
        
        .service-table {{
            width: 100%;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-height: 600px;
            overflow-y: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        tbody tr {{
            cursor: pointer;
            transition: background-color 0.2s ease;
            position: relative;
            z-index: 2;
            pointer-events: all;
        }}
        
        tbody tr:hover {{
            background-color: #f8f9ff !important;
            transform: scale(1.001);
        }}
        
        tbody tr:focus {{
            outline: 2px solid #667eea;
            outline-offset: -2px;
            background-color: #f0f4ff !important;
        }}
        
        .table-container {{
            position: relative;
        }}
        
        thead {{
            background: #667eea;
            color: white;
            position: relative;
            z-index: 1;
        }}
        
        thead th {{
            position: relative;
            pointer-events: none;
        }}
        
        th, td {{
            padding: 15px;
            text-align: left;
        }}
        
        tbody tr {{
            border-bottom: 1px solid #eee;
            cursor: pointer;
            transition: background 0.3s;
        }}
        
        tbody tr:hover {{
            background: #f8f9fa;
        }}
        
        .amount {{
            font-weight: bold;
            color: #667eea;
        }}
        
        .provider {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .detail-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            z-index: 1000;
            padding: 20px;
            overflow-y: auto;
        }}
        
        .modal-content {{
            background: white;
            max-width: 800px;
            margin: 50px auto;
            border-radius: 15px;
            padding: 30px;
            position: relative;
        }}
        
        .close-modal {{
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 30px;
            cursor: pointer;
            color: #999;
        }}
        
        .close-modal:hover {{
            color: #333;
        }}
        
        .detail-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        
        .detail-item {{
            padding: 10px;
            background: #f8f9fa;
            border-radius: 5px;
        }}
        
        .detail-label {{
            font-size: 0.9em;
            color: #666;
            margin-bottom: 5px;
        }}
        
        .detail-value {{
            font-size: 1.1em;
            font-weight: bold;
            color: #333;
        }}
        
        .items-list {{
            margin-top: 20px;
        }}
        
        .item-row {{
            padding: 10px;
            background: #f8f9fa;
            margin-bottom: 10px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
        }}
        
        @media (max-width: 768px) {{
            .stats-grid {{
                grid-template-columns: 1fr;
            }}
            
            .detail-grid {{
                grid-template-columns: 1fr;
            }}
            
            th, td {{
                padding: 10px;
                font-size: 0.9em;
            }}
        }}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="{vehicle_image}" alt="{vehicle_make} {vehicle_model}" class="vehicle-image">
            <h1>{vehicle_make} {vehicle_model}</h1>
            <div class="subtitle">Registration: {vehicle_reg} | Service History Analysis</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_services}</div>
                <div class="stat-label">Total Services</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">€{total_cost}</div>
                <div class="stat-label">Total Cost</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">€{average_cost}</div>
                <div class="stat-label">Average Cost</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{date_years}</div>
                <div class="stat-label">Years Tracked</div>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-container">
                <h2 class="chart-title">Service Costs Over Time</h2>
                <canvas id="costChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h2 class="chart-title">Cumulative Spending</h2>
                <canvas id="cumulativeChart"></canvas>
            </div>
            
            <div class="chart-container">
                <h2 class="chart-title">Cost Distribution</h2>
                <canvas id="distributionChart"></canvas>
            </div>
        </div>
        
        <div class="table-section">
            <h2 class="chart-title">Service History Details</h2>
            <div class="service-table">
                <table id="serviceTable">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Provider</th>
                            <th>Odometer</th>
                            <th>Amount</th>
                            <th>Invoice</th>
                        </tr>
                    </thead>
                    <tbody id="tableBody">
                        <!-- Table rows will be inserted here -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div id="detailModal" class="detail-modal">
        <div class="modal-content">
            <span class="close-modal" onclick="closeModal()">&times;</span>
            <h2 id="modalTitle">Service Details</h2>
            <div id="modalContent">
                <!-- Modal content will be inserted here -->
            </div>
        </div>
    </div>
    
    <script>
        // Service data embedded
        const serviceData = {data_json};
        
        // Initialize charts
        function initCharts() {{
            const chartData = serviceData.charts;
            
            // Cost over time chart
            const costCtx = document.getElementById('costChart').getContext('2d');
            new Chart(costCtx, {{
                type: 'line',
                data: {{
                    labels: chartData.time_series.map(d => d.date),
                    datasets: [{{
                        label: 'Service Cost (€)',
                        data: chartData.time_series.map(d => d.cost),
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: function(value) {{
                                    return '€' + value;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
            
            // Cumulative chart
            const cumCtx = document.getElementById('cumulativeChart').getContext('2d');
            new Chart(cumCtx, {{
                type: 'line',
                data: {{
                    labels: chartData.time_series.map(d => d.date),
                    datasets: [{{
                        label: 'Cumulative Cost (€)',
                        data: chartData.time_series.map(d => d.cumulative),
                        borderColor: '#764ba2',
                        backgroundColor: 'rgba(118, 75, 162, 0.1)',
                        fill: true,
                        tension: 0.4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                callback: function(value) {{
                                    return '€' + value.toLocaleString();
                                }}
                            }}
                        }}
                    }}
                }}
            }});
            
            // Distribution chart
            const distCtx = document.getElementById('distributionChart').getContext('2d');
            const distData = chartData.cost_distribution;
            new Chart(distCtx, {{
                type: 'bar',
                data: {{
                    labels: Object.keys(distData),
                    datasets: [{{
                        label: 'Number of Services',
                        data: Object.values(distData),
                        backgroundColor: [
                            'rgba(102, 126, 234, 0.8)',
                            'rgba(118, 75, 162, 0.8)',
                            'rgba(102, 126, 234, 0.6)',
                            'rgba(118, 75, 162, 0.6)',
                            'rgba(102, 126, 234, 0.4)',
                            'rgba(118, 75, 162, 0.4)'
                        ]
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            display: false
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            ticks: {{
                                stepSize: 1
                            }}
                        }}
                    }}
                }}
            }});
        }}
        
        // Populate service table
        function populateTable() {{
            const tbody = document.getElementById('tableBody');
            serviceData.receipts.forEach((receipt, index) => {{
                const row = document.createElement('tr');
                row.style.cursor = 'pointer';
                row.setAttribute('data-receipt-index', index);
                row.setAttribute('tabindex', '0');
                
                // Add multiple event handlers for better compatibility
                row.addEventListener('click', (e) => {{
                    e.preventDefault();
                    e.stopPropagation();
                    showDetails(index);
                }});
                
                row.addEventListener('keydown', (e) => {{
                    if (e.key === 'Enter' || e.key === ' ') {{
                        e.preventDefault();
                        e.stopPropagation();
                        showDetails(index);
                    }}
                }});
                
                row.innerHTML = `
                    <td>${{receipt.service_date || 'N/A'}}</td>
                    <td class="provider">${{receipt.service_provider || receipt.company || 'Unknown'}}</td>
                    <td>${{receipt.odometer_km ? receipt.odometer_km.toLocaleString() + ' km' : 'N/A'}}</td>
                    <td class="amount">€${{(receipt.total_with_vat || receipt.total_amount || 0).toFixed(2)}}</td>
                    <td>${{receipt.invoice_number || 'N/A'}}</td>
                `;
                tbody.appendChild(row);
            }});
        }}
        
        // Show service details modal
        function showDetails(index) {{
            const receipt = serviceData.receipts[index];
            const modal = document.getElementById('detailModal');
            const modalContent = document.getElementById('modalContent');
            
            let itemsHtml = '';
            if (receipt.service_items && receipt.service_items.length > 0) {{
                itemsHtml = '<h3>Service Items</h3><div class="items-list">';
                receipt.service_items.forEach(item => {{
                    itemsHtml += `
                        <div class="item-row">
                            <span>${{item.description || 'Service'}}</span>
                            <span>€${{(item.total_price || item.amount || 0).toFixed(2)}}</span>
                        </div>
                    `;
                }});
                itemsHtml += '</div>';
            }} else if (receipt.items && receipt.items.length > 0) {{
                itemsHtml = '<h3>Service Items</h3><div class="items-list">';
                receipt.items.forEach(item => {{
                    itemsHtml += `
                        <div class="item-row">
                            <span>${{item.description || item.item || 'Service'}}</span>
                            <span>€${{(item.amount || 0).toFixed(2)}}</span>
                        </div>
                    `;
                }});
                itemsHtml += '</div>';
            }}
            
            modalContent.innerHTML = `
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="detail-label">Date</div>
                        <div class="detail-value">${{receipt.service_date || 'N/A'}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Invoice Number</div>
                        <div class="detail-value">${{receipt.invoice_number || 'N/A'}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Provider</div>
                        <div class="detail-value">${{receipt.service_provider || receipt.company || 'Unknown'}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Vehicle</div>
                        <div class="detail-value">${{receipt.vehicle_reg || 'N/A'}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Odometer</div>
                        <div class="detail-value">${{receipt.odometer_km ? receipt.odometer_km.toLocaleString() + ' km' : 'N/A'}}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Total Amount</div>
                        <div class="detail-value">€${{(receipt.total_with_vat || receipt.total_amount || 0).toFixed(2)}}</div>
                    </div>
                    ${{receipt.vat_amount ? `
                    <div class="detail-item">
                        <div class="detail-label">VAT Amount</div>
                        <div class="detail-value">€${{receipt.vat_amount.toFixed(2)}}</div>
                    </div>` : ''}}
                    ${{receipt.next_service_km ? `
                    <div class="detail-item">
                        <div class="detail-label">Next Service</div>
                        <div class="detail-value">${{receipt.next_service_km.toLocaleString()}} km</div>
                    </div>` : ''}}
                </div>
                ${{itemsHtml}}
            `;
            
            modal.style.display = 'block';
        }}
        
        // Close modal
        function closeModal() {{
            document.getElementById('detailModal').style.display = 'none';
        }}
        
        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modal = document.getElementById('detailModal');
            if (event.target == modal) {{
                modal.style.display = 'none';
            }}
        }}
        
        // Initialize everything when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            initCharts();
            populateTable();
        }});
    </script>
</body>
</html>'''
    
    # Calculate years tracked
    stats = data_model.get('statistics', {})
    date_range = stats.get('date_range', {})
    years = 0
    if date_range.get('start') and date_range.get('end'):
        start_year = int(date_range['start'][:4])
        end_year = int(date_range['end'][:4])
        years = end_year - start_year + 1
    
    # Format the HTML with data
    html = html_template.format(
        vehicle_make=data_model['vehicle']['make'],
        vehicle_model=data_model['vehicle']['model'],
        vehicle_reg=data_model['vehicle']['registration'],
        vehicle_image=data_model['vehicle']['image_placeholder'],
        total_services=stats.get('total_services', 0),
        total_cost=f"{stats.get('total_cost', 0):,.2f}",
        average_cost=f"{stats.get('average_cost', 0):.2f}",
        date_years=f"{years} years" if years else "N/A",
        data_json=json.dumps(data_model, ensure_ascii=False)
    )
    
    return html


def generate_static_site():
    """Main function to generate the static site"""
    
    print("Generating static site...")
    
    # Load data model
    data_model_file = "service_data_model.json"
    if not Path(data_model_file).exists():
        print(f"Error: {data_model_file} not found. Run generate_data_model.py first.")
        return
    
    with open(data_model_file, 'r', encoding='utf-8') as f:
        data_model = json.load(f)
    
    print(f"  Loaded data model with {len(data_model.get('receipts', []))} receipts")
    
    # Generate HTML
    html = generate_html(data_model)
    
    # Save HTML file
    output_file = "service_history.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ Static site generated: {output_file}")
    print(f"  Open {output_file} in your browser to view the visualization")
    
    # Also create a simple index.html that redirects
    index_html = '''<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="refresh" content="0; url=service_history.html">
    <title>Redirecting...</title>
</head>
<body>
    <p>Redirecting to <a href="service_history.html">service history</a>...</p>
</body>
</html>'''
    
    with open("index.html", 'w') as f:
        f.write(index_html)
    
    print("✓ Created index.html redirect")


if __name__ == "__main__":
    generate_static_site()
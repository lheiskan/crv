# Car Service Receipt Extraction & Analysis

A Python-based system for extracting and analyzing car service receipts from PDF documents, with support for multiple formats, languages, and receipt types.

## Overview

This project processes scanned car service receipts (primarily from Finnish service providers) to extract structured data and build a comprehensive service history timeline. It handles both simple single-page receipts and complex multi-page documents with mixed content.

## Features

### 🔍 Intelligent PDF Processing
- **OCR Support**: Extracts text from scanned PDFs using Tesseract OCR
- **Multi-language**: Supports Finnish and English text recognition
- **Multi-page handling**: Processes documents with multiple receipts
- **Automatic company detection**: Identifies service providers automatically

### 📊 Data Extraction
- Service dates and invoice numbers
- Vehicle registration and odometer readings
- Itemized service details and parts
- Cost breakdowns (labor, parts, VAT)
- Next service recommendations

### 📈 Analysis & Visualization
- Timeline visualization of service history
- Cost analysis and trends
- Service interval tracking
- Provider comparison
- Comprehensive statistics

## Supported Service Providers

- **Järvenpään Automajor Oy**
- **Veho Autotalot**
- **A-Katsastus** (Vehicle Inspection)
- **Sulan Katsastus** (Vehicle Inspection)
- **First Stop** (Tire Services)
- **Euromaster** (Tire Services)

## Project Structure

```
crv/
├── receipts/                    # Original single-page receipts (35 files)
├── receipts_2/                   # Complex multi-page receipts (5 files)
├── receipts_json/                # Individual receipt JSON files
├── extract_receipts.py           # Main extraction script for simple receipts
├── extract_complex_receipts.py   # Enhanced extraction for complex PDFs
├── visualize_timeline.py         # Timeline and analysis visualization
├── service_history.json          # Combined data from receipts/
├── complex_receipts.json         # Combined data from receipts_2/
├── service_timeline.png          # Generated visualization
└── requirements.txt              # Python dependencies
```

## Installation

1. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install system dependencies:
```bash
# macOS
brew install tesseract tesseract-lang poppler

# Linux
sudo apt-get install tesseract-ocr tesseract-ocr-fin poppler-utils
```

## Usage

### Extract Simple Receipts
```bash
python extract_receipts.py
```
Processes PDFs in `receipts/` folder and generates `service_history.json`

### Extract Complex Multi-page Receipts
```bash
python extract_complex_receipts.py
```
Processes PDFs in `receipts_2/` folder with enhanced parsing for multiple formats

### Generate Timeline Visualization
```bash
python visualize_timeline.py
```
Creates visual analysis and timeline from extracted data

## Current Status

### ✅ Completed
- Basic OCR extraction pipeline
- Support for major Finnish service providers
- Multi-page PDF processing
- Individual JSON export for each receipt
- Timeline visualization with cost analysis
- Automatic odometer reading correction

### 📊 Extraction Results
- **Simple receipts**: 21/35 successfully extracted (60% success rate)
- **Complex receipts**: 8 receipts extracted from 5 multi-page PDFs
- **Total documented services**: 29 receipts
- **Date range**: 2018-2025
- **Total costs tracked**: €5,434+

### 🔧 Known Issues
- Handwritten data extraction has lower accuracy
- Some receipt formats not fully supported
- Mixed success with heavily degraded scans
- Receipt boundary detection in combined PDFs needs improvement

## Data Format

Each extracted receipt contains:
```json
{
  "invoice_number": "13764",
  "service_date": "2024-11-05",
  "vehicle_reg": "LTI-509",
  "odometer_km": 387551,
  "service_items": [
    {
      "description": "Oil change",
      "quantity": 1,
      "unit_price": 69.35,
      "total_price": 69.35
    }
  ],
  "total_with_vat": 240.00,
  "service_provider": "Järvenpään Automajor Oy",
  "next_service_km": 387651
}
```

## Future Enhancements

### Short-term
- [ ] Improve handwritten text recognition
- [ ] Add receipt naming system (date + company + invoice)
- [ ] Create individual PDFs for each receipt in multi-page documents
- [ ] Add confidence scores to extracted data

### Long-term
- [ ] LLM-based parsing for better accuracy
- [ ] Web interface for manual review/correction
- [ ] Automatic receipt categorization
- [ ] Predictive maintenance recommendations
- [ ] Export to accounting software formats
- [ ] Mobile app for receipt capture

## Key Findings

From the analyzed Honda CR-V (LTI-509) service history:
- **Average service cost**: €296
- **Average service interval**: 15,639 km
- **Annual driving**: ~20,836 km
- **Cost per 1000 km**: €35.35
- **Primary service provider**: Järvenpään Automajor Oy

## Technologies Used

- **Python 3.x**
- **OCR**: Tesseract with Finnish language support
- **PDF Processing**: pdfplumber, PyPDF2, pdf2image
- **Data Analysis**: pandas, numpy
- **Visualization**: matplotlib
- **Image Processing**: PIL/Pillow

## License

This project is for personal use. The extraction logic and analysis tools can be adapted for other vehicle service tracking needs.

## Contributing

This is a personal project, but suggestions for improving extraction accuracy or adding new receipt formats are welcome.

---

*Note: This system is specifically tuned for Finnish automotive service receipts but can be adapted for other languages and formats.*
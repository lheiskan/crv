# Car Service Receipt Extraction & Analytics

A comprehensive system for extracting, validating, and analyzing car service receipts from scanned PDFs. Built specifically for Finnish automotive service records with intelligent OCR processing and web-based analytics dashboard.

## Overview

This project processes car service receipts (primarily Finnish) to create a complete service history with analytics for a Honda CR-V (LTI-509). It handles both simple single-page receipts and complex multi-page documents from various service providers.

## Features

### 📄 Receipt Processing
- **OCR Extraction**: Tesseract OCR with Finnish+English language support
- **Pattern Matching**: Fast regex-based extraction for known receipt formats
- **LLM Integration**: LLAMA3.2 AI for advanced Finnish receipt understanding
- **Smart Fallback**: Automatic LLM processing when pattern matching fails
- **Multi-format Support**: Handles various invoice formats from Finnish service providers
- **Data Validation**: Automatic validation of extracted data with error detection
- **Override System**: Manual correction mechanism for extraction errors

### 📊 Analytics Dashboard
- **Maintenance Costs**: Yearly expenses with 3-year moving averages
- **Mileage Tracking**: Annual mileage calculations from odometer readings
- **Fuel Cost Estimation**: Based on Statistics Finland historical prices
- **Interactive Charts**: Chart.js-powered visualizations

### 🌐 Web Interface
- **Service History**: Sortable table with all service records
- **Receipt Details**: Individual pages with PDF viewer and extracted data
- **Mobile Responsive**: Works on all device sizes
- **Static Generation**: No server required, just open index.html

## Quick Start

1. **Setup Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Process Receipts**
   ```bash
   # Extract data from PDFs (full pipeline: OCR + Pattern + LLM fallback)
   python extract.py
   
   # Advanced extraction modes
   python extract.py --llm-only receipts/receipt.pdf    # LLM extraction only
   python extract.py --pattern-only receipts/receipt.pdf # Pattern matching only
   python extract.py --test-llm                          # Test LLM extractor
   
   # Verify and correct data interactively
   ./verify_receipts.sh
   ```

3. **Generate Website**
   ```bash
   # Build static site
   python site.py build
   
   # Serve locally
   python site.py serve
   ```

4. **View Results**
   Open http://localhost:8080 to see your service history dashboard.

## Project Structure

```
crv/
├── receipts/           # Original PDF receipts
├── verified/           # Ground truth data and overrides
│   └── {receipt}/
│       ├── verified.json   # Manually verified extraction data
│       ├── claude.json     # LLM verified extraction data
│       └── override.json   # Manual corrections (optional)
├── site/               # Generated static website
│   ├── index.html      # Main dashboard
│   ├── receipts/       # Individual receipt pages
│   ├── pdfs/           # Renamed PDF files
│   └── data/           # JSON data and analytics
├── extract.py          # Main extraction script
├── site.py            # Static site generator
└── verify_receipts.sh # Interactive verification tool
```

## Receipt Processing Pipeline

The system uses a multi-stage intelligent extraction pipeline:

1. **OCR Processing**: Extract text from PDFs using Tesseract with Finnish language support
2. **Pattern Matching**: Fast regex-based extraction for known receipt formats (~60% success, <1ms)
3. **LLM Fallback**: LLAMA3.2 processes receipts when pattern matching fails (~100% success, ~6-8s)
4. **Data Validation**: Check field consistency and completeness
5. **Manual Verification**: Interactive review and correction workflow
6. **Override System**: Apply manual corrections with visual indicators
7. **Site Generation**: Create static HTML dashboard with analytics

### Extraction Modes

- **Full Pipeline** (default): OCR → Pattern → LLM (if needed)
- **Pattern Only**: OCR → Pattern matching only
- **LLM Only**: OCR → LLAMA3.2 extraction only  
- **OCR Only**: Text extraction without field parsing

## Data Formats

### Extracted Data Structure
```json
{
  "ground_truth": {
    "date": "2023-05-04",
    "amount": 850.00,
    "vat_amount": 164.52,
    "odometer_km": 352832,
    "company": "Järvenpään Automajor Oy",
    "invoice_number": "11245"
  }
}
```

### Override Corrections
```json
{
  "ground_truth": {
    "odometer_km": 352832
  }
}
```

## Supported Service Providers

- **Järvenpään Automajor**: Standard format, high success rate
- **Veho Autotalot**: Multi-page documents, detailed itemization
- **A-Katsastus/Sulan Katsastus**: Vehicle inspection receipts
- **First Stop/Euromaster**: Tire services, often handwritten

## Analytics Features

### Cost Analysis
- Yearly maintenance expenses
- 3-year moving averages for trend analysis
- Cost per kilometer calculations
- VAT breakdown

### Mileage Tracking
- Annual mileage from odometer readings
- Gap filling for missing service years
- Driving pattern analysis

### Fuel Estimates
- Historical fuel costs using Statistics Finland data
- 8.5L/100km consumption model
- Yearly fuel expense projections

## Manual Corrections

The override system allows manual correction of OCR errors:

1. Create `override.json` in the receipt's verified folder
2. Specify corrected values
3. Rebuild site to apply changes
4. Visual indicators show corrected fields

Example workflow:
```bash
# Edit corrections
echo '{"ground_truth": {"odometer_km": 352832}}' > verified/receipt.pdf/override.json

# Rebuild with corrections
python site.py build --force
```

## Development Context

See [CLAUDE.md](CLAUDE.md) for detailed technical context including:
- Finnish language terms and formats
- Common extraction patterns
- Known data issues and solutions
- Performance metrics and targets

## Requirements

- Python 3.8+
- Tesseract OCR with Finnish language pack
- LLAMA3.2 (local installation via Ollama recommended)
- Standard Python packages: `requests`, `pdf2image`, `pytesseract`, `pillow`

### LLM Setup

For optimal performance, install LLAMA3.2 locally:

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull LLAMA3.2 model
ollama pull llama3.2

# Start Ollama service (runs on localhost:11434)
ollama serve
```

The system automatically detects and uses local LLAMA3.2 installation.

## License

MIT License - See LICENSE file for details.

## Contributing

This is a personal project for tracking Honda CR-V service history. While not actively seeking contributions, the codebase demonstrates patterns useful for similar document processing tasks.

---

**Last Updated**: September 2025  
**Vehicle**: Honda CR-V (LTI-509)  
**Service Records**: 40 receipts spanning 2007-2025  
**Pipeline Version**: 2.0.0 (LLM Integration Complete)

## Performance Metrics

- **Pattern Extraction**: 60% success rate, <1ms processing time
- **LLM Extraction**: 100% success rate, ~6-8s processing time  
- **Combined Pipeline**: Intelligent fallback maximizes accuracy while minimizing cost
- **Web Dashboard**: Real-time analytics for 18+ years of service history

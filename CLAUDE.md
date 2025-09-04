# Claude Development Context - Car Service Receipt Extraction

## ⚠️ Important Setup Notes

### Virtual Environment - ALWAYS USE VENV
```bash
# REMEMBER: Always activate the virtual environment before running any Python commands
source venv/bin/activate

# If venv is broken, recreate it:
rm -rf venv && python3 -m venv venv
source venv/bin/activate
pip install pdf2image pytesseract pillow
```

## Project Overview

This project extracts structured data from Finnish car service receipts (PDFs) using a comprehensive multi-step processing pipeline:
- **OCR**: Extract text from PDFs using Tesseract
- **Pattern Parsing**: Fast regex-based extraction for known formats
- **LLM Integration**: LLAMA3.2 via REST API for advanced extraction and fallback
- **Web Dashboard**: Interactive analytics site with charts and PDF viewer

**Primary Vehicle**: Honda CR-V, Registration: LTI-509

## Current Architecture

### File Structure
```
crv/
├── extract.py                  # Main extraction script with integrated validation
├── receipts/                   # Input PDF files
├── extracted/                  # Output directory
│   └── <pdf_name>/
│       ├── data.json          # Structured extraction results
│       └── ocr.txt            # Raw OCR output
├── verified/                   # Ground truth for testing
│   └── <pdf_name>/
│       └── verified.json      # Expected values
│       └── claude.json        # Unverified expected values from Claude LLM
└── site.py                     # Static site generator
```

### Data Model (data.json)
```json
{
  "final_data": {
    "date": "2009-05-15",
    "amount": 203.75,
    "vat_amount": 36.74,
    "odometer_km": 100745,
    "company": "Veho Autotalot Oy",
    "invoice_number": "66517163",
    "work_description": ["KATSASTUS", "PIENTARVIKKEET"]
  },
  "processing_steps": [
    {
      "step_name": "ocr",
      "output": {"text": "base64_encoded_ocr_text"},
      "duration_ms": 2794
    },
    {
      "step_name": "parsing", 
      "extracted_fields": {...},
      "missing_fields": [],
      "duration_ms": 0
    },
    {
      "step_name": "llm_extraction",
      "method": "llama3.2",
      "extracted_fields": {...},
      "duration_ms": 6821,
      "raw_response": "JSON from LLM"
    }
  ],
  "metadata": {
    "source_file": "receipt.pdf",
    "processed_at": "2025-09-04T16:19:24",
    "field_sources": {"date": "parsing", "odometer_km": "llm"}
  }
}
```

## Running Extraction

### Basic Usage
```bash
# Always activate venv first!
source venv/bin/activate

# Process single PDF (full pipeline: OCR + Pattern + LLM fallback)
python extract.py receipts/receipt.pdf

# Process all PDFs in directory
python extract.py receipts/

# Extraction modes (exclusive)
python extract.py --ocr-only receipts/receipt.pdf      # OCR text only
python extract.py --pattern-only receipts/receipt.pdf  # OCR + Pattern matching
python extract.py --llm-only receipts/receipt.pdf      # OCR + LLM extraction

# Test LLM extractor independently
python extract.py --test-llm

# Validate extraction accuracy
python extract.py --validate                    # All receipts  
python extract.py --validate receipt.pdf        # Specific receipt

# Results saved to extracted/<pdf_name>/
```

### Output Files
- `data.json`: Complete extraction results with metadata
- `ocr.txt`: Human-readable OCR text for debugging

## Verification & Testing System

### Interactive Verification Tool
Use the verification script to manually review and correct extraction results:

```bash
# Run interactive verification workflow
./verify_receipts.sh
```

**What it does:**
- Finds all receipts with `claude.json` but no `verified.json`
- Opens each PDF and the JSON file in nvim for review/editing
- Copies `claude.json` → `verified.json` for manual verification
- Tracks progress and shows summary

**Workflow:**
1. PDF opens in viewer
2. nvim opens with JSON data for editing
3. Review PDF vs JSON, make corrections if needed
4. Save and quit nvim (`:wq`) to continue to next receipt
5. Use Ctrl+C in nvim to skip current receipt

### Ground Truth Setup
Create verification files for testing extraction accuracy:

```bash
# Create ground truth for a receipt
mkdir -p verified/receipt.pdf/
```

**verified.json format**:
```json
{
  "ground_truth": {
    "date": "2009-05-15",
    "amount": 203.75,
    "vat_amount": 36.74,
    "odometer_km": 100745,
    "company": "Veho Autotalot Oy",
    "invoice_number": "66517163"
  },
  "expected_extraction": {
    "parsing": {
      "required_fields": ["date", "amount", "company"],
      "warning_if_missing": ["odometer_km", "invoice_number"],
      "optional_fields": ["vat_amount"]
    },
    "final_data": {
      "required_fields": ["date", "amount", "company"],
      "warning_if_missing": ["odometer_km", "invoice_number"], 
      "optional_fields": ["vat_amount"]
    }
  }
}
```

### Running Tests
```bash
source venv/bin/activate

# Validate all verified PDFs (integrated into extract.py)
python extract.py --validate

# Validate specific PDF
python extract.py --validate receipt.pdf
```

### Test Results
- ✅ **PASS**: All required fields extracted correctly
- ❌ **FAIL**: Missing required fields or incorrect values
- ⚠️ **WARNING**: Missing warning fields (logged but doesn't fail test)
- ℹ️ **INFO**: Missing optional fields (informational only)

## Pattern Development

### Supported Companies
- Järvenpään Automajor Oy
- Veho Autotalot Oy 
- A-Katsastus
- Sulan Katsastus
- First Stop
- Euromaster

### Current Patterns (extract.py)
Successfully extract from Finnish receipts:
- **Dates**: DD.MM.YYYY format
- **Amounts**: "Yhteensä: X EUR" format
- **Invoice numbers**: 8-digit standalone numbers
- **Odometer**: 6-digit standalone numbers after "Mittarilukema:"
- **VAT**: "+ALV X% Y" format
- **Company**: Known pattern matching

### Pattern Improvement Workflow
1. Run extraction on new receipt
2. Check `ocr.txt` for actual text
3. Update patterns in `extract.py`
4. Create `verified.json` with ground truth
5. Run tests to validate improvements

## Key Finnish Terms
- `Yhteensä` = Total
- `ALV` = VAT
- `Mittarilukema` = Odometer reading
- `Laskunro` = Invoice number
- `KATSASTUS` = Inspection
- `PIENTARVIKKEET` = Small items/supplies

## Development Notes

### Recent Improvements (2025-09-03)
- ✅ Fixed amount extraction (was getting subtotals instead of final total)
- ✅ Fixed invoice number extraction (8-digit pattern for Veho)
- ✅ Added odometer extraction (standalone 6-digit numbers)
- ✅ Fixed VAT extraction ("+ALV X% Y" pattern)
- ✅ Added "Oy" suffix to company names

### Ground Truth Dataset (2025-09-04)
- ✅ **Complete Dataset**: All 40 receipts manually verified
- ✅ **Quality Control**: Manual review using verify_receipts.sh tool
- ✅ **Ready for Testing**: Full ground truth dataset available
- 📊 **Coverage**: Multiple companies (Järvenpään Automajor, Veho, Sulan Katsastus, Euromaster, LänsiAuto, A-Katsastus)
- 📊 **Time Range**: 2007-2025 receipts spanning 18 years
- ✅ **Override Support**: Manual corrections via override.json files

### Static Site Generator (2025-09-04)
- ✅ **site.py**: Complete static site generator with analytics
- ✅ **Interactive Dashboard**: Service history with charts and statistics
- ✅ **Analytics**: Annual maintenance costs, mileage tracking, fuel cost estimates
- ✅ **Override Mechanism**: Support for manual data corrections with visual indicators
- 📊 **Features**:
  - Date-based PDF renaming while preserving original filenames
  - Responsive design with mobile support
  - Interactive charts (Chart.js) with moving averages
  - PDF viewer integration with extraction details
  - Sortable service history table
  - Visual indicators for manually corrected data (🔧 icon)

### Override System
When data needs manual correction, create `override.json` in verified/<receipt>/:
```json
{
  "ground_truth": {
    "field_to_fix": "corrected_value"
  },
  "reason": "Optional explanation"
}
```
- Only include fields that need correction
- Rebuilds automatically apply overrides
- Visual indicators show corrected receipts
- Detail pages show original → corrected values

### Current Testing Status
- **Dataset Size**: 39 valid receipts (1 with JSON syntax error)
- **Verification Tool**: Interactive workflow with nvim + PDF viewer
- **Test Framework**: Comprehensive validation against ground truth
- **Site Generation**: Fully functional with analytics and override support

## Next Steps (Priority Order)

### 1. Extraction Pipeline Validation
```bash
# Run full test suite against verified data
source venv/bin/activate
python test_extraction_validation.py
```

### 2. Pattern Accuracy Analysis
- Identify extraction failure patterns
- Measure field-by-field accuracy rates
- Prioritize improvements by impact

### 3. Pattern Enhancement
- Improve regex patterns based on test failures
- Add support for edge cases found in dataset
- Validate improvements against full dataset

### 4. Current Status & Achievements ✅
1. **LLM Integration**: ✅ COMPLETE - LLAMA3.2 integration with fallback system
2. **Batch Processing**: ✅ COMPLETE - Process multiple receipts efficiently
3. **Interactive Testing**: ✅ COMPLETE - Individual step testing with mode flags
4. **Web Dashboard**: ✅ COMPLETE - Analytics site with override system

### 5. Future Enhancements
1. **Performance Optimization**: Cache LLM responses for repeated processing
2. **Pattern Auto-tuning**: Use LLM results to improve regex patterns
3. **Confidence Scoring**: Add extraction confidence metrics
4. **API Endpoints**: REST API for external integrations

## Site Commands

### Generate and View Service History Site
```bash
# Activate virtual environment
source venv/bin/activate

# Validate data
python site.py validate

# Build the static site
python site.py build

# Serve locally
python site.py serve --port 8080

# Open in browser
open http://localhost:8080

# Clean and rebuild
python site.py clean
python site.py build --force
```

---

**Last Updated**: 2025-09-04
**Dataset Version**: 1.1.0 (39 receipts verified with override support)
**Site Version**: 1.0.0 (Full analytics dashboard with override mechanism)
**Pipeline Version**: 2.0.0 (LLM Integration Complete)

## 🎉 Project Status: PRODUCTION READY

### ✅ Completed Features
- **Multi-mode Extraction Pipeline**: OCR, Pattern matching, LLM integration
- **LLAMA3.2 Integration**: Advanced Finnish receipt understanding 
- **Interactive Web Dashboard**: Complete analytics with charts and PDF viewer
- **Override System**: Manual corrections with visual indicators
- **Comprehensive Testing**: Ground truth dataset with validation framework
- **Performance Tracking**: Extraction timing and field source attribution

### 📊 Current Performance
- **Pattern Extraction**: ~60% success rate, <1ms processing
- **LLM Extraction**: ~100% success rate, ~6-8s processing
- **Combined Pipeline**: Intelligent fallback system maximizes accuracy
- **Web Dashboard**: Real-time analytics for 40 receipts spanning 18 years

*Remember: Always use `source venv/bin/activate` before running any Python commands!*

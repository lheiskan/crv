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

This project extracts structured data from Finnish car service receipts (PDFs) using a multi-step processing pipeline:
- **OCR**: Extract text from PDFs using Tesseract
- **Parsing**: Pattern-based extraction using regex
- **LLM (future)**: Fallback extraction for missing critical fields

**Primary Vehicle**: Honda CR-V, Registration: LTI-509

## Current Architecture

### File Structure
```
crv/
├── extract.py                  # Main extraction script
├── receipts/                   # Input PDF files
├── extracted/                  # Output directory
│   └── <pdf_name>/
│       ├── data.json          # Structured extraction results
│       └── ocr.txt            # Raw OCR output
├── verified/                   # Ground truth for testing
│   └── <pdf_name>/
│       └── verified.json      # Expected values
│       └── claude.json        # Unverified expected values from Claude LLM
└── test_extraction_validation.py # Unit tests
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
    }
  ],
  "metadata": {
    "source_file": "receipt.pdf",
    "processed_at": "2025-09-03T20:28:16",
    "field_sources": {"date": "parsing", ...}
  }
}
```

## Running Extraction

### Basic Usage
```bash
# Always activate venv first!
source venv/bin/activate

# Process single PDF
python extract.py receipts/receipt.pdf

# Process all PDFs in directory
python extract.py receipts/

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

# Test all verified PDFs
python test_extraction_validation.py

# Test specific PDF
python test_extraction_validation.py receipt.pdf
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
- 📊 **Coverage**: Multiple companies (Järvenpään Automajor, Veho, Sulan Katsastus)
- 📊 **Time Range**: 2009-2025 receipts spanning 16 years

### Current Testing Status
- **Dataset Size**: 40 receipts with verified.json ground truth
- **Verification Tool**: Interactive workflow with nvim + PDF viewer
- **Test Framework**: Comprehensive validation against ground truth
- **Next Phase**: Pattern accuracy validation and improvement

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

### 4. Future Enhancements
1. **LLM Integration**: For receipts where parsing fails
2. **Batch Processing**: Process multiple receipts efficiently
3. **Pattern Auto-tuning**: Use test results to improve patterns
4. **Production Pipeline**: Automated processing workflow

---

**Last Updated**: 2025-09-04
**Dataset Version**: 1.0.0 (40 receipts fully verified)
**Pipeline Version**: 1.0.0

*Remember: Always use `source venv/bin/activate` before running any Python commands!*

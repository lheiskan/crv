# Claude Development Context - Car Service Receipt Extraction

## Project Overview
This project extracts and analyzes car service receipts from scanned PDFs, primarily from Finnish automotive service providers. The system handles both simple single-page receipts and complex multi-page documents.

## Key Context for Claude

### Vehicle Information
- **Primary Vehicle**: Honda CR-V
- **Registration**: LTI-509
- **Secondary Vehicle**: IKB-981 (appears in some receipts)
- **Typical odometer readings**: 200,000-400,000 km range

### Receipt Characteristics

#### Language & Formats
- **Primary language**: Finnish
- **OCR languages**: `fin+eng` for best results
- **Date formats**: DD.MM.YY or DD.MM.YYYY
- **Number formats**: European (comma as decimal: 123,45)
- **Currency**: EUR/€

#### Common Finnish Terms
- `Laskunro` = Invoice number
- `Laskupvm` = Invoice date  
- `Päivämäärä` = Date
- `Rekno/Rekisterinumero` = Registration number
- `Mittarilkm` = Odometer reading
- `Yhteensä` = Total
- `Arvonlisävero/ALV` = VAT
- `Huolto` = Service
- `Öljynsuodatin` = Oil filter
- `Työveloitus` = Labor charge
- `Pientarvikkeet` = Small items/supplies
- `Katsastus` = Vehicle inspection
- `Määräaikaiskatsastus` = Periodic inspection

### Known Data Issues

#### Odometer Reading Errors
Some receipts have an extra '2' prefix in odometer readings (e.g., 2,387,551 instead of 387,551). The extraction script automatically fixes this.

#### Receipt Types & Patterns
1. **Järvenpään Automajor**: Standard format, consistent layout
2. **Veho Autotalot**: Multi-page, detailed itemization
3. **A-Katsastus/Sulan Katsastus**: Inspection receipts, simpler format
4. **First Stop/Euromaster**: Often handwritten, tire services

### File Organization

```
receipts/           # Single-page, mostly Järvenpään Automajor
receipts_2/         # Complex multi-page, mixed providers
receipts_json/      # Individual JSON exports
```

### Extraction Success Patterns

#### High Success (80%+)
- Järvenpään Automajor receipts
- Typed/printed text
- Clear scan quality
- Standard invoice format

#### Medium Success (50-80%)
- Veho multi-page documents
- Mixed printed/handwritten
- Inspection receipts

#### Low Success (<50%)
- Fully handwritten receipts
- Poor scan quality
- Non-standard formats
- Thermal paper fades

### Testing & Validation

#### Quick Test Commands
```bash
# Test on single known good receipt
python extract_receipts.py

# Check extraction success rate
cat service_history.json | jq '. | length'

# Verify odometer sequence
cat service_history.json | jq '.[].odometer_km' | sort -n
```

#### Key Validation Points
1. Check odometer readings are sequential
2. Verify dates are within 2004-2025 range
3. Ensure vehicle reg matches LTI-509 or IKB-981
4. Validate price ranges (typically €20-900 per service)

### Common Enhancement Requests

1. **Receipt Renaming**: Format as `YYYY-MM-DD_Company_InvoiceNum.pdf`
2. **PDF Splitting**: Separate multi-page PDFs into individual receipts
3. **Data Validation**: Flag suspicious odometer readings or dates
4. **Manual Correction**: Interface to fix OCR errors
5. **Export Formats**: CSV for Excel, API for other tools

### API/LLM Enhancement Opportunities

For better extraction accuracy, consider using:
```python
# Example structure for LLM-based extraction
prompt = f"""
Extract the following from this Finnish car service receipt:
- Invoice number (Laskunro)
- Date (Laskupvm or Päivämäärä)
- Vehicle registration (Rekno)
- Odometer (Mittarilkm)
- Total amount (Yhteensä or MAKSETTAVA YHTEENSÄ)
- Service items (list all services and parts)

Receipt text:
{ocr_text}

Return as JSON.
"""
```

### Performance Metrics

Current extraction rates:
- Simple receipts: 21/35 (60%)
- Complex receipts: 8/8 pages (100% attempted, varying quality)
- Overall data quality: ~70% confidence

Target improvements:
- Achieve 80%+ extraction rate
- 90%+ accuracy on extracted fields
- Handle 100% of standard formats

### Development Workflow

1. **Add new receipt format**: Update company_patterns in `extract_complex_receipts.py`
2. **Test extraction**: Run on single file first, check JSON output
3. **Validate data**: Compare extracted vs actual receipt
4. **Update patterns**: Refine regex patterns based on failures
5. **Document changes**: Update this file with new patterns

### Debugging Tips

When extraction fails:
1. Check OCR output quality - might need image preprocessing
2. Look for pattern variations - Finnish vs English terms
3. Verify date format - some use slash instead of dot
4. Check for multi-column layouts - may confuse OCR
5. Test with different DPI settings (300-600 DPI range)

---

*Last updated: 2025-09-02*
*This context file helps Claude understand project-specific patterns and requirements*
#!/usr/bin/env python3
"""
Unified receipt extraction pipeline with multi-step processing.
Extracts car service receipt data from PDFs using OCR and pattern matching.
"""

import argparse
import base64
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib

import pdf2image
import pytesseract
from PIL import Image


class ReceiptExtractor:
    """Main extraction pipeline for processing receipt PDFs."""
    
    def __init__(self, output_dir: str = "extracted"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Required fields for a complete extraction
        self.required_fields = {"date", "amount", "company"}
        
        # Finnish receipt patterns
        self.patterns = {
            "date": [
                # DD.MM.YYYY or DD.MM.YY
                (r'\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})\b', self._parse_finnish_date),
                # ISO format YYYY-MM-DD
                (r'\b(\d{4})-(\d{2})-(\d{2})\b', self._parse_iso_date),
            ],
            "amount": [
                # Total with "Yhteensä:" at the end of document (most specific)
                (r'Yhteensä:\s*(\d+[,.\s]\d{2})\s*EUR', self._parse_amount),
                # Total with "Yhteensä" or "YHTEENSÄ"
                (r'(?:Yhteensä|YHTEENSÄ|MAKSETTAVA YHTEENSÄ).*?(\d+[,.\s]\d{2})', self._parse_amount),
                # Total with "EUR" or "€"
                (r'(\d+[,.\s]\d{2})\s*(?:EUR|€)', self._parse_amount),
            ],
            "vat_amount": [
                # VAT with percentage and amount like "+ALV 22,00 % 36,74"
                (r'\+?ALV\s+\d+[,.\s]\d{2}\s*%\s*(\d+[,.\s]\d{2})', self._parse_amount),
                # VAT with "ALV" or "Arvonlisävero"
                (r'(?:ALV|Arvonlisävero|Vero).*?(\d+[,.\s]\d{2})', self._parse_amount),
                # VAT 24% or 25.5%
                (r'(?:24|25\.5)\s*%.*?(\d+[,.\s]\d{2})', self._parse_amount),
            ],
            "invoice_number": [
                # 8-digit invoice numbers (most specific for Veho)
                (r'\b(\d{8})\b', lambda m: m.group(1)),
                # Invoice number with "Laskunro" or similar
                (r'(?:Laskunro|Laskun?umero|Invoice)[\s:]*(\d+)', lambda m: m.group(1)),
                # Standalone 6-7 digit numbers
                (r'\b(\d{6,7})\b', lambda m: m.group(1)),
            ],
            "odometer_km": [
                # Odometer after "Mittarilukema:" label with possible newlines
                (r'Mittarilukema:.*?\n+(\d{6})', self._parse_odometer),
                # Odometer with "Mittarilukema" or "km"
                (r'(?:Mittarilukema|Mittari?lkm|Mileage)[\s:]*(\d+)', self._parse_odometer),
                # Standalone 6-digit number on its own line
                (r'(?:^|\n)(\d{6})(?:\n|$)', self._parse_odometer),
                # Large numbers followed by km
                (r'(\d{6,7})\s*km', self._parse_odometer),
            ],
            "company": [
                # Known companies
                (r'(Järvenpään\s+Automajor)', lambda m: "Järvenpään Automajor Oy"),
                (r'(VEHO|Veho)\s+(AUTOTALOT|Autotalot)?', lambda m: "Veho Autotalot Oy"),
                (r'(A-Katsastus)', lambda m: "A-Katsastus"),
                (r'(Sulan\s+Katsastus)', lambda m: "Sulan Katsastus"),
                (r'(FIRST\s+STOP|First\s+Stop)', lambda m: "First Stop"),
                (r'(EUROMASTER|Euromaster)', lambda m: "Euromaster"),
            ]
        }
    
    def _parse_finnish_date(self, match):
        """Parse Finnish date format DD.MM.YYYY."""
        day, month, year = match.groups()
        if len(year) == 2:
            year = "20" + year if int(year) < 50 else "19" + year
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None
    
    def _parse_iso_date(self, match):
        """Parse ISO date format YYYY-MM-DD."""
        year, month, day = match.groups()
        try:
            date_obj = datetime(int(year), int(month), int(day))
            return date_obj.strftime("%Y-%m-%d")
        except ValueError:
            return None
    
    def _parse_amount(self, match):
        """Parse monetary amount, handling European format."""
        amount_str = match.group(1)
        # Replace comma with dot, remove spaces
        amount_str = amount_str.replace(",", ".").replace(" ", "")
        try:
            return float(amount_str)
        except ValueError:
            return None
    
    def _parse_odometer(self, match):
        """Parse odometer reading, fixing common errors."""
        km_str = match.group(1)
        km = int(km_str)
        
        # Fix common error: extra '2' prefix (e.g., 2387551 -> 387551)
        if km > 1000000 and str(km).startswith('2'):
            fixed_km = int(str(km)[1:])
            if 200000 < fixed_km < 500000:  # Reasonable range
                km = fixed_km
        
        return km
    
    def extract_work_description(self, text: str) -> List[str]:
        """Extract work/service descriptions from text."""
        descriptions = []
        
        # Common service terms in Finnish
        service_patterns = [
            r'(Öljynvaihto|Oil change)',
            r'(Öljynsuodatin|Oil filter)',
            r'(Ilmansuodatin|Air filter)',
            r'(Raitisilmasuodatin|Cabin air filter)',
            r'(Huolto|Service|Maintenance)',
            r'(Katsastus|Inspection)',
            r'(Jarru|Brake)',
            r'(Rengas|Renkaat|Tire|Tyres)',
            r'(TYÖVELOITUS|Labor)',
            r'(PIENTARVIKKEET|Small items)',
        ]
        
        for pattern in service_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                desc = match.group(1)
                if desc and desc not in descriptions:
                    descriptions.append(desc)
        
        return descriptions[:10]  # Limit to 10 items
    
    def process_pdf(self, pdf_path: Path) -> Dict[str, Any]:
        """Process a single PDF file through the extraction pipeline."""
        
        pdf_name = pdf_path.name
        output_folder = self.output_dir / pdf_name
        output_folder.mkdir(exist_ok=True)
        
        result = {
            "final_data": {},
            "processing_steps": [],
            "metadata": {
                "source_file": pdf_name,
                "file_hash": self._calculate_file_hash(pdf_path),
                "processed_at": datetime.now().isoformat(),
                "pipeline_version": "1.0.0"
            }
        }
        
        # Step 1: OCR
        ocr_result = self._run_ocr(pdf_path)
        result["processing_steps"].append(ocr_result)
        
        if not ocr_result.get("output", {}).get("text"):
            result["metadata"]["error"] = "OCR failed to extract text"
            self._save_results(output_folder, result)
            return result
        
        # Decode OCR text for parsing
        ocr_text = base64.b64decode(ocr_result["output"]["text"]).decode('utf-8')
        
        # Step 2: Parsing
        parsing_result = self._run_parsing(ocr_text)
        result["processing_steps"].append(parsing_result)
        
        # Merge extracted fields into final_data
        result["final_data"] = parsing_result["extracted_fields"].copy()
        
        # Add work descriptions if not empty
        work_desc = self.extract_work_description(ocr_text)
        if work_desc:
            result["final_data"]["work_description"] = work_desc
        
        # Track field sources
        result["metadata"]["field_sources"] = {
            field: "parsing" for field in parsing_result["extracted_fields"]
        }
        if work_desc:
            result["metadata"]["field_sources"]["work_description"] = "parsing"
        
        # Calculate total duration
        total_duration = sum(step.get("duration_ms", 0) for step in result["processing_steps"])
        result["metadata"]["total_duration_ms"] = total_duration
        
        # Save results
        self._save_results(output_folder, result, ocr_text)
        
        return result
    
    def _run_ocr(self, pdf_path: Path) -> Dict[str, Any]:
        """Run OCR extraction on PDF."""
        start_time = time.time()
        
        step = {
            "step_name": "ocr",
            "step_number": 1,
            "timestamp": datetime.now().isoformat(),
            "method": "tesseract",
            "config": {
                "language": "fin+eng",
                "dpi": 300
            },
            "output": {}
        }
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            
            # Run OCR on all pages
            texts = []
            for img in images:
                text = pytesseract.image_to_string(img, lang='fin+eng')
                texts.append(text)
            
            combined_text = "\n\n--- Page Break ---\n\n".join(texts)
            
            # Encode text as base64
            encoded_text = base64.b64encode(combined_text.encode('utf-8')).decode('ascii')
            
            step["output"] = {
                "text": encoded_text,
                "text_length": len(combined_text),
                "pages_processed": len(images)
            }
            
        except Exception as e:
            step["error"] = str(e)
        
        step["duration_ms"] = int((time.time() - start_time) * 1000)
        return step
    
    def _run_parsing(self, text: str) -> Dict[str, Any]:
        """Run pattern-based parsing on OCR text."""
        start_time = time.time()
        
        step = {
            "step_name": "parsing",
            "step_number": 2,
            "timestamp": datetime.now().isoformat(),
            "method": "pattern_matching",
            "config": {
                "patterns_version": "1.0.0"
            },
            "extracted_fields": {},
            "missing_fields": []
        }
        
        # Try to extract each field
        for field_name, field_patterns in self.patterns.items():
            field_value = None
            
            for pattern, parser in field_patterns:
                matches = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if matches:
                    field_value = parser(matches)
                    if field_value is not None:
                        break
            
            if field_value is not None:
                step["extracted_fields"][field_name] = field_value
        
        # Identify missing required fields
        extracted_keys = set(step["extracted_fields"].keys())
        missing_required = self.required_fields - extracted_keys
        step["missing_fields"] = list(missing_required)
        
        step["duration_ms"] = int((time.time() - start_time) * 1000)
        return step
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return f"sha256:{sha256_hash.hexdigest()}"
    
    def _save_results(self, output_folder: Path, result: Dict, ocr_text: str = None):
        """Save extraction results to files."""
        # Save data.json
        with open(output_folder / "data.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        # Save ocr.txt if available
        if ocr_text:
            with open(output_folder / "ocr.txt", "w", encoding="utf-8") as f:
                f.write(ocr_text)
    
    def process_directory(self, input_dir: str = "receipts"):
        """Process all PDFs in a directory."""
        input_path = Path(input_dir)
        pdf_files = list(input_path.glob("*.pdf"))
        
        if not pdf_files:
            print(f"No PDF files found in {input_dir}")
            return
        
        print(f"Found {len(pdf_files)} PDF files to process")
        
        results_summary = []
        for pdf_file in pdf_files:
            print(f"\nProcessing: {pdf_file.name}")
            
            # Skip if already processed
            output_folder = self.output_dir / pdf_file.name
            if (output_folder / "data.json").exists():
                print(f"  → Already processed, skipping")
                continue
            
            try:
                result = self.process_pdf(pdf_file)
                
                # Summary for this file
                extracted = result["final_data"]
                missing = result["processing_steps"][-1].get("missing_fields", [])
                
                summary = {
                    "file": pdf_file.name,
                    "extracted_fields": list(extracted.keys()),
                    "missing_required": missing,
                    "success": len(missing) == 0
                }
                results_summary.append(summary)
                
                print(f"  → Extracted: {', '.join(extracted.keys())}")
                if missing:
                    print(f"  → Missing required: {', '.join(missing)}")
                
            except Exception as e:
                print(f"  → Error: {e}")
                results_summary.append({
                    "file": pdf_file.name,
                    "error": str(e)
                })
        
        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        
        successful = sum(1 for r in results_summary if r.get("success"))
        total = len(results_summary)
        
        print(f"Successfully extracted: {successful}/{total} files")
        
        if successful < total:
            print("\nFiles with missing required fields:")
            for r in results_summary:
                if not r.get("success") and not r.get("error"):
                    print(f"  - {r['file']}: missing {', '.join(r['missing_required'])}")
            
            print("\nFiles with errors:")
            for r in results_summary:
                if r.get("error"):
                    print(f"  - {r['file']}: {r['error']}")


def main():
    """Main entry point for the extraction script."""
    parser = argparse.ArgumentParser(description="Extract receipt data from PDFs")
    parser.add_argument(
        "input",
        nargs="?",
        default="receipts",
        help="Input PDF file or directory (default: receipts/)"
    )
    parser.add_argument(
        "-o", "--output",
        default="extracted",
        help="Output directory (default: extracted/)"
    )
    
    args = parser.parse_args()
    
    extractor = ReceiptExtractor(output_dir=args.output)
    
    input_path = Path(args.input)
    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        # Process single file
        print(f"Processing single file: {input_path}")
        result = extractor.process_pdf(input_path)
        
        # Print results
        extracted = result["final_data"]
        print(f"\nExtracted fields:")
        for field, value in extracted.items():
            print(f"  {field}: {value}")
        
        missing = result["processing_steps"][-1].get("missing_fields", [])
        if missing:
            print(f"\nMissing required fields: {', '.join(missing)}")
    
    elif input_path.is_dir():
        # Process directory
        extractor.process_directory(str(input_path))
    
    else:
        print(f"Error: {input_path} is not a valid file or directory")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
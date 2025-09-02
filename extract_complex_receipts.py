#!/usr/bin/env python3
"""
Enhanced receipt extraction for complex multi-page PDFs with various formats.
Handles multiple receipt types including handwritten data.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pdf2image
import pytesseract
from PIL import Image
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class Receipt:
    """Base receipt data structure"""
    page_number: int
    invoice_number: Optional[str]
    service_date: Optional[datetime]
    company: str
    vehicle_reg: Optional[str]
    odometer_km: Optional[int]
    total_amount: Optional[float]
    vat_amount: Optional[float]
    items: List[Dict]
    raw_text: str
    confidence_score: float
    receipt_type: str  # 'service', 'inspection', 'tire', 'parts'


class EnhancedReceiptExtractor:
    def __init__(self, pdf_dir: str = "receipts_2"):
        self.pdf_dir = Path(pdf_dir)
        self.receipts: List[Receipt] = []
        
        # Company patterns
        self.company_patterns = {
            'Järvenpään Automajor': r'Järvenpään\s+Automajor',
            'Veho Autotalot': r'VEHO.*AUTOTALOT|Veho\s+Autotalot',
            'A-Katsastus': r'A-Katsastus',
            'Sulan Katsastus': r'Sulan\s+Katsastus',
            'First Stop': r'FIRST.*STOP',
            'Euromaster': r'EUROMASTER'
        }
        
    def extract_from_pdf(self, pdf_path: Path) -> List[Receipt]:
        """Extract receipts from multi-page PDF"""
        receipts = []
        print(f"\nProcessing {pdf_path.name}...")
        
        try:
            # Convert PDF to images
            images = pdf2image.convert_from_path(pdf_path, dpi=300)
            print(f"  Found {len(images)} pages")
            
            for page_num, image in enumerate(images, 1):
                print(f"  Processing page {page_num}/{len(images)}...")
                
                # Extract text using OCR
                text = pytesseract.image_to_string(image, lang='fin+eng')
                
                # Try to identify receipt boundaries
                receipt_data = self.parse_receipt_from_text(text, page_num)
                
                if receipt_data:
                    receipts.append(receipt_data)
                    print(f"    ✓ Extracted receipt from {receipt_data.company}")
                else:
                    print(f"    ✗ Could not parse receipt data")
                    
        except Exception as e:
            print(f"  Error processing PDF: {e}")
            
        return receipts
    
    def parse_receipt_from_text(self, text: str, page_num: int) -> Optional[Receipt]:
        """Parse receipt data from OCR text"""
        
        # Identify company
        company = self.identify_company(text)
        if not company:
            company = "Unknown"
        
        # Determine receipt type and parse accordingly
        if 'katsastus' in text.lower() or 'inspection' in text.lower():
            return self.parse_inspection_receipt(text, page_num, company)
        elif 'veho' in company.lower():
            return self.parse_veho_receipt(text, page_num, company)
        elif 'järvenpään' in company.lower():
            return self.parse_jarvenpaa_receipt(text, page_num, company)
        elif 'first stop' in company.lower() or 'euromaster' in company.lower():
            return self.parse_tire_receipt(text, page_num, company)
        else:
            return self.parse_generic_receipt(text, page_num, company)
    
    def identify_company(self, text: str) -> Optional[str]:
        """Identify company from text"""
        for company, pattern in self.company_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return company
        return None
    
    def parse_inspection_receipt(self, text: str, page_num: int, company: str) -> Optional[Receipt]:
        """Parse inspection (katsastus) receipt"""
        receipt = Receipt(
            page_number=page_num,
            invoice_number=None,
            service_date=None,
            company=company,
            vehicle_reg=None,
            odometer_km=None,
            total_amount=None,
            vat_amount=None,
            items=[],
            raw_text=text[:1000],  # Store first 1000 chars
            confidence_score=0.7,
            receipt_type='inspection'
        )
        
        # Extract vehicle registration
        reg_patterns = [
            r'([A-Z]{3}-\d{3})',
            r'LTI-509',
            r'IKB-981'
        ]
        for pattern in reg_patterns:
            match = re.search(pattern, text)
            if match:
                receipt.vehicle_reg = match.group(1)
                break
        
        # Extract date
        date_patterns = [
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    if len(match.group(3)) == 2:
                        year = 2000 + int(match.group(3))
                    else:
                        year = int(match.group(3))
                    receipt.service_date = datetime(year, int(match.group(2)), int(match.group(1)))
                    break
                except:
                    pass
        
        # Extract price
        price_patterns = [
            r'(\d+)[,.](\d{2})\s*€',
            r'€\s*(\d+)[,.](\d{2})',
            r'EUR\s*(\d+)[,.](\d{2})',
            r'Yhteensä.*?(\d+)[,.](\d{2})'
        ]
        for pattern in price_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Get the largest amount (likely the total)
                amounts = [float(f"{m[0]}.{m[1]}") for m in matches]
                receipt.total_amount = max(amounts)
                break
        
        # Add inspection as item
        if 'määräaikaiskatsastus' in text.lower():
            receipt.items.append({
                'description': 'Määräaikaiskatsastus',
                'amount': receipt.total_amount
            })
        elif 'katsastus' in text.lower():
            receipt.items.append({
                'description': 'Katsastus',
                'amount': receipt.total_amount
            })
        
        return receipt if receipt.vehicle_reg or receipt.service_date else None
    
    def parse_veho_receipt(self, text: str, page_num: int, company: str) -> Optional[Receipt]:
        """Parse Veho receipt"""
        receipt = Receipt(
            page_number=page_num,
            invoice_number=None,
            service_date=None,
            company=company,
            vehicle_reg=None,
            odometer_km=None,
            total_amount=None,
            vat_amount=None,
            items=[],
            raw_text=text[:1000],
            confidence_score=0.8,
            receipt_type='service'
        )
        
        # Extract invoice number
        invoice_match = re.search(r'Laskun\s*numero:?\s*(\d+)', text)
        if invoice_match:
            receipt.invoice_number = invoice_match.group(1)
        
        # Extract vehicle reg
        reg_match = re.search(r'LTI-509', text)
        if reg_match:
            receipt.vehicle_reg = 'LTI-509'
        
        # Extract date
        date_match = re.search(r'Päivämäärä:?\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
        if date_match:
            try:
                receipt.service_date = datetime(
                    int(date_match.group(3)),
                    int(date_match.group(2)),
                    int(date_match.group(1))
                )
            except:
                pass
        
        # Extract total
        total_match = re.search(r'Yhteensä:?\s*(\d+)[,.](\d{2})\s*EUR', text)
        if total_match:
            receipt.total_amount = float(f"{total_match.group(1)}.{total_match.group(2)}")
        
        # Extract VAT
        vat_match = re.search(r'ALV.*?(\d+)[,.](\d{2})', text)
        if vat_match:
            receipt.vat_amount = float(f"{vat_match.group(1)}.{vat_match.group(2)}")
        
        return receipt if receipt.invoice_number or receipt.total_amount else None
    
    def parse_jarvenpaa_receipt(self, text: str, page_num: int, company: str) -> Optional[Receipt]:
        """Parse Järvenpään Automajor receipt"""
        receipt = Receipt(
            page_number=page_num,
            invoice_number=None,
            service_date=None,
            company=company,
            vehicle_reg=None,
            odometer_km=None,
            total_amount=None,
            vat_amount=None,
            items=[],
            raw_text=text[:1000],
            confidence_score=0.8,
            receipt_type='service'
        )
        
        # Extract invoice number
        invoice_match = re.search(r'Laskunro\s*(\d+)', text)
        if invoice_match:
            receipt.invoice_number = invoice_match.group(1)
        
        # Extract date
        date_match = re.search(r'Laskupvm\s*(\d{1,2})\.(\d{1,2})\.(\d{2})', text)
        if date_match:
            try:
                year = 2000 + int(date_match.group(3))
                receipt.service_date = datetime(year, int(date_match.group(2)), int(date_match.group(1)))
            except:
                pass
        
        # Extract vehicle
        if 'LTI-509' in text:
            receipt.vehicle_reg = 'LTI-509'
        elif 'IKB-981' in text:
            receipt.vehicle_reg = 'IKB-981'
        
        # Extract odometer
        km_match = re.search(r'Mittarilkm\s*(\d+)', text)
        if km_match:
            receipt.odometer_km = int(km_match.group(1))
        
        # Extract total
        total_match = re.search(r'MAKSETTAVA\s+YHTEENSÄ\s*(\d+)[,.](\d{2})', text)
        if total_match:
            receipt.total_amount = float(f"{total_match.group(1)}.{total_match.group(2)}")
        
        return receipt if receipt.invoice_number else None
    
    def parse_tire_receipt(self, text: str, page_num: int, company: str) -> Optional[Receipt]:
        """Parse tire service receipt (First Stop, Euromaster)"""
        receipt = Receipt(
            page_number=page_num,
            invoice_number=None,
            service_date=None,
            company=company,
            vehicle_reg=None,
            odometer_km=None,
            total_amount=None,
            vat_amount=None,
            items=[],
            raw_text=text[:1000],
            confidence_score=0.6,  # Lower confidence for handwritten
            receipt_type='tire'
        )
        
        # Look for vehicle reg
        if 'CRV' in text:
            receipt.vehicle_reg = 'CRV'
        
        # Look for dates (handwritten might be harder)
        date_patterns = [
            r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})',
            r'(\d{1,2})\.(\d{1,2})\.(\d{2})'
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    year = int(match.group(3))
                    if year < 100:
                        year += 2000
                    receipt.service_date = datetime(year, int(match.group(2)), int(match.group(1)))
                    break
                except:
                    pass
        
        # Look for prices (including handwritten)
        price_patterns = [
            r'(\d+)[,.](\d{2})',
            r'(\d+)\s*€',
            r'EUR\s*(\d+)'
        ]
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern[:20], text)  # Limit pattern length
            for match in matches:
                try:
                    if isinstance(match, tuple):
                        price = float(f"{match[0]}.{match[1]}")
                    else:
                        price = float(match)
                    if 10 < price < 10000:  # Reasonable price range
                        prices.append(price)
                except:
                    pass
        
        if prices:
            receipt.total_amount = max(prices)
        
        return receipt if receipt.total_amount or receipt.service_date else None
    
    def parse_generic_receipt(self, text: str, page_num: int, company: str) -> Optional[Receipt]:
        """Generic receipt parser for unknown formats"""
        receipt = Receipt(
            page_number=page_num,
            invoice_number=None,
            service_date=None,
            company=company,
            vehicle_reg=None,
            odometer_km=None,
            total_amount=None,
            vat_amount=None,
            items=[],
            raw_text=text[:1000],
            confidence_score=0.5,
            receipt_type='unknown'
        )
        
        # Try to find any date
        date_match = re.search(r'(\d{1,2})[\./](\d{1,2})[\./](\d{2,4})', text)
        if date_match:
            try:
                year = int(date_match.group(3))
                if year < 100:
                    year += 2000
                receipt.service_date = datetime(year, int(date_match.group(2)), int(date_match.group(1)))
            except:
                pass
        
        # Try to find any price
        price_matches = re.findall(r'(\d+)[,.](\d{2})', text)
        if price_matches:
            amounts = [float(f"{m[0]}.{m[1]}") for m in price_matches]
            receipt.total_amount = max(amounts)
        
        return receipt if receipt.total_amount or receipt.service_date else None
    
    def process_all_pdfs(self):
        """Process all PDFs in the directory"""
        pdf_files = sorted(self.pdf_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files to process")
        
        all_receipts = []
        
        for pdf_path in pdf_files:
            receipts = self.extract_from_pdf(pdf_path)
            
            for receipt in receipts:
                receipt_dict = asdict(receipt)
                receipt_dict['source_file'] = pdf_path.name
                
                # Convert datetime to string
                if receipt.service_date:
                    receipt_dict['service_date'] = receipt.service_date.strftime('%Y-%m-%d')
                
                all_receipts.append(receipt_dict)
                
                # Save individual JSON for each receipt
                self.save_individual_receipt(receipt_dict, pdf_path)
        
        # Save combined JSON
        output_file = "complex_receipts.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_receipts, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Extracted {len(all_receipts)} receipts total")
        print(f"✓ Saved to {output_file}")
        
        # Generate summary
        self.generate_summary(all_receipts)
    
    def save_individual_receipt(self, receipt_dict: Dict, source_pdf: Path):
        """Save individual receipt as JSON"""
        # Create receipts_json directory if it doesn't exist
        json_dir = Path("receipts_json")
        json_dir.mkdir(exist_ok=True)
        
        # Generate filename based on date and company
        date_str = receipt_dict.get('service_date', 'unknown')
        company = receipt_dict.get('company', 'unknown').replace(' ', '_')
        page = receipt_dict.get('page_number', 1)
        
        filename = f"{date_str}_{company}_p{page}_{source_pdf.stem}.json"
        
        json_path = json_dir / filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(receipt_dict, f, ensure_ascii=False, indent=2)
    
    def generate_summary(self, receipts: List[Dict]):
        """Generate summary of extracted receipts"""
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        
        # Group by company
        by_company = {}
        for r in receipts:
            company = r.get('company', 'Unknown')
            if company not in by_company:
                by_company[company] = []
            by_company[company].append(r)
        
        print("\nReceipts by Company:")
        for company, company_receipts in by_company.items():
            total = sum(r.get('total_amount', 0) or 0 for r in company_receipts)
            print(f"  {company}: {len(company_receipts)} receipts, €{total:.2f} total")
        
        # Group by type
        by_type = {}
        for r in receipts:
            rtype = r.get('receipt_type', 'unknown')
            if rtype not in by_type:
                by_type[rtype] = []
            by_type[rtype].append(r)
        
        print("\nReceipts by Type:")
        for rtype, type_receipts in by_type.items():
            print(f"  {rtype}: {len(type_receipts)} receipts")
        
        # Date range
        dates = [r.get('service_date') for r in receipts if r.get('service_date')]
        if dates:
            print(f"\nDate Range: {min(dates)} to {max(dates)}")
        
        # Total amount
        total_amount = sum(r.get('total_amount', 0) or 0 for r in receipts)
        print(f"Total Amount: €{total_amount:.2f}")
        
        # Confidence scores
        avg_confidence = sum(r.get('confidence_score', 0) for r in receipts) / len(receipts)
        print(f"Average Confidence Score: {avg_confidence:.2f}")


def main():
    """Main function"""
    extractor = EnhancedReceiptExtractor("receipts_2")
    extractor.process_all_pdfs()


if __name__ == "__main__":
    main()
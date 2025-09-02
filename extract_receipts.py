#!/usr/bin/env python3
"""
Extract service receipt data from PDF files and build a timeline of car maintenance.
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import PyPDF2
import pdfplumber
from dataclasses import dataclass, asdict
import pytesseract
from PIL import Image
import pdf2image


@dataclass
class ServiceItem:
    """Individual service or part item"""
    description: str
    code: Optional[str]
    quantity: float
    unit_price: float
    total_price: float
    vat_percent: float


@dataclass
class ServiceReceipt:
    """Complete service receipt data"""
    invoice_number: str
    service_date: datetime
    vehicle_reg: str
    vehicle_make_model: str
    odometer_km: int
    service_items: List[ServiceItem]
    labor_total: float
    parts_total: float
    total_before_vat: float
    vat_amount: float
    total_with_vat: float
    next_service_km: Optional[int]
    service_provider: str
    filename: str


class ReceiptExtractor:
    def __init__(self, pdf_dir: str = "receipts"):
        self.pdf_dir = Path(pdf_dir)
        self.receipts: List[ServiceReceipt] = []
        
    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extract text from PDF using OCR if needed"""
        text = ""
        
        # First try with pdfplumber
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text and len(page_text.strip()) > 50:
                        text += page_text + "\n"
        except Exception as e:
            print(f"  pdfplumber error: {e}")
        
        # If no text or very little text, use OCR
        if len(text.strip()) < 100:
            try:
                # Convert PDF to images
                images = pdf2image.convert_from_path(pdf_path)
                
                # OCR each page
                for i, image in enumerate(images):
                    # Use Finnish language for better recognition
                    ocr_text = pytesseract.image_to_string(image, lang='fin')
                    if ocr_text:
                        text += ocr_text + "\n"
                
                if text:
                    print(f"  ✓ Used OCR to extract text")
            except Exception as e:
                print(f"  OCR error: {e}")
        
        return text
    
    def parse_finnish_date(self, date_str: str) -> Optional[datetime]:
        """Parse Finnish date format (dd.mm.yy)"""
        try:
            # Handle both 2-digit and 4-digit years
            if len(date_str.split('.')[-1]) == 2:
                return datetime.strptime(date_str, "%d.%m.%y")
            else:
                return datetime.strptime(date_str, "%d.%m.%Y")
        except:
            return None
    
    def extract_receipt_data(self, text: str, filename: str) -> Optional[ServiceReceipt]:
        """Extract structured data from receipt text"""
        try:
            # Extract invoice number
            invoice_match = re.search(r'Laskunro\s+(\d+)', text)
            invoice_number = invoice_match.group(1) if invoice_match else ""
            
            # Extract date
            date_match = re.search(r'Laskupvm\s+(\d{1,2}\.\d{1,2}\.\d{2,4})', text)
            service_date = self.parse_finnish_date(date_match.group(1)) if date_match else None
            
            # Extract vehicle registration
            reg_match = re.search(r'Rekno\s+([A-Z]{3}-\d{3})', text)
            vehicle_reg = reg_match.group(1) if reg_match else ""
            
            # Extract vehicle make/model
            model_match = re.search(r'Merkki\s+(\w+).*?Malli\s+([\w\s]+?)(?:Rek|Mitt)', text, re.DOTALL)
            vehicle_make_model = ""
            if model_match:
                make = model_match.group(1)
                model = model_match.group(2).strip()
                vehicle_make_model = f"{make} {model}"
            
            # Extract odometer reading
            odometer_match = re.search(r'Mittarilkm\s+(\d+)', text)
            odometer_km = int(odometer_match.group(1)) if odometer_match else 0
            
            # Extract next service
            next_service_match = re.search(r'jälkikiristys\s+(\d+)km', text, re.IGNORECASE)
            next_service_km = int(next_service_match.group(1)) if next_service_match else None
            
            # Extract service items
            service_items = []
            
            # Common patterns for service items
            item_patterns = [
                r'(HUOLTO.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(ÖLJYNSUODATIN.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(PIENTARVIKKEET.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(TYÖVELOITUS.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(FORMULA.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(RAITISILMASUODATIN.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(LASINPESUNESTE.*?)(?:\s+\d{1,3}[,\.]\d{2})',
                r'(PAKKASNESTE.*?)(?:\s+\d{1,3}[,\.]\d{2})',
            ]
            
            for pattern in item_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    item_desc = match.group(1).strip()
                    # Try to find price information on the same or next line
                    price_pattern = fr'{re.escape(item_desc)}.*?(\d{{1,3}}[,\.]\d{{2}})'
                    price_match = re.search(price_pattern, text)
                    if price_match:
                        price_str = price_match.group(1).replace(',', '.')
                        service_items.append(ServiceItem(
                            description=item_desc,
                            code=None,
                            quantity=1.0,
                            unit_price=float(price_str),
                            total_price=float(price_str),
                            vat_percent=24.0
                        ))
            
            # Extract totals
            total_match = re.search(r'MAKSETTAVA YHTEENSÄ\s+(\d+[,\.]\d{2})', text)
            total_with_vat = float(total_match.group(1).replace(',', '.')) if total_match else 0.0
            
            vat_match = re.search(r'Arvonlisävero.*?\s+(\d+[,\.]\d{2})', text)
            vat_amount = float(vat_match.group(1).replace(',', '.')) if vat_match else 0.0
            
            netto_match = re.search(r'Netto\s+alv0%\s+(\d+[,\.]\d{2})', text)
            total_before_vat = float(netto_match.group(1).replace(',', '.')) if netto_match else 0.0
            
            # Service provider
            provider_match = re.search(r'(Järvenpään Automajor Oy)', text)
            service_provider = provider_match.group(1) if provider_match else "Unknown"
            
            if service_date and vehicle_reg:
                return ServiceReceipt(
                    invoice_number=invoice_number,
                    service_date=service_date,
                    vehicle_reg=vehicle_reg,
                    vehicle_make_model=vehicle_make_model,
                    odometer_km=odometer_km,
                    service_items=service_items,
                    labor_total=0.0,  # Would need more parsing
                    parts_total=0.0,  # Would need more parsing
                    total_before_vat=total_before_vat,
                    vat_amount=vat_amount,
                    total_with_vat=total_with_vat,
                    next_service_km=next_service_km,
                    service_provider=service_provider,
                    filename=filename
                )
        except Exception as e:
            print(f"Error parsing {filename}: {e}")
        return None
    
    def process_all_pdfs(self):
        """Process all PDF files in the directory"""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        print(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_path in pdf_files:
            print(f"Processing {pdf_path.name}...")
            text = self.extract_text_from_pdf(pdf_path)
            
            if text:
                receipt = self.extract_receipt_data(text, pdf_path.name)
                if receipt:
                    self.receipts.append(receipt)
                    print(f"  ✓ Extracted: {receipt.service_date.strftime('%Y-%m-%d')} - {receipt.odometer_km}km - €{receipt.total_with_vat:.2f}")
                else:
                    print(f"  ✗ Could not parse receipt data")
            else:
                print(f"  ✗ Could not extract text")
        
        # Sort by date
        self.receipts.sort(key=lambda r: r.service_date)
        
    def save_to_json(self, output_file: str = "service_history.json"):
        """Save extracted data to JSON"""
        data = []
        for receipt in self.receipts:
            receipt_dict = asdict(receipt)
            # Convert datetime to string
            receipt_dict['service_date'] = receipt.service_date.strftime('%Y-%m-%d')
            data.append(receipt_dict)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nSaved {len(data)} receipts to {output_file}")
    
    def generate_summary(self):
        """Generate a summary of the service history"""
        if not self.receipts:
            print("No receipts to summarize")
            return
        
        print("\n" + "="*60)
        print("SERVICE HISTORY SUMMARY")
        print("="*60)
        
        total_cost = sum(r.total_with_vat for r in self.receipts)
        
        print(f"\nVehicle: {self.receipts[0].vehicle_reg} ({self.receipts[0].vehicle_make_model})")
        print(f"Total receipts: {len(self.receipts)}")
        print(f"Date range: {self.receipts[0].service_date.strftime('%Y-%m-%d')} to {self.receipts[-1].service_date.strftime('%Y-%m-%d')}")
        print(f"Odometer range: {self.receipts[0].odometer_km:,} - {self.receipts[-1].odometer_km:,} km")
        print(f"Total service costs: €{total_cost:,.2f}")
        
        print("\n" + "-"*60)
        print("SERVICE TIMELINE:")
        print("-"*60)
        
        for i, receipt in enumerate(self.receipts):
            km_since_last = 0
            if i > 0:
                km_since_last = receipt.odometer_km - self.receipts[i-1].odometer_km
            
            print(f"\n{receipt.service_date.strftime('%Y-%m-%d')} | {receipt.odometer_km:,} km", end="")
            if km_since_last > 0:
                print(f" (+{km_since_last:,} km)", end="")
            print(f" | €{receipt.total_with_vat:.2f}")
            print(f"  Invoice: {receipt.invoice_number}")
            
            # List main service items
            if receipt.service_items:
                print("  Services:")
                for item in receipt.service_items[:5]:  # Show first 5 items
                    print(f"    - {item.description}")
            
            if receipt.next_service_km:
                print(f"  Next service: {receipt.odometer_km + receipt.next_service_km:,} km")


def main():
    """Main function"""
    extractor = ReceiptExtractor("receipts")
    extractor.process_all_pdfs()
    extractor.save_to_json()
    extractor.generate_summary()


if __name__ == "__main__":
    main()
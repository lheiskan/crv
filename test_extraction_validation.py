#!/usr/bin/env python3
"""
Unit tests for validating extraction results against ground truth data.
Tests compare extracted data.json against verified.json for accuracy.
"""

import json
import unittest
from pathlib import Path
from typing import Dict, List, Tuple, Any


class ExtractionValidationTest(unittest.TestCase):
    """Test extraction results against verified ground truth data."""
    
    def setUp(self):
        """Set up test paths."""
        self.extracted_dir = Path("extracted")
        self.verified_dir = Path("verified")
        
        # Collect all test cases (PDFs with both extracted and verified data)
        self.test_cases = self._find_test_cases()
    
    def _find_test_cases(self) -> List[Path]:
        """Find all PDFs that have both extracted and verified data."""
        test_cases = []
        
        if not self.verified_dir.exists():
            return test_cases
        
        for verified_pdf_dir in self.verified_dir.iterdir():
            if verified_pdf_dir.is_dir():
                verified_json = verified_pdf_dir / "verified.json"
                extracted_json = self.extracted_dir / verified_pdf_dir.name / "data.json"
                
                if verified_json.exists() and extracted_json.exists():
                    test_cases.append(verified_pdf_dir.name)
        
        return test_cases
    
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _compare_values(self, extracted_value: Any, ground_truth_value: Any) -> bool:
        """Compare two values - exact comparison only, no calculations."""
        return extracted_value == ground_truth_value
    
    def _validate_step(self, step_name: str, extracted_data: Dict, 
                      ground_truth: Dict, step_config: Dict) -> Tuple[List[str], List[str], List[str]]:
        """
        Validate a single extraction step against ground truth.
        Returns: (errors, warnings, info_messages)
        """
        errors = []
        warnings = []
        info_messages = []
        
        required_fields = step_config.get("required_fields", [])
        warning_fields = step_config.get("warning_if_missing", [])
        optional_fields = step_config.get("optional_fields", [])
        
        # Check required fields
        for field in required_fields:
            if field not in extracted_data:
                errors.append(f"{step_name}: REQUIRED field '{field}' not found")
            elif field in ground_truth:
                if not self._compare_values(extracted_data[field], ground_truth[field]):
                    errors.append(
                        f"{step_name}: REQUIRED field '{field}' incorrect - "
                        f"got {extracted_data[field]}, expected {ground_truth[field]}"
                    )
        
        # Check warning fields
        for field in warning_fields:
            if field not in extracted_data:
                warnings.append(f"{step_name}: WARNING field '{field}' not found")
            elif field in ground_truth:
                if not self._compare_values(extracted_data[field], ground_truth[field]):
                    errors.append(
                        f"{step_name}: WARNING field '{field}' has incorrect value - "
                        f"got {extracted_data[field]}, expected {ground_truth[field]}"
                    )
        
        # Check optional fields
        for field in optional_fields:
            if field not in extracted_data:
                info_messages.append(f"{step_name}: Optional field '{field}' not found")
            elif field in ground_truth:
                if not self._compare_values(extracted_data[field], ground_truth[field]):
                    errors.append(
                        f"{step_name}: Optional field '{field}' has incorrect value - "
                        f"got {extracted_data[field]}, expected {ground_truth[field]}"
                    )
        
        return errors, warnings, info_messages
    
    def test_extraction_accuracy(self):
        """Test all PDF extractions against their ground truth."""
        
        if not self.test_cases:
            self.skipTest("No test cases found (no verified PDFs)")
        
        all_errors = []
        all_warnings = []
        all_info = []
        
        for pdf_name in self.test_cases:
            # Load data
            extracted_json = self._load_json(self.extracted_dir / pdf_name / "data.json")
            verified_json = self._load_json(self.verified_dir / pdf_name / "verified.json")
            
            ground_truth = verified_json["ground_truth"]
            expected_extraction = verified_json["expected_extraction"]
            
            print(f"\n{'='*60}")
            print(f"Testing: {pdf_name}")
            print(f"{'='*60}")
            
            # Check each processing step that was executed
            for step in extracted_json.get("processing_steps", []):
                step_name = step["step_name"]
                
                # Skip OCR step (no field validation needed)
                if step_name == "ocr":
                    continue
                
                # Get extracted fields from this step
                step_extracted = step.get("extracted_fields", {})
                
                # Get expectations for this step
                if step_name in expected_extraction:
                    step_config = expected_extraction[step_name]
                    errors, warnings, info = self._validate_step(
                        step_name, step_extracted, ground_truth, step_config
                    )
                    
                    all_errors.extend(errors)
                    all_warnings.extend(warnings)
                    all_info.extend(info)
                    
                    # Print step results
                    print(f"\n{step_name} step:")
                    if step_extracted:
                        print(f"  Extracted: {list(step_extracted.keys())}")
                    else:
                        print(f"  No fields extracted")
            
            # Validate the final merged data
            final_data = extracted_json.get("final_data", {})
            if "final_data" in expected_extraction:
                final_config = expected_extraction["final_data"]
                errors, warnings, info = self._validate_step(
                    "final_data", final_data, ground_truth, final_config
                )
                
                all_errors.extend(errors)
                all_warnings.extend(warnings)
                all_info.extend(info)
                
                print(f"\nfinal_data:")
                if final_data:
                    print(f"  Extracted: {list(final_data.keys())}")
                else:
                    print(f"  No final data")
            
            # Print validation results for this PDF
            pdf_errors = [e for e in errors if pdf_name in e or "final_data" in e or "parsing" in e or "llm_extraction" in e]
            pdf_warnings = [w for w in warnings if pdf_name in w or "final_data" in w or "parsing" in w or "llm_extraction" in w]
            pdf_info = [i for i in info if pdf_name in i or "final_data" in i or "parsing" in i or "llm_extraction" in i]
            
            if pdf_errors or pdf_warnings or pdf_info:
                print(f"\nValidation results:")
                
                if pdf_errors:
                    print("\n❌ ERRORS:")
                    for error in pdf_errors:
                        print(f"  - {error}")
                
                if pdf_warnings:
                    print("\n⚠️  WARNINGS:")
                    for warning in pdf_warnings:
                        print(f"  - {warning}")
                
                if pdf_info:
                    print("\nℹ️  INFO:")
                    for info_msg in pdf_info:
                        print(f"  - {info_msg}")
            else:
                print(f"\n✅ All fields correctly extracted!")
        
        # Print summary
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Total PDFs tested: {len(self.test_cases)}")
        print(f"Total errors: {len(all_errors)}")
        print(f"Total warnings: {len(all_warnings)}")
        print(f"Total info messages: {len(all_info)}")
        
        # Fail the test if there are any errors
        if all_errors:
            self.fail(f"\n{len(all_errors)} extraction errors found. See details above.")
    
    def test_required_fields_present(self):
        """Test that all required fields are present in final_data."""
        
        if not self.test_cases:
            self.skipTest("No test cases found")
        
        for pdf_name in self.test_cases:
            with self.subTest(pdf=pdf_name):
                extracted_json = self._load_json(self.extracted_dir / pdf_name / "data.json")
                verified_json = self._load_json(self.verified_dir / pdf_name / "verified.json")
                
                final_data = extracted_json.get("final_data", {})
                
                # Get required fields from final_data config
                if "final_data" in verified_json["expected_extraction"]:
                    required_fields = verified_json["expected_extraction"]["final_data"].get("required_fields", [])
                    missing_required = set(required_fields) - set(final_data.keys())
                    
                    self.assertEqual(
                        len(missing_required), 0,
                        f"Missing required fields in {pdf_name}: {missing_required}"
                    )


def run_single_test(pdf_name: str):
    """Run validation test for a single PDF."""
    suite = unittest.TestSuite()
    
    # Create a test instance with custom PDF filter
    test = ExtractionValidationTest('test_extraction_accuracy')
    test.test_cases = [Path(pdf_name).name] if Path(f"verified/{pdf_name}").exists() else []
    
    suite.addTest(test)
    
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Test specific PDF
        pdf_name = sys.argv[1]
        run_single_test(pdf_name)
    else:
        # Run all tests
        unittest.main(verbosity=2)
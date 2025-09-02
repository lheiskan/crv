#!/usr/bin/env python3
"""
Complete build script for the service history visualization.
Runs all steps: data extraction → data model → static site generation
"""

import subprocess
import sys
from pathlib import Path


def run_command(command: str, description: str):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False


def build_visualization():
    """Build complete visualization from PDFs to HTML"""
    
    print("🚀 Building Car Service History Visualization")
    print("=" * 50)
    
    # Check if we have receipt files
    receipts_dir = Path("receipts")
    receipts_2_dir = Path("receipts_2")
    
    if not receipts_dir.exists() or not list(receipts_dir.glob("*.pdf")):
        print("⚠️  No PDFs found in receipts/ folder")
    else:
        print(f"📁 Found {len(list(receipts_dir.glob('*.pdf')))} PDFs in receipts/")
        
    if not receipts_2_dir.exists() or not list(receipts_2_dir.glob("*.pdf")):
        print("⚠️  No PDFs found in receipts_2/ folder")
    else:
        print(f"📁 Found {len(list(receipts_2_dir.glob('*.pdf')))} PDFs in receipts_2/")
    
    # Step 1: Extract simple receipts (if not already done)
    if not Path("service_history.json").exists():
        print("\n📄 Extracting simple receipts...")
        if not run_command("python extract_receipts.py", "Extract simple receipts"):
            print("⚠️  Simple receipt extraction failed, continuing...")
    else:
        print("✅ Simple receipts already extracted")
    
    # Step 2: Extract complex receipts (if not already done)  
    if not Path("complex_receipts.json").exists():
        print("\n📄 Extracting complex receipts...")
        if not run_command("python extract_complex_receipts.py", "Extract complex receipts"):
            print("⚠️  Complex receipt extraction failed, continuing...")
    else:
        print("✅ Complex receipts already extracted")
    
    # Step 3: Generate data model
    if not run_command("python generate_data_model.py", "Generate unified data model"):
        print("❌ Data model generation failed!")
        return False
    
    # Step 4: Generate static site
    if not run_command("python generate_static_site.py", "Generate static HTML site"):
        print("❌ Static site generation failed!")
        return False
    
    print("\n🎉 Build completed successfully!")
    print("📊 Open service_history.html in your browser to view the visualization")
    
    # Show file sizes
    files_to_check = [
        "service_history.json",
        "complex_receipts.json", 
        "service_data_model.json",
        "service_history.html"
    ]
    
    print("\n📁 Generated files:")
    for file in files_to_check:
        path = Path(file)
        if path.exists():
            size_kb = path.stat().st_size / 1024
            print(f"  {file}: {size_kb:.1f} KB")
    
    return True


if __name__ == "__main__":
    success = build_visualization()
    sys.exit(0 if success else 1)
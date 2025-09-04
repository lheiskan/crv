#!/bin/bash
# verify_receipts.sh - Interactive receipt verification tool
# 
# Workflow:
# 1. Finds receipts with claude.json but no verified.json
# 2. Opens PDF and nvim editor for manual verification
# 3. Continues through all unverified receipts

set -e

echo "🔍 Starting receipt verification workflow..."
echo "Press Ctrl+C to skip current receipt, Ctrl+C twice to exit"
echo

verified_count=0
skipped_count=0
total_count=0

# Find all PDFs that need verification
for pdf in receipts/*.pdf; do
    [ ! -f "$pdf" ] && continue
    
    pdf_basename=$(basename "$pdf")
    dir="verified/$pdf_basename"
    
    # Skip if already verified
    if [ -f "$dir/verified.json" ]; then
        continue
    fi
    
    # Skip if no claude.json exists
    if [ ! -f "$dir/claude.json" ]; then
        echo "⚠️  Skipping $pdf_basename - no claude.json found"
        continue
    fi
    
    ((total_count++))
    
    echo "📄 Processing: $pdf_basename"
    echo "   Opening PDF and editor..."
    
    # Copy claude.json to verified.json
    cp "$dir/claude.json" "$dir/verified.json"
    
    # Open PDF in background
    if command -v open >/dev/null 2>&1; then
        # macOS
        open "$pdf" &
        pdf_pid=$!
    elif command -v xdg-open >/dev/null 2>&1; then
        # Linux
        xdg-open "$pdf" &
        pdf_pid=$!
    else
        echo "   ⚠️  Could not open PDF - no suitable viewer found"
        pdf_pid=""
    fi
    
    # Open nvim and wait for user to finish editing
    if nvim "$dir/verified.json"; then
        echo "   ✅ Verified: $pdf_basename"
        ((verified_count++))
    else
        echo "   ⏭️  Skipped: $pdf_basename"
        # Remove the copied verified.json if user skipped
        rm -f "$dir/verified.json"
        ((skipped_count++))
    fi
    
    # Try to close the PDF viewer (macOS only)
#    if [ -n "$pdf_pid" ] && command -v osascript >/dev/null 2>&1; then
#        # Close Preview app on macOS
#        osascript -e 'tell application "Preview" to quit' 2>/dev/null || true
#    fi
    
    echo
done

# Summary
echo "📊 Verification Summary:"
echo "   ✅ Verified: $verified_count"
echo "   ⏭️  Skipped: $skipped_count" 
echo "   📝 Total processed: $total_count"

if [ $total_count -eq 0 ]; then
    echo "🎉 All receipts are already verified!"
else
    echo "🎉 Verification workflow complete!"
fi

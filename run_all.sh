#!/bin/bash
# Run the complete pipeline: search → clone → count

cd "$(dirname "$0")"
source venv/bin/activate

echo "================================================================================"
echo "🚀 Running Complete Pipeline"
echo "================================================================================"
echo ""

echo "Step 1/3: Searching for repos on GitHub..."
python3 github_searcher.py
if [ $? -ne 0 ]; then
    echo "❌ Search failed!"
    exit 1
fi
echo ""

echo "Step 2/3: Cloning repos..."
python3 git_cloner.py
if [ $? -ne 0 ]; then
    echo "❌ Cloning failed!"
    exit 1
fi
echo ""

echo "Step 3/3: Counting tokens..."
python3 token_counter.py
if [ $? -ne 0 ]; then
    echo "❌ Token counting failed!"
    exit 1
fi
echo ""

echo "================================================================================"
echo "✅ Pipeline complete!"
echo "================================================================================"


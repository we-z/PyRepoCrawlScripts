#!/bin/bash
# Run the GitHub crawler

cd "$(dirname "$0")"
source venv/bin/activate
python3 github_crawler.py


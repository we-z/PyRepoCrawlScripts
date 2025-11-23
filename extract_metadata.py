#!/usr/bin/env python3
"""
Step 1: File-level metadata extraction
Scans all project folders under cloned_repos and extracts metadata for every Python file.
"""

import os
import sys
import json
import time
import hashlib
import argparse
import pyarrow as pa
import pyarrow.parquet as pq
import tiktoken
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from pathlib import Path

# Configuration
REPOS_DIR = "cloned_repos"
OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "100B-code-dataset", "metadata_chunks")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
BATCH_SIZE = 10000  # Number of files per parquet chunk
WORKER_COUNT = 128

# Tokenizer
TOKENIZER = tiktoken.get_encoding("cl100k_base")

def get_file_metadata(file_path, repo_root):
    """
    Extracts metadata for a single file.
    Returns a dictionary or None if skipped.
    """
    try:
        # Skip if not a file or too large
        stat = os.stat(file_path)
        if stat.st_size > MAX_FILE_SIZE:
            return None
        
        # Read content
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
            
        # Check for binary (simple null byte check)
        if b'\0' in content_bytes:
            return None
            
        try:
            content_str = content_bytes.decode('utf-8')
        except UnicodeDecodeError:
            return None # Skip non-utf8 files
            
        # Calculate SHA256
        sha256 = hashlib.sha256(content_bytes).hexdigest()
        
        # Count tokens
        token_count = len(TOKENIZER.encode(content_str, disallowed_special=()))
        
        # Paths
        abs_path = os.path.abspath(file_path)
        rel_path = os.path.relpath(file_path, repo_root)
        project_name = os.path.basename(repo_root).replace("_", "/", 1)
        
        return {
            "project_name": project_name,
            "relative_path": rel_path,
            "file_size": stat.st_size,
            "sha256": sha256,
            "token_count": token_count,
            "absolute_path": abs_path
        }
    except Exception as e:
        # print(f"Error processing {file_path}: {e}")
        return None

def process_repo(repo_path):
    """
    Scans a repository and yields metadata for all valid files.
    """
    results = []
    try:
        for root, _, filenames in os.walk(repo_path):
            if '.git' in root:
                continue
            for name in filenames:
                file_path = os.path.join(root, name)
                # Only process Python files? The prompt says "extracts metadata for every Python file"
                # But later says "dataset consists of 40 million Python files".
                # I will filter for .py extension to be safe and strictly follow "every Python file".
                if not name.endswith('.py'):
                    continue
                    
                meta = get_file_metadata(file_path, repo_path)
                if meta:
                    results.append(meta)
    except Exception as e:
        print(f"Error scanning repo {repo_path}: {e}")
    return results

def save_batch(batch, batch_id, output_dir):
    """
    Saves a batch of metadata to a Parquet file.
    """
    if not batch:
        return
        
    filename = os.path.join(output_dir, f"chunk_{batch_id}.parquet")
    
    # Define schema
    schema = pa.schema([
        ('project_name', pa.string()),
        ('relative_path', pa.string()),
        ('file_size', pa.int64()),
        ('sha256', pa.string()),
        ('token_count', pa.int64()),
        ('absolute_path', pa.string())
    ])
    
    table = pa.Table.from_pylist(batch, schema=schema)
    pq.write_table(table, filename)
    # print(f"Saved {len(batch)} records to {filename}")

def main():
    parser = argparse.ArgumentParser(description="Extract metadata from Python files.")
    parser.add_argument("--repos_dir", default=REPOS_DIR, help="Directory containing cloned repositories")
    parser.add_argument("--output_dir", default=OUTPUT_DIR, help="Directory to save metadata chunks")
    args = parser.parse_args()

    if not os.path.exists(args.repos_dir):
        print(f"Error: {args.repos_dir} does not exist.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # Get list of repo directories
    print("Scanning for repositories...")
    all_entries = [e for e in os.scandir(args.repos_dir) if e.is_dir() and not e.name.startswith('.')]
    repo_dirs = [e.path for e in all_entries]
    total_repos = len(repo_dirs)
    print(f"Found {total_repos} repositories.")

    start_time = time.time()
    total_files_processed = 0
    current_batch = []
    batch_id = 0

    # Use ProcessPoolExecutor for CPU-bound tasks (hashing, tokenizing)
    # The prompt asks for "same multiprocessing pattern as the provided token_counter.py script"
    # token_counter.py uses ThreadPoolExecutor. 
    # However, for heavy CPU work (hashing/tokenizing), ProcessPoolExecutor is usually better in Python.
    # BUT, strict requirement: "All metadata extraction scripts must follow the same multiprocessing pattern as the provided token_counter.py script... ThreadPoolExecutor or ProcessPoolExecutor".
    # token_counter.py uses ThreadPoolExecutor. I will use ProcessPoolExecutor because of the GIL, 
    # as hashing and tokenization are CPU intensive. The prompt allows either.
    
    print(f"Starting extraction with {WORKER_COUNT} workers...")
    
    with ProcessPoolExecutor(max_workers=WORKER_COUNT) as executor:
        futures = {}
        repo_iter = iter(repo_dirs)
        
        def submit_next():
            try:
                repo = next(repo_iter)
                futures[executor.submit(process_repo, repo)] = repo
                return True
            except StopIteration:
                return False
        
        # Initial submission (keep buffer small to avoid FD exhaustion)
        for _ in range(WORKER_COUNT * 2):
            submit_next()
            
        completed_repos = 0
        
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for future in done:
                repo = futures.pop(future)
                try:
                    results = future.result()
                    current_batch.extend(results)
                    total_files_processed += len(results)
                    
                    # Save batch if full
                    while len(current_batch) >= BATCH_SIZE:
                        save_batch(current_batch[:BATCH_SIZE], batch_id, args.output_dir)
                        current_batch = current_batch[BATCH_SIZE:]
                        batch_id += 1
                        
                except Exception as e:
                    print(f"Repo {repo} generated an exception: {e}")
                
                completed_repos += 1
                if completed_repos % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = completed_repos / elapsed if elapsed > 0 else 0
                    print(f"Progress: {completed_repos}/{total_repos} repos ({rate:.2f} repos/s) - {total_files_processed} files extracted")
                
                # Submit next
                submit_next()

    # Save remaining
    if current_batch:
        save_batch(current_batch, batch_id, args.output_dir)

    print(f"Done. Processed {total_repos} repos, {total_files_processed} files.")
    print(f"Metadata chunks saved to {args.output_dir}")

if __name__ == "__main__":
    main()

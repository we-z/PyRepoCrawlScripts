#!/usr/bin/env python3
"""
Test script for the dataset preparation pipeline.
Creates dummy data and runs all scripts.
"""

import os
import sys
import shutil
import json
import subprocess
import tiktoken

# Configuration
TEST_DIR = "test_env"
REPOS_DIR = os.path.join(TEST_DIR, "cloned_repos")
OUTPUT_DIR = os.path.join(TEST_DIR, "output")
TOKEN_COUNTS_FILE = os.path.join(TEST_DIR, "token_counts.json")

def setup_test_env():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(REPOS_DIR)
    os.makedirs(OUTPUT_DIR)

    # Create dummy repos
    repos = ["repo_a", "repo_b"]
    total_tokens = 0
    total_files = 0
    repo_stats = {}
    
    enc = tiktoken.get_encoding("cl100k_base")

    for repo in repos:
        repo_path = os.path.join(REPOS_DIR, repo)
        os.makedirs(repo_path)
        
        repo_tokens = 0
        repo_files = 0
        
        # Create files
        for i in range(5):
            filename = f"file_{i}.py"
            content = f"print('Hello from {repo} file {i}')\n" * 10
            with open(os.path.join(repo_path, filename), 'w') as f:
                f.write(content)
            
            tokens = len(enc.encode(content, disallowed_special=()))
            repo_tokens += tokens
            repo_files += 1
            
        repo_stats[repo] = {"tokens": repo_tokens, "files_processed": repo_files}
        total_tokens += repo_tokens
        total_files += repo_files

    # Create token_counts.json
    with open(TOKEN_COUNTS_FILE, 'w') as f:
        json.dump({
            "total_tokens": total_tokens,
            "total_repos": len(repos),
            "total_files": total_files,
            "repos": repo_stats
        }, f)
        
    print(f"Setup complete. Created {len(repos)} repos, {total_files} files, {total_tokens} tokens.")

def run_command(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(result.stderr)
        sys.exit(1)
    print(result.stdout)

def main():
    setup_test_env()
    
    # 1. Extract Metadata
    print("\n--- Step 1: Extract Metadata ---")
    run_command(f"{sys.executable} extract_metadata.py --repos_dir {REPOS_DIR} --output_dir {os.path.join(OUTPUT_DIR, 'metadata_chunks')}")
    
    # 2. Merge Metadata
    print("\n--- Step 2: Merge Metadata ---")
    run_command(f"{sys.executable} merge_metadata.py --chunks_dir {os.path.join(OUTPUT_DIR, 'metadata_chunks')} --output_file {os.path.join(OUTPUT_DIR, 'global_index.parquet')}")
    
    # 3. Create Shards
    print("\n--- Step 3: Create Shards ---")
    run_command(f"{sys.executable} create_shards.py --global_index {os.path.join(OUTPUT_DIR, 'global_index.parquet')} --shards_dir {os.path.join(OUTPUT_DIR, 'shards')} --shard_meta_dir {os.path.join(OUTPUT_DIR, 'shard_metadata')} --repos_dir {REPOS_DIR}")
    
    # 4. Finalize Metadata
    print("\n--- Step 4: Finalize Metadata ---")
    run_command(f"{sys.executable} finalize_metadata.py --shard_meta_dir {os.path.join(OUTPUT_DIR, 'shard_metadata')} --output_file {os.path.join(OUTPUT_DIR, 'final_metadata.parquet')} --token_counts {TOKEN_COUNTS_FILE} --update-counts")
    
    print("\n✅ Test Pipeline Completed Successfully!")

if __name__ == "__main__":
    main()

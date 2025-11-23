#!/usr/bin/env python3
"""
Step 3: Create deterministic compressed .tar.zst shards
Streams files into .tar.zst archives and produces per-shard metadata.
"""

import os
import sys
import argparse
import tarfile
import time
import pyarrow as pa
import pyarrow.parquet as pq
import zstandard as zstd
import io
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "100B-code-dataset")
GLOBAL_INDEX = os.path.join(BASE_OUTPUT_DIR, "global_index.parquet")
SHARDS_DIR = os.path.join(BASE_OUTPUT_DIR, "shards")
SHARD_META_DIR = os.path.join(BASE_OUTPUT_DIR, "shard_metadata")
REPOS_DIR = "cloned_repos"
TARGET_SHARD_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB
MIN_SHARD_SIZE = 5 * 1024 * 1024 * 1024    # 5 GB
MAX_SHARD_SIZE = 20 * 1024 * 1024 * 1024   # 20 GB
WORKER_COUNT = 16  # Number of parallel shard creators

def get_absolute_path(project_name, file_path, repos_dir):
    """
    Reconstructs absolute path from project_name and file_path.
    project_name has '/' but directory has '_'.
    """
    # project_name was created via: os.path.basename(repo_root).replace("_", "/", 1)
    # So we reverse it: replace first "/" with "_"
    repo_dir_name = project_name.replace("/", "_", 1)
    return os.path.join(repos_dir, repo_dir_name, file_path)

def create_shard(shard_id, files, output_dir, meta_output_dir, repos_dir):
    """
    Creates a single .tar.zst shard and its corresponding metadata file.
    files: list of dicts (row from parquet)
    """
    shard_filename = f"shard_{shard_id:05d}.tar.zst"
    shard_path = os.path.join(output_dir, shard_filename)
    meta_path = os.path.join(meta_output_dir, f"shard_{shard_id:05d}_metadata.parquet")
    
    if os.path.exists(shard_path) and os.path.exists(meta_path):
        print(f"Shard {shard_id} already exists. Skipping.")
        return

    print(f"Creating {shard_filename} with {len(files)} files...")
    
    # Prepare metadata list with shard_id
    shard_meta = []
    
    # Setup Zstandard compressor
    cctx = zstd.ZstdCompressor(level=3)
    
    try:
        with open(shard_path, 'wb') as f_out:
            with cctx.stream_writer(f_out) as zstream:
                with tarfile.open(fileobj=zstream, mode='w|') as tar:
                    for row in files:
                        project_name = row['project_name']
                        file_path = row['file_path']
                        abs_path = get_absolute_path(project_name, file_path, repos_dir)
                        
                        # Validate existence
                        if not os.path.exists(abs_path):
                            print(f"Warning: File not found {abs_path}. Skipping.")
                            continue
                            
                        # Add to tar
                        try:
                            tar.add(abs_path, arcname=os.path.join(project_name, file_path))
                            
                            # Add to metadata
                            row_copy = row.copy()
                            row_copy['shard_id'] = f"{shard_id:05d}"
                            shard_meta.append(row_copy)
                        except Exception as e:
                            print(f"Error adding {abs_path} to shard: {e}")

        # Write metadata
        if shard_meta:
            schema = pa.schema([
                ('project_name', pa.string()),
                ('file_path', pa.string()),
                ('tokens', pa.int64()),
                ('size', pa.int64()),
                ('sha256', pa.string()),
                ('shard_id', pa.string())
            ])
            table = pa.Table.from_pylist(shard_meta, schema=schema)
            pq.write_table(table, meta_path)
            
        print(f"✅ Created {shard_filename} ({os.path.getsize(shard_path) / 1024 / 1024:.2f} MB)")
        
    except Exception as e:
        print(f"❌ Error creating shard {shard_id}: {e}")
        # Cleanup partial files
        if os.path.exists(shard_path):
            os.remove(shard_path)

def main():
    parser = argparse.ArgumentParser(description="Create deterministic shards.")
    parser.add_argument("--global_index", default=GLOBAL_INDEX, help="Path to global index parquet")
    parser.add_argument("--shards_dir", default=SHARDS_DIR, help="Directory to save shards")
    parser.add_argument("--shard_meta_dir", default=SHARD_META_DIR, help="Directory to save shard metadata")
    parser.add_argument("--repos_dir", default=REPOS_DIR, help="Directory containing cloned repositories")
    args = parser.parse_args()

    if not os.path.exists(args.global_index):
        print(f"Error: {args.global_index} does not exist.")
        sys.exit(1)

    os.makedirs(args.shards_dir, exist_ok=True)
    os.makedirs(args.shard_meta_dir, exist_ok=True)

    print("Reading global index...")
    parquet_file = pq.ParquetFile(args.global_index)
    
    current_shard_files = []
    current_shard_size = 0
    shard_id = 0
    
    print(f"Starting shard creation with {WORKER_COUNT} workers...")
    
    with ProcessPoolExecutor(max_workers=WORKER_COUNT) as executor:
        futures = set()
        
        def submit_shard(s_id, files):
            # Submit a copy of the list to avoid mutation issues (though processes copy anyway)
            f = executor.submit(create_shard, s_id, files, args.shards_dir, args.shard_meta_dir, args.repos_dir)
            futures.add(f)
            
        # Iterate over row groups to avoid loading everything
        for i in range(parquet_file.num_row_groups):
            table = parquet_file.read_row_group(i)
            rows = table.to_pylist()
            
            for row in rows:
                file_size = row['size']
                
                # Check if adding this file would exceed max size
                if current_shard_size + file_size > MAX_SHARD_SIZE:
                    # If we have enough data for a shard, create it
                    if current_shard_size >= MIN_SHARD_SIZE:
                        submit_shard(shard_id, current_shard_files)
                        shard_id += 1
                        current_shard_files = []
                        current_shard_size = 0
                        
                        # Flow control: Don't queue too many shards in memory
                        if len(futures) >= WORKER_COUNT * 2:
                            done, _ = wait(futures, return_when=FIRST_COMPLETED)
                            futures.difference_update(done)
                
                current_shard_files.append(row)
                current_shard_size += file_size
                
                # If we hit target size, create shard
                if current_shard_size >= TARGET_SHARD_SIZE:
                    submit_shard(shard_id, current_shard_files)
                    shard_id += 1
                    current_shard_files = []
                    current_shard_size = 0
                    
                    # Flow control
                    if len(futures) >= WORKER_COUNT * 2:
                        done, _ = wait(futures, return_when=FIRST_COMPLETED)
                        futures.difference_update(done)

        # Create final shard
        if current_shard_files:
            submit_shard(shard_id, current_shard_files)

        # Wait for all
        while futures:
            done, _ = wait(futures)
            futures.difference_update(done)

    print("Done creating shards.")

if __name__ == "__main__":
    main()

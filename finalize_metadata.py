#!/usr/bin/env python3
"""
Step 4: Produce final shard-aware Parquet metadata
Merges all per-shard metadata, verifies integrity, and checks against token_counts.json.
"""

import os
import sys
import json
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "100B-code-dataset")
SHARD_META_DIR = os.path.join(BASE_OUTPUT_DIR, "shard_metadata")
FINAL_OUTPUT = os.path.join(BASE_OUTPUT_DIR, "final_metadata.parquet")
TOKEN_COUNTS_FILE = "token_counts.json"

def load_token_counts(token_counts_file):
    if not os.path.exists(token_counts_file):
        print(f"Warning: {token_counts_file} not found. Skipping token count verification.")
        return None
    try:
        with open(token_counts_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {token_counts_file}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Finalize metadata and verify.")
    parser.add_argument("--shard_meta_dir", default=SHARD_META_DIR, help="Directory containing shard metadata")
    parser.add_argument("--output_file", default=FINAL_OUTPUT, help="Path to save final metadata")
    parser.add_argument("--token_counts", default=TOKEN_COUNTS_FILE, help="Path to token counts json file")
    parser.add_argument("--update-counts", action="store_true", help="Update token_counts.json if mismatches are found")
    args = parser.parse_args()

    if not os.path.exists(args.shard_meta_dir):
        print(f"Error: {args.shard_meta_dir} does not exist.")
        sys.exit(1)

    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    print(f"Scanning shard metadata in {args.shard_meta_dir}...")
    meta_files = [os.path.join(args.shard_meta_dir, f) for f in os.listdir(args.shard_meta_dir) if f.endswith('.parquet')]
    meta_files.sort()

    if not meta_files:
        print("No shard metadata files found.")
        sys.exit(1)

    # Schema should match the one used in create_shards
    schema = pa.schema([
        ('project_name', pa.string()),
        ('file_path', pa.string()),
        ('tokens', pa.int64()),
        ('size', pa.int64()),
        ('sha256', pa.string()),
        ('shard_id', pa.string())
    ])

    print(f"Found {len(meta_files)} metadata files. Merging...")

    writer = None
    total_rows = 0
    total_tokens = 0
    total_size = 0
    
    # Per-repo aggregation
    repo_stats = {} # project_name -> {tokens: int, files: int}

    try:
        writer = pq.ParquetWriter(args.output_file, schema)
        
        for meta_file in meta_files:
            try:
                table = pq.read_table(meta_file)
                
                # Verify schema matches
                if not table.schema.equals(schema):
                    # Cast if needed, but warn
                    # print(f"Warning: Schema mismatch in {meta_file}. Casting...")
                    table = table.cast(schema)
                
                writer.write_table(table)
                
                # Accumulate stats
                total_rows += len(table)
                
                # Aggregate columns
                df = table.to_pandas()
                total_tokens += df['tokens'].sum()
                total_size += df['size'].sum()
                
                # Aggregate per repo
                # Group by project_name and sum tokens/counts
                # This is efficient enough for chunked processing
                grouped = df.groupby('project_name').agg({'tokens': 'sum', 'file_path': 'count'}).reset_index()
                for _, row in grouped.iterrows():
                    p_name = row['project_name']
                    t_count = row['tokens']
                    f_count = row['file_path']
                    
                    if p_name not in repo_stats:
                        repo_stats[p_name] = {'tokens': 0, 'files_processed': 0}
                    
                    repo_stats[p_name]['tokens'] += int(t_count)
                    repo_stats[p_name]['files_processed'] += int(f_count)
                
            except Exception as e:
                print(f"Error reading {meta_file}: {e}")

    finally:
        if writer:
            writer.close()

    print(f"✅ Final metadata saved to {args.output_file}")
    print(f"Total Files: {total_rows:,}")
    print(f"Total Tokens: {total_tokens:,}")
    print(f"Total Size: {total_size / 1024 / 1024 / 1024:.2f} GB")

    # Verification against token_counts.json
    token_data = load_token_counts(args.token_counts)
    if token_data:
        expected_tokens = token_data.get("total_tokens", 0)
        expected_files = token_data.get("total_files", 0)
        
        print("\nVerification Results:")
        print(f"Expected Tokens: {expected_tokens:,}")
        print(f"Actual Tokens:   {total_tokens:,}")
        
        if expected_tokens == total_tokens:
            print("✅ Token count matches!")
        else:
            diff = total_tokens - expected_tokens
            print(f"❌ Token count mismatch! Diff: {diff:,}")

        print(f"Expected Files:  {expected_files:,}")
        print(f"Actual Files:    {total_rows:,}")
        
        if expected_files == total_rows:
            print("✅ File count matches!")
        else:
            diff = total_rows - expected_files
            print(f"❌ File count mismatch! Diff: {diff:,}")
            
        # Note: Mismatch might happen if we filtered out binary/large files in extract_metadata
        # but token_counter.py included them?
        # token_counter.py skips > 5MB and binary (via errors='ignore' and encoding check implicitly?)
        # token_counter.py:
        # if stat.st_size > MAX_SIZE: continue
        # with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        #    content = f.read(MAX_LEN)
        #    if content: ...
        
        # extract_metadata.py:
        # if stat.st_size > MAX_FILE_SIZE: return None
        # with open(file_path, 'rb') as f: content_bytes = f.read()
        # if b'\0' in content_bytes: return None
        # try: content_str = content_bytes.decode('utf-8') except: return None
        
        # There might be slight differences in how "binary" is detected.
        # token_counter uses errors='ignore', so it might process binary files as garbage text.
        # extract_metadata is stricter (b'\0' check).
        # So we expect Actual Files <= Expected Files.
        
        if total_rows < expected_files:
            print("Note: Actual file count is lower. This is expected if extraction was stricter (e.g. skipping binary files).")

        # Update token_counts.json if requested and mismatch found
        if (expected_tokens != total_tokens or expected_files != total_rows) and args.update_counts:
            print(f"\nUpdating {args.token_counts} with accurate numbers...")
            
            # Reconstruct the repos dict with new stats
            # We only have stats for repos we processed. 
            # If there were repos in token_counts that we skipped entirely (e.g. empty), they won't be in repo_stats.
            # But if we want to be accurate to the dataset, we should probably only include what's in the dataset.
            # However, preserving old keys might be desired? 
            # The user said "reflect the accurate numbers". Accurate to the dataset means what we have.
            
            new_data = {
                "total_tokens": int(total_tokens),
                "total_repos": len(repo_stats),
                "total_files": int(total_rows),
                "repos": repo_stats
            }
            
            try:
                with open(args.token_counts, 'w') as f:
                    json.dump(new_data, f, indent=2)
                print("✅ Updated token_counts.json successfully.")
            except Exception as e:
                print(f"❌ Error updating token_counts.json: {e}")

if __name__ == "__main__":
    main()

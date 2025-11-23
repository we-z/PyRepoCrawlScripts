#!/usr/bin/env python3
"""
Step 2: Merge all batch metadata into a global Parquet file
Reads all batch metadata files in streaming mode and writes a single global Parquet metadata file.
"""

import os
import sys
import argparse
import pyarrow as pa
import pyarrow.parquet as pq

# Configuration
BASE_OUTPUT_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "100B-code-dataset")
CHUNKS_DIR = os.path.join(BASE_OUTPUT_DIR, "metadata_chunks")
OUTPUT_FILE = os.path.join(BASE_OUTPUT_DIR, "global_index.parquet")
BATCH_SIZE = 100000  # Rows per row group in output

def main():
    parser = argparse.ArgumentParser(description="Merge metadata chunks into global index.")
    parser.add_argument("--chunks_dir", default=CHUNKS_DIR, help="Directory containing metadata chunks")
    parser.add_argument("--output_file", default=OUTPUT_FILE, help="Path to save the global index parquet file")
    args = parser.parse_args()

    if not os.path.exists(args.chunks_dir):
        print(f"Error: {args.chunks_dir} does not exist.")
        sys.exit(1)

    output_dir = os.path.dirname(args.output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Define final schema
    # Note: 'relative_path' from extraction becomes 'file_path' here as per requirements
    # Schema: project_name, file_path, tokens, size, sha256, shard_id
    schema = pa.schema([
        ('project_name', pa.string()),
        ('file_path', pa.string()),
        ('tokens', pa.int64()),
        ('size', pa.int64()),
        ('sha256', pa.string()),
        ('shard_id', pa.string()) # Nullable
    ])

    print(f"Scanning chunks in {args.chunks_dir}...")
    chunk_files = [os.path.join(args.chunks_dir, f) for f in os.listdir(args.chunks_dir) if f.endswith('.parquet')]
    chunk_files.sort() # Ensure deterministic order if needed, though not strictly required
    
    if not chunk_files:
        print("No chunk files found.")
        sys.exit(0)

    print(f"Found {len(chunk_files)} chunks. Starting merge...")

    writer = None
    total_rows = 0

    try:
        for chunk_file in chunk_files:
            try:
                # Read chunk
                table = pq.read_table(chunk_file)
                
                # Transform to match final schema
                # Rename columns
                # extraction: project_name, relative_path, file_size, sha256, token_count, absolute_path
                # target: project_name, file_path, tokens, size, sha256, shard_id
                
                # We need to keep absolute_path for the sharding step?
                # The requirements for Step 2 say:
                # schema: project_name, file_path, tokens, size, sha256, shard_id
                # BUT Step 3 needs to stream files. It needs the absolute path to read them.
                # "Create a script that... streams files into .tar.zst archives"
                # If we lose absolute_path, we have to reconstruct it from project_name + file_path + REPOS_DIR.
                # That is safer and cleaner.
                # Let's assume file_path is the relative path.
                
                # Rename columns
                table = table.rename_columns(['project_name', 'file_path', 'size', 'sha256', 'tokens', 'absolute_path'])
                
                # Select only needed columns + add shard_id (null)
                # We might want to keep absolute_path for convenience if the user allows extra columns, 
                # but the requirement specifies the schema explicitly.
                # "defines the schema: project_name, file_path, tokens, size, sha256, shard_id"
                # I will stick to the requested schema to be strict.
                # I can reconstruct absolute path later: os.path.join(REPOS_DIR, project_name.replace("/", "_"), file_path)
                # Wait, project_name in extraction was: os.path.basename(repo_root).replace("_", "/", 1)
                # So to get back to directory name: project_name.replace("/", "_", 1)
                
                # Create shard_id column (nulls)
                shard_id_array = pa.array([None] * len(table), type=pa.string())
                table = table.append_column('shard_id', shard_id_array)
                
                # Select and reorder columns
                table = table.select(['project_name', 'file_path', 'tokens', 'size', 'sha256', 'shard_id'])
                
                # Cast to ensure types match exactly
                table = table.cast(schema)

                # Initialize writer with the first chunk's schema (which matches our defined schema)
                if writer is None:
                    writer = pq.ParquetWriter(args.output_file, schema)
                
                writer.write_table(table)
                total_rows += len(table)
                # print(f"Merged {chunk_file} ({len(table)} rows)")
                
            except Exception as e:
                print(f"Error reading {chunk_file}: {e}")

    finally:
        if writer:
            writer.close()

    print(f"✅ Merged {len(chunk_files)} chunks into {args.output_file}")
    print(f"Total rows: {total_rows}")

if __name__ == "__main__":
    main()

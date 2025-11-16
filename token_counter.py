#!/usr/bin/env python3
"""Token Counter for cloned_repos/"""
import sys
import json
from datetime import datetime
from pathlib import Path
import tiktoken
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
REPOS_DIR = BASE_DIR / "cloned_repos"
OUTPUT_FILE = BASE_DIR / "token_counts.json"
TOKENIZER = tiktoken.get_encoding("cl100k_base")
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_CONTENT_LEN = 5_000_000 # 5 million characters

def count_tokens_in_file(file_path: Path) -> int:
    """Counts tokens in a single file, skipping large or non-UTF8 files."""
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE:
            return 0
        content = file_path.read_text(encoding='utf-8')
        if len(content) > MAX_CONTENT_LEN:
            return 0
        return len(TOKENIZER.encode(content, disallowed_special=()))
    except (IOError, UnicodeDecodeError,AttributeError,FileNotFoundError):
        return 0

def count_repo_tokens(repo_path: Path) -> dict:
    """Counts tokens for all processable files in a repository."""
    stats = {"tokens": 0, "files_processed": 0}
    try:
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and '.git' not in file_path.parts:
                tokens = count_tokens_in_file(file_path)
                if tokens > 0:
                    stats["tokens"] += tokens
                    stats["files_processed"] += 1
    except Exception:
        pass  # Ignore errors for a single repo and continue
    return stats

def main():
    """Main function to count tokens in all repositories."""
    if not REPOS_DIR.exists():
        print(f"❌ No '{REPOS_DIR.name}' directory found!")
        sys.exit(1)

    repo_dirs = [d for d in REPOS_DIR.iterdir() if d.is_dir() and not d.name.startswith('.')]
    total_repos = len(repo_dirs)
    print(f"📊 Counting tokens in {total_repos:,} repositories...")

    results = {}
    total_tokens, total_files = 0, 0

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(count_repo_tokens, repo_dir): repo_dir for repo_dir in repo_dirs}
        
        for i, future in enumerate(as_completed(futures), 1):
            repo_dir = futures[future]
            repo_name = repo_dir.name.replace("_", "/", 1)
            try:
                stats = future.result()
                results[repo_name] = stats
                total_tokens += stats['tokens']
                total_files += stats['files_processed']
                
                progress = (i / total_repos) * 100
                bar = '█' * int(progress / 2) + '░' * (50 - int(progress / 2))
                print(f"\r[{bar}] {progress:>5.1f}% ({i:,}/{total_repos:,}) | Tokens: {total_tokens:>15,}", end='', flush=True)
            except Exception as e:
                print(f"\nError processing {repo_name}: {e}")

    print(f"\n\n✅ Token counting complete!")
    
    output_data = {
        "total_tokens": total_tokens,
        "total_repos": total_repos,
        "total_files_processed": total_files,
        "counted_at": datetime.now().isoformat(),
        "repos": results
    }
    OUTPUT_FILE.write_text(json.dumps(output_data, indent=2))

    print(f"Total tokens: {total_tokens:,}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
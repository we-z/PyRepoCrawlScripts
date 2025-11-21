#!/usr/bin/env python3
"""Token Counter for cloned_repos/"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path
import tiktoken
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = Path(__file__).parent
REPOS_DIR = BASE_DIR / "cloned_repos"
OUTPUT_FILE = BASE_DIR / "token_counts.json"
TOKENIZER = tiktoken.get_encoding("cl100k_base")
MAX_FILE_SIZE = 5 * 1024 * 1024
MAX_CONTENT_LEN = 5_000_000

def count_tokens_in_file(file_path: Path) -> int:
    """Counts tokens in a single file, skipping large or non-UTF8 files."""
    try:
        if file_path.stat().st_size > MAX_FILE_SIZE or len(content := file_path.read_text(encoding='utf-8')) > MAX_CONTENT_LEN:
            return 0
        return len(TOKENIZER.encode(content, disallowed_special=()))
    except (IOError, UnicodeDecodeError, AttributeError, FileNotFoundError):
        return 0

def count_repo_tokens(repo_path: Path) -> dict:
    """Counts tokens for all processable files in a repository."""
    stats = {"tokens": 0, "files_processed": 0}
    try:
        for file_path in repo_path.rglob('*'):
            if file_path.is_file() and '.git' not in file_path.parts and (tokens := count_tokens_in_file(file_path)) > 0:
                stats["tokens"] += tokens
                stats["files_processed"] += 1
    except Exception:
        pass
    return stats

def main():
    """Main function to count tokens in all repositories."""
    if not REPOS_DIR.exists():
        print(f"❌ No '{REPOS_DIR.name}' directory found!")
        sys.exit(1)

    print("Gathering list of repository directories...")
    repo_dirs = [Path(e.path) for e in os.scandir(REPOS_DIR) if e.is_dir() and not e.name.startswith('.')]
    total_repos = len(repo_dirs)
    max_repo_name_len = min(max((len(d.name.replace("_", "/", 1)) for d in repo_dirs), default=30), 50)
    progress_width = len(f"[{total_repos:,}/{total_repos:,}]")
    repo_width = max_repo_name_len + 2
    stats_width = total_width = 30

    print(f"📊 Counting tokens in {total_repos:,} repositories...\n")
    print(f"{'Progress':<{progress_width}} {'Status':<7} {'Repository':<{repo_width}} {'Repo Stats':>{stats_width}} {'Running Total':>{total_width}}")
    print("=" * (progress_width + 7 + repo_width + stats_width + total_width + 8))

    results, total_tokens, total_files = {}, 0, 0
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = {executor.submit(count_repo_tokens, repo_dir): repo_dir for repo_dir in repo_dirs}
        for i, future in enumerate(as_completed(futures), 1):
            repo_dir = futures[future]
            repo_name = repo_dir.name.replace("_", "/", 1)
            repo_display_name = repo_name if len(repo_name) <= max_repo_name_len else repo_name[:max_repo_name_len-3] + "..."
            progress_str = f"[{i:,}/{total_repos:,}]"

            try:
                stats = future.result()
                results[repo_name] = stats
                total_tokens += stats['tokens']
                total_files += stats['files_processed']
                repo_stats = f"{stats['tokens']:>15,} tok, {stats['files_processed']:>6,} files"
                total_stats = f"{total_tokens:>15,} tok, {total_files:>6,} files"
                print(f"{progress_str:<{progress_width}}  ✓     {repo_display_name:<{repo_width}} {repo_stats:>{stats_width}}  {total_stats:>{total_width}}")
            except Exception as e:
                print(f"{progress_str:<{progress_width}}  ✗     {repo_display_name:<{repo_width}} {'Error: ' + str(e):>{stats_width}}")

    print(f"\n\n✅ Token counting complete!")
    OUTPUT_FILE.write_text(json.dumps({
        "total_tokens": total_tokens, "total_repos": total_repos, "total_files_processed": total_files,
        "counted_at": datetime.now().isoformat(), "repos": results
    }, indent=2))
    print(f"Total tokens: {total_tokens:,}\nSaved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
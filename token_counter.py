#!/usr/bin/env python3
"""Fast Token Counter for cloned_repos/"""
import sys, os, json, time, tiktoken
from concurrent.futures import ThreadPoolExecutor, as_completed

REPOS_DIR = "cloned_repos"
OUTPUT_FILE = "token_counts.json"
TOKENIZER = tiktoken.get_encoding("cl100k_base")
MAX_SIZE = 5 * 1024 * 1024
MAX_LEN = 5_000_000

def count_repo(repo_path):
    tokens, files = 0, 0
    try:
        for root, _, filenames in os.walk(repo_path):
            if '.git' in root: continue
            for name in filenames:
                try:
                    path = os.path.join(root, name)
                    stat = os.stat(path)
                    if stat.st_size > MAX_SIZE: continue
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(MAX_LEN)
                        if content:
                            tokens += len(TOKENIZER.encode(content, disallowed_special=()))
                            files += 1
                except Exception: pass
    except Exception: pass
    return tokens, files

def main():
    if not os.path.exists(REPOS_DIR): return print(f"❌ No '{REPOS_DIR}' found!")
    repo_dirs = [os.path.join(REPOS_DIR, d) for d in os.listdir(REPOS_DIR) if os.path.isdir(os.path.join(REPOS_DIR, d)) and not d.startswith('.')]
    total_repos = len(repo_dirs)
    print(f"📊 Processing {total_repos:,} repositories with 128 workers...")
    
    results, total_tok, total_files, start_time = {}, 0, 0, time.time()
    print(f"{'Progress':<18} {'Rate':<12} {'Repository':<40} {'Repo Stats':<25} {'Total Stats':<25}")
    print("=" * 120)

    with ThreadPoolExecutor(max_workers=128) as exe:
        futures = {exe.submit(count_repo, p): p for p in repo_dirs}
        for i, f in enumerate(as_completed(futures), 1):
            repo_path = futures[f]
            name = os.path.basename(repo_path).replace("_", "/", 1)
            try:
                t, c = f.result()
                results[name] = {"tokens": t, "files_processed": c}
                total_tok += t
                total_files += c
                
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                prog = f"[{i:,}/{total_repos:,}]"
                r_stats = f"{t:,} tok, {c:,} files"
                t_stats = f"{total_tok:,} tok, {total_files:,} files"
                print(f"{prog:<18} {rate:>6.1f}/s   {name[:38]:<40} {r_stats:<25} {t_stats:<25}")
            except Exception as e:
                print(f"Error {name}: {e}")

    with open(OUTPUT_FILE, 'w') as f:
        json.dump({"total_tokens": total_tok, "total_repos": total_repos, "total_files": total_files, "repos": results}, f, indent=2)
    print(f"\n✅ Done! {total_tok:,} tokens in {total_files:,} files. Saved to {OUTPUT_FILE}")

if __name__ == "__main__": main()
#!/usr/bin/env python3
"""Fast Token Counter for cloned_repos/"""
import sys, os, json, time, tiktoken
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

REPOS_DIR = "cloned_repos"
OUTPUT_FILE = "token_counts.json"
TOKENIZER = tiktoken.get_encoding("cl100k_base")
MAX_SIZE = 5 * 1024 * 1024
MAX_LEN = 5_000_000

def load_existing():
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data = json.load(f)
                return data.get("repos", {}), data.get("total_tokens", 0), data.get("total_files", 0)
        except: pass
    return {}, 0, 0

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
    
    results, total_tok, total_files = load_existing()
    existing_count = len(results)
    
    all_dirs = [e.path for e in os.scandir(REPOS_DIR) if e.is_dir() and not e.name.startswith('.')]
    existing_names = set(results.keys())
    repo_dirs = [d for d in all_dirs if os.path.basename(d).replace("_", "/", 1) not in existing_names]
    
    new_count = len(repo_dirs)
    total_repos = len(all_dirs)
    
    print(f"📊 Found {existing_count:,} cached repos, {new_count:,} new repos to process ({total_repos:,} total)")
    if new_count == 0: return print(f"✅ All repos already counted! {total_tok:,} tokens in {total_files:,} files.")
    
    print(f"{'Progress':<20}        {'Rate':<15}        {'Repository':<45}        {'Repo Stats':<30}        {'Total Stats':<30}")
    print("=" * 160)
    
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=128) as exe:
        futures = {}
        repo_iter = iter(repo_dirs)
        
        def submit_next():
            try:
                p = next(repo_iter)
                futures[exe.submit(count_repo, p)] = p
                return True
            except StopIteration: return False
        
        for _ in range(200): submit_next()
        
        processed = 0
        while futures:
            done, _ = wait(futures, return_when=FIRST_COMPLETED)
            for f in done:
                repo_path = futures.pop(f)
                processed += 1
                name = os.path.basename(repo_path).replace("_", "/", 1)
                try:
                    t, c = f.result()
                    results[name] = {"tokens": t, "files_processed": c}
                    total_tok += t
                    total_files += c
                    
                    elapsed = time.time() - start_time
                    rate = processed / elapsed if elapsed > 0 else 0
                    prog = f"[{processed:,}/{new_count:,}]"
                    r_stats = f"{t:,} tok, {c:,} files"
                    t_stats = f"{total_tok:,} tok, {total_files:,} files"
                    print(f"{prog:<20}        {rate:>6.1f}/s        {name[:43]:<45}        {r_stats:<30}        {t_stats:<30}")
                except Exception as e:
                    print(f"Error {name}: {e}")
                submit_next()
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({"total_tokens": total_tok, "total_repos": total_repos, "total_files": total_files, "repos": results}, f, indent=2)
    print(f"\n✅ Done! {total_tok:,} tokens in {total_files:,} files across {total_repos:,} repos. Saved to {OUTPUT_FILE}")

if __name__ == "__main__": main()
#!/usr/bin/env python3
"""GitHub ML/DL Repo Searcher - Outputs: repos_to_clone.json"""
import os, sys, json, time, requests
from pathlib import Path
from dotenv import load_dotenv
from topics import TOPICS

class GitHubSearcher:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"token {token}"}
        base = Path(__file__).parent
        self.output = base / "repos_to_clone.json"
        self.seen_file = base / "data" / "seen_repos.json"
        self.seen_file.parent.mkdir(exist_ok=True)
        
        repos_dir = base / "cloned_repos"
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() if d.is_dir()} if repos_dir.exists() else set()
        
        self.seen = set()
        if self.seen_file.exists():
            try:
                with open(self.seen_file, 'r') as f:
                    self.seen = set(json.load(f))
            except (json.JSONDecodeError, ValueError):
                print(f"⚠️  Warning: Could not parse {self.seen_file}. Starting fresh.")
    
    def search(self, q: str, page: int, sort: str) -> list:
        try:
            r = requests.get("https://api.github.com/search/repositories",
                           headers=self.headers, params={"q": q, "page": page, "per_page": 100, "sort": sort}, timeout=30)
            if r.status_code == 403:
                time.sleep(int(r.headers.get('X-RateLimit-Reset', time.time())) - int(time.time()) + 10)
                return self.search(q, page, sort)
            return r.json().get('items', []) if r.status_code == 200 else []
        except: return []
    
    def run(self, target: int = 50000):
        already_have = len(self.cloned)
        print("="*90)
        print(f"🔍 GitHub ML/DL Repository Searcher")
        print(f"Target: {target:,} new repos | Already have: {already_have:,} cloned repos")
        print("="*90)
        print()
        
        results = []
        query_num = 0
        for topic in TOPICS:
            for stars in [">=500", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"]:
                for sort in ["stars", "updated", "forks"]:
                    query_num += 1
                    query = f"language:python topic:{topic} stars:{stars}"
                    for page in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                        print(f"Query {query_num:>4}: {query[:55]:55s} | Sort: {sort:8s} | Page: {page}", end='', flush=True)
                        repos_found = self.search(query, page, sort)
                        print(f" | API returned: {len(repos_found):>3} repos", end='', flush=True)
                        if len(repos_found) == 0:
                            print(f" | Skipping remaining pages (0 results)")
                            break
                        new = 0
                        for r in repos_found:
                            rid, name = str(r['id']), r['full_name']
                            if rid not in self.seen and name not in self.cloned:
                                self.seen.add(rid)
                                results.append({"full_name": name, "clone_url": r['clone_url'], "stars": r.get('stargazers_count', 0)})
                                new += 1
                        progress = (len(results) / target) * 100
                        print(f" | New: {new:>3} | Total found: {len(results):>6,} ({progress:>5.1f}%)")
                        if len(results) >= target: break
                    if len(results) >= target: break
                if len(results) >= target: break
            if len(results) >= target: break
        
        existing_results = []
        if self.output.exists():
            try:
                with open(self.output, 'r') as f:
                    existing_results = json.load(f)
            except (json.JSONDecodeError, ValueError): pass
        
        with open(self.output, 'w') as f:
            json.dump(existing_results + results, f, indent=2)
        with open(self.seen_file, 'w') as f:
            json.dump(list(self.seen), f)
        
        print(f"\n{'='*90}\n✅ Search Complete!\n   New unique repos found: {len(results):,}\n   Already have cloned:    {already_have:,}\n   Total after cloning:    {already_have + len(results):,}\n   Saved to: {self.output}\n{'='*90}")

if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get('GITHUB_TOKEN')
    if not token: sys.exit("ERROR: GITHUB_TOKEN not found!")
    GitHubSearcher(token).run(50000)

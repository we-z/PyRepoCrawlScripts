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
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() 
                      if d.is_dir()} if repos_dir.exists() else set()
        self.seen = set()
        if self.seen_file.exists():
            try: self.seen = set(json.load(open(self.seen_file, 'r')))
            except: pass
    def search(self, q: str, page: int, sort: str) -> list:
        try:
            r = requests.get("https://api.github.com/search/repositories",
                headers=self.headers, params={"q": q, "page": page, "per_page": 100,
                "sort": sort}, timeout=30)
            if r.status_code == 403:
                reset = int(r.headers.get('X-RateLimit-Reset', time.time()))
                time.sleep(reset - int(time.time()) + 10)
                return self.search(q, page, sort)
            return r.json().get('items', []) if r.status_code == 200 else []
        except: return []
    def process_query(self, query: str, sort: str, max_pages: int, target: int,
                     results: list, query_num: int) -> bool:
        for page in range(1, max_pages + 1):
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
            pct = (len(results)/target)*100
            print(f" | New: {new:>3} | Total: {len(results):>6,} ({pct:>5.1f}%)")
            if len(results) >= target: return True
        return False
    def run(self, target: int = 50000):
        already_have = len(self.cloned)
        print("="*90 + f"\n🔍 GitHub ML/DL Repository Searcher\n"
              f"Target: {target:,} new repos | Already have: {already_have:,} "
              f"cloned repos\n" + "="*90 + "\n")
        results, query_num = [], 0
        stars_ranges = [">=500", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"]
        sorts = ["stars", "updated", "forks"]
        for topic in TOPICS:
            for stars in stars_ranges:
                for sort in sorts:
                    queries = [f"language:python topic:{topic} stars:{stars}",
                              f'language:python "{topic}" in:readme stars:{stars}',
                              f'language:python "{topic}" in:description stars:{stars}']
                    for q in queries:
                        query_num += 1
                        if self.process_query(q, sort, 10 if "topic:" in q else 5, target, results, query_num):
                            return self._save(results, already_have)
        if len(results) < target:
            extra_queries = [("filename:model.py", stars_ranges[:6], 3),
                            ("filename:train.py", stars_ranges[:6], 3),
                            ("pytorch", stars_ranges[:4], 3),
                            ("tensorflow", stars_ranges[:4], 3),
                            ('"neural network" OR "machine learning"', stars_ranges[:5], 3),
                            ('"deep learning" OR "artificial intelligence"', stars_ranges[:5], 3)]
            for base_q, star_list, max_p in extra_queries:
                for stars in star_list:
                    for sort in sorts:
                        query_num += 1
                        q = f"language:python {base_q} stars:{stars}"
                        if self.process_query(q, sort, max_p, target, results, query_num):
                            return self._save(results, already_have)
        return self._save(results, already_have)
    def _save(self, results: list, already_have: int):
        existing = []
        if self.output.exists():
            try: existing = json.load(open(self.output, 'r'))
            except: pass
        existing_names = {r.get('full_name') for r in existing}
        new_results = [r for r in results if r['full_name'] not in existing_names]
        json.dump(existing + new_results, open(self.output, 'w'), indent=2)
        json.dump(list(self.seen), open(self.seen_file, 'w'))
        total = already_have + len(new_results)
        print(f"\n{'='*90}\n✅ Search Complete!\n   New unique repos found: "
              f"{len(new_results):,}\n   Already have cloned: {already_have:,}\n"
              f"   Total after cloning: {total:,}\n   Saved to: {self.output}\n{'='*90}")
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get('GITHUB_TOKEN')
    if not token: sys.exit("ERROR: GITHUB_TOKEN not found!")
    GitHubSearcher(token).run(50000)
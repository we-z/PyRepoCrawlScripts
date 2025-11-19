import os, sys, json, time, requests
from pathlib import Path
from dotenv import load_dotenv
from topics import TOPICS

class GitHubSearcher:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"token {token}"}
        base = Path(__file__).parent
        self.output = base / "repos_to_clone.json"
        data_dir = base / "data"
        data_dir.mkdir(exist_ok=True)
        self.seen_file = data_dir / "seen_repos.json"
        self.queries_file = data_dir / "seen_queries.json"
        repos_dir = base / "cloned_repos"
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() 
                      if d.is_dir()} if repos_dir.exists() else set()
        self.seen = set(json.load(open(self.seen_file, 'r'))) if self.seen_file.exists() else set()
        self.seen_queries = set(json.load(open(self.queries_file, 'r'))) if self.queries_file.exists() else set()
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
    def run(self, target):
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
                    for q in [f"language:python topic:{topic} stars:{stars}",
                              f'language:python "{topic}" in:readme stars:{stars}',
                              f'language:python "{topic}" in:description stars:{stars}']:
                        query_key = f"{q}|{sort}"
                        if query_key in self.seen_queries: continue
                        query_num += 1
                        self.process_query(q, sort, 10, target, results, query_num)
                        self.seen_queries.add(query_key)
                        self._save(results, already_have)
                        if len(results) >= target: return
        if len(results) < target:
            for base_q, star_list in [("filename:model.py", stars_ranges[:6]),
                            ("filename:train.py", stars_ranges[:6]), ("pytorch", stars_ranges[:4]),
                            ("tensorflow", stars_ranges[:4]), ('"neural network" OR "machine learning"', stars_ranges[:5]),
                            ('"deep learning" OR "artificial intelligence"', stars_ranges[:5])]:
                for stars in star_list:
                    for sort in sorts:
                        q = f"language:python {base_q} stars:{stars}"
                        query_key = f"{q}|{sort}"
                        if query_key in self.seen_queries: continue
                        query_num += 1
                        self.process_query(q, sort, 10, target, results, query_num)
                        self.seen_queries.add(query_key)
                        self._save(results, already_have)
                        if len(results) >= target: return
    def _save(self, results: list, already_have: int):
        existing = json.load(open(self.output, 'r')) if self.output.exists() else []
        existing_names = {r.get('full_name') for r in existing}
        new_results = [r for r in results if r['full_name'] not in existing_names]
        json.dump(existing + new_results, open(self.output, 'w'), indent=2)
        json.dump(list(self.seen), open(self.seen_file, 'w'))
        json.dump(list(self.seen_queries), open(self.queries_file, 'w'))
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get('GITHUB_TOKEN')
    if not token: sys.exit("ERROR: GITHUB_TOKEN not found!")
    GitHubSearcher(token).run(500000)
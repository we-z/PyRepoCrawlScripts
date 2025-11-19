import os, sys, json, time, requests, re
from pathlib import Path
from topics import TOPICS
class GitHubScraper:
    def __init__(self):
        self.headers = {"User-Agent": "Mozilla/5.0"}
        base = Path(__file__).parent
        self.output = base / "repos_to_clone.json"
        self.seen_file = base / "data" / "seen_repos.json"
        self.seen_file.parent.mkdir(exist_ok=True)
        repos_dir = base / "cloned_repos"
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() 
                      if d.is_dir()} if repos_dir.exists() else set()
        self.seen = set(json.load(open(self.seen_file, 'r'))) if self.seen_file.exists() else set()
    def search(self, q: str, page: int, sort: str) -> list:
        try:
            url = f"https://github.com/search?q={q.replace(' ', '+')}&type=repositories&s={sort}&o=desc&p={page}"
            print(f"\n  URL: {url}")
            r = requests.get(url, headers=self.headers, timeout=30)
            if r.status_code == 429: time.sleep(60); return self.search(q, page, sort)
            if r.status_code != 200: return []
            repos, seen_names = [], set()
            repo_matches = list(re.finditer(r'<div[^>]*search-title[^>]*>.*?href="/([^/]+/[^/"]+)"', r.text, re.DOTALL))
            print(f"  Found {len(repo_matches)} repo matches")
            for match in repo_matches:
                name = match.group(1)
                if name in seen_names or name.count('/') != 1: continue
                context = r.text[max(0, match.start()-200):min(len(r.text), match.end()+3000)]
                stars = 0
                aria_match = re.search(r'aria-label="(\d+)\s+stars"', context)
                if aria_match:
                    stars = int(aria_match.group(1))
                else:
                    star_match = re.search(r'href="/[^"]+/stargazers"[^>]*>.*?<span[^>]*>([\d.]+[kmKM]?)</span>', context, re.DOTALL)
                    if star_match:
                        s = star_match.group(1).lower()
                        stars = int(float(s.replace('k', '')) * 1000) if 'k' in s else int(float(s.replace('m', '')) * 1000000) if 'm' in s else int(float(s))
                if stars > 0 and not any(x in name for x in ['solutions', 'resources', 'topics', 'sponsors']):
                    seen_names.add(name)
                    repos.append({"full_name": name, "clone_url": f"https://github.com/{name}.git", "stars": stars})
            return repos[:10]
        except Exception as e: print(f"  ⚠️  Exception: {e}"); return []
    def process_query(self, query: str, sort: str, max_pages: int, target: int, results: list, query_num: int) -> bool:
        for page in range(1, max_pages + 1):
            print(f"Query {query_num:>4}: {query[:55]:55s} | Sort: {sort:8s} | Page: {page}", end='', flush=True)
            repos_found = self.search(query, page, sort)
            print(f" | Found: {len(repos_found):>3} repos", end='', flush=True)
            if len(repos_found) == 0: print(f" | Skipping remaining pages (0 results)"); break
            new = 0
            for r in repos_found:
                name = r['full_name']
                if name not in self.seen and name not in self.cloned:
                    self.seen.add(name); results.append(r); new += 1
            pct = (len(results)/target)*100
            print(f" | New: {new:>3} | Total: {len(results):>6,} ({pct:>5.1f}%)")
            if len(results) >= target: return True
            time.sleep(2)
        return False
    def run(self, target):
        already_have = len(self.cloned)
        print("="*90 + f"\n🔍 GitHub ML/DL Repository Scraper\n"
              f"Target: {target:,} new repos | Already have: {already_have:,} cloned repos\n" + "="*90 + "\n")
        results, query_num = [], 0
        stars_ranges = [">=10000", "5000..9999", "2000..4999", "1000..1999", "500..999", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"]
        sorts = ["stars", "updated", "forks"]
        for topic in TOPICS:
            for stars in stars_ranges:
                for sort in sorts:
                    queries = [f"language:python topic:{topic} stars:{stars}",
                              f'language:python "{topic}" in:readme stars:{stars}',
                              f'language:python "{topic}" in:description stars:{stars}']
                    for q in queries:
                        query_num += 1
                        if self.process_query(q, sort, 100, target, results, query_num):
                            return self._save(results, already_have)
        if len(results) < target:
            extra_queries = [("filename:model.py", stars_ranges[:6]), ("filename:train.py", stars_ranges[:6]),
                            ("pytorch", stars_ranges[:4]), ("tensorflow", stars_ranges[:4]),
                            ('"neural network" OR "machine learning"', stars_ranges[:5]),
                            ('"deep learning" OR "artificial intelligence"', stars_ranges[:5])]
            for base_q, star_list in extra_queries:
                for stars in star_list:
                    for sort in sorts:
                        query_num += 1
                        if self.process_query(f"language:python {base_q} stars:{stars}", sort, 100, target, results, query_num):
                            return self._save(results, already_have)
        return self._save(results, already_have)
    def _save(self, results: list, already_have: int):
        existing = json.load(open(self.output, 'r')) if self.output.exists() else []
        existing_names = {r.get('full_name') for r in existing}
        new_results = [r for r in results if r['full_name'] not in existing_names]
        json.dump(existing + new_results, open(self.output, 'w'), indent=2)
        json.dump(list(self.seen), open(self.seen_file, 'w'))
        print(f"\n{'='*90}\n✅ Search Complete!\n   New unique repos found: {len(new_results):,}\n"
              f"   Already have cloned: {already_have:,}\n   Total after cloning: {already_have + len(new_results):,}\n"
              f"   Saved to: {self.output}\n{'='*90}")
if __name__ == "__main__":
    GitHubScraper().run(500000)

import os, sys, json, time, asyncio
from pathlib import Path
from dotenv import load_dotenv
from topics import TOPICS
import aiohttp
class GitHubSearcher:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"token {token}"}
        base = Path(__file__).parent
        self.output = base / "repos_to_clone.json"
        data_dir = base / "data"; data_dir.mkdir(exist_ok=True)
        self.seen_file = data_dir / "seen_repos.json"
        self.queries_file = data_dir / "seen_queries.json"
        repos_dir = base / "cloned_repos"
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() if d.is_dir()} if repos_dir.exists() else set()
        self.seen = set(json.load(open(self.seen_file, 'r'))) if self.seen_file.exists() else set()
        self.seen_queries = set(json.load(open(self.queries_file, 'r'))) if self.queries_file.exists() else set()
        self.last_request_time, self.min_interval, self.session = 0, 2.0, None
        self.rate_limit_lock = asyncio.Lock()
    
    async def _wait(self):
        async with self.rate_limit_lock:
            now = time.time()
            if self.last_request_time > 0 and now - self.last_request_time < self.min_interval:
                await asyncio.sleep(self.min_interval - (now - self.last_request_time))
            self.last_request_time = time.time()
    
    async def search(self, q: str, page: int, sort: str) -> list:
        try:
            await self._wait()
            async with self.session.get("https://api.github.com/search/repositories",
                params={"q": q, "page": page, "per_page": 100, "sort": sort},
                timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 403:
                    reset = int(resp.headers.get('X-RateLimit-Reset', time.time()))
                    await asyncio.sleep(max(reset - int(time.time()) + 10, 5))
                    return await self.search(q, page, sort)
                if resp.status != 200: return []
                data = await resp.json()
                return data.get('items', [])
        except: return []
    
    async def process_query(self, query: str, sort: str, target: int, results: list, query_num: int) -> bool:
        for page in range(1, 11):
            print(f"Query {query_num:>4}: {query[:55]:55s} | Sort: {sort:8s} | Page: {page}", end='', flush=True)
            repos_found = await self.search(query, page, sort)
            print(f" | Found: {len(repos_found):>3} repos", end='', flush=True)
            if len(repos_found) == 0:
                print(f" | No more results"); break
            new = 0
            for r in repos_found:
                name = r['full_name']
                if name not in self.seen and name not in self.cloned:
                    self.seen.add(name)
                    results.append({"full_name": name, "clone_url": r['clone_url'], "stars": r.get('stargazers_count', 0)})
                    new += 1
            pct = (len(results)/target)*100
            print(f" | New: {new:>3} | Total: {len(results):>6,} ({pct:>5.1f}%)")
            if len(repos_found) < 100 or len(results) >= target:
                if len(results) >= target: return True
                break
        return False
    
    async def run(self, target):
        already_have = len(self.cloned)
        print("="*90 + f"\n🔍 GitHub ML/DL Repository Searcher\n"
              f"Target: {target:,} new repos | Already have: {already_have:,} cloned repos\n" + "="*90 + "\n")
        results, query_num, stars_ranges, sorts = [], 0, [">=500", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"], ["stars", "updated", "forks"]
        async with aiohttp.ClientSession(headers=self.headers) as session:
            self.session = session
            for topic in TOPICS:
                for stars in stars_ranges:
                    for sort in sorts:
                        for q in [f"language:python topic:{topic} stars:{stars}",
                                  f'language:python "{topic}" in:readme stars:{stars}',
                                  f'language:python "{topic}" in:description stars:{stars}']:
                            query_key = f"{q}|{sort}"
                            if query_key in self.seen_queries: continue
                            query_num += 1
                            await self.process_query(q, sort, target, results, query_num)
                            self.seen_queries.add(query_key)
                            await self._save(results)
                            if len(results) >= target: return
    
    async def _save(self, results: list):
        def _save_sync():
            existing = json.load(open(self.output, 'r')) if self.output.exists() else []
            existing_names = {r.get('full_name') for r in existing}
            new_results = [r for r in results if r['full_name'] not in existing_names]
            json.dump(existing + new_results, open(self.output, 'w'), indent=2)
            json.dump(list(self.seen), open(self.seen_file, 'w'))
            json.dump(list(self.seen_queries), open(self.queries_file, 'w'))
        await asyncio.to_thread(_save_sync)
if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get('GITHUB_TOKEN')
    if not token: sys.exit("ERROR: GITHUB_TOKEN not found!")
    asyncio.run(GitHubSearcher(token).run(500000))
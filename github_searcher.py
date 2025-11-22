import os, sys, json, time, asyncio, aiohttp
from pathlib import Path
from dotenv import load_dotenv
from topics import TOPICS
from datetime import datetime

RATE_LIMIT = 27 # API requests per minute

class GitHubSearcher:
    def __init__(self, token):
        self.headers = {"Authorization": f"token {token}"}
        self.base = Path(__file__).parent
        self.data = self.base / "data"; self.data.mkdir(exist_ok=True)
        self.seen_file, self.queries_file = self.data / "seen_repos.json", self.data / "seen_queries.json"
        self.seen = set(json.load(open(self.seen_file)) if self.seen_file.exists() else [])
        self.cloned = {d.name.replace("_", "/", 1) for d in os.scandir(self.base/"cloned_repos") if d.is_dir()} if (self.base/"cloned_repos").exists() else set()
        self.seen_queries = set(json.load(open(self.queries_file)) if self.queries_file.exists() else [])
        self.req_times = []
        self.lock = None

    async def search(self, session, q, page, sort):
        while True:
            async with self.lock:
                now = time.time()
                self.req_times = [t for t in self.req_times if now - t < 60]
                if len(self.req_times) >= RATE_LIMIT:
                    wait_time = 60 - (now - self.req_times[0]) + 1 if self.req_times else 1
                    wait = True
                else:
                    self.req_times.append(now)
                    wait = False
            
            if wait:
                await asyncio.sleep(wait_time)
                continue

            try:
                async with session.get("https://api.github.com/search/repositories", 
                                     params={"q": q, "page": page, "per_page": 100, "sort": sort},
                                     timeout=aiohttp.ClientTimeout(total=30)) as r:
                    if r.status == 403 or r.status == 429:
                        reset = int(r.headers.get('X-RateLimit-Reset', time.time() + 60))
                        sleep_time = max(reset - time.time(), 30)
                        print(f"\n⚠️ RATE LIMIT HIT! Reset: {reset} (sleeping {sleep_time:.0f}s)")
                        await asyncio.sleep(sleep_time)
                        continue
                    return (await r.json()).get('items', []) if r.status == 200 else []
            except: return []

    async def worker(self, session, queue, results, target):
        while len(results) < target and not queue.empty():
            q, sort, q_num = await queue.get()
            for page in range(1, 11):
                if len(results) >= target: break
                items = await self.search(session, q, page, sort)
                if not items: break
                new_items = [i for i in items if i['full_name'] not in self.seen and i['full_name'] not in self.cloned]
                for i in new_items:
                    self.seen.add(i['full_name'])
                    results.append({"full_name": i['full_name'], "clone_url": i['clone_url'], "stars": i['stargazers_count']})
                
                pct = len(results) / target * 100
                q_print = (q[:75] + '..') if len(q) > 75 else q
                t_str = datetime.now().strftime("%H:%M:%S")
                print(f"{t_str} | QPM: {len(self.req_times):>2} | {q_print:<77} | Sort: {sort:<7} | P{page:<2} | Found: {len(items):>3} | New: {len(new_items):>3} | Total: {len(results):>6,}/{target:,} ({pct:>6.2f}%)")
                
                if len(items) < 100: break
            self.seen_queries.add(f"{q}|{sort}")
            queue.task_done()

    async def run(self, target):
        self.lock = asyncio.Lock()
        results, queue, q_id = [], asyncio.Queue(), 0
        print(f"🔍 Starting search for {target:,} new repos...")
        for t in TOPICS:
            for s in ["stars", "updated", "forks"]:
                for r in [">=500", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9"]:
                    for q in [f"language:python topic:{t} stars:{r}", f'language:python "{t}" in:readme stars:{r}']:
                        if f"{q}|{s}" not in self.seen_queries: queue.put_nowait((q, s, q_id)); q_id += 1
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            await asyncio.gather(*[self.worker(session, queue, results, target) for _ in range(5)])
        
        existing = json.load(open(self.base/"repos_to_clone.json")) if (self.base/"repos_to_clone.json").exists() else []
        json.dump(existing + results, open(self.base/"repos_to_clone.json", 'w'), indent=2)
        json.dump(list(self.seen), open(self.seen_file, 'w')); json.dump(list(self.seen_queries), open(self.queries_file, 'w'))
        print(f"✅ Saved {len(results)} new repos.")

if __name__ == "__main__":
    load_dotenv()
    if not (token := os.environ.get('GITHUB_TOKEN')): sys.exit("ERROR: GITHUB_TOKEN not found!")
    asyncio.run(GitHubSearcher(token).run(500000))
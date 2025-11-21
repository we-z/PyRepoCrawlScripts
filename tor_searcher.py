import asyncio
import atexit
import json
import logging
import os
import random
import re
import shutil
import socket
import subprocess
import sys
import time
import resource
from pathlib import Path
from typing import List, Set, Dict, Optional

import httpx
from dotenv import load_dotenv

# Import TOPICS from topics.py
try:
    from topics import TOPICS
except ImportError:
    sys.exit("Error: Could not import TOPICS from topics.py")

# --- Configuration ---
NUM_INSTANCES = 64
START_SOCKS_PORT = 9050
START_CONTROL_PORT = 9051
TOR_DATA_DIR_BASE = Path("/tmp/tor_data_instances")
MAX_OPEN_FILES = 10000

# Rate limiting
REQUEST_DELAY = 10.0  # Seconds between requests per IP

# User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

# --- Styling ---
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def log(msg, color=Colors.ENDC, end="\n"):
    timestamp = time.strftime("%H:%M:%S")
    print(f"{Colors.BLUE}[{timestamp}]{Colors.ENDC} {color}{msg}{Colors.ENDC}", end=end, flush=True)

# --- Tor Management ---
class TorManager:
    def __init__(self, num_instances=NUM_INSTANCES, start_socks=START_SOCKS_PORT):
        self.num_instances = num_instances
        self.start_socks = start_socks
        self.processes = []
        self.ports = []
        self.tor_cmd = shutil.which("tor")
        
        if not self.tor_cmd:
            # Fallback for Mac Homebrew
            if os.path.exists("/opt/homebrew/bin/tor"):
                self.tor_cmd = "/opt/homebrew/bin/tor"
            else:
                sys.exit(f"{Colors.FAIL}Error: 'tor' executable not found. Please install tor.{Colors.ENDC}")

        # Increase file limits
        try:
            soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
            resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, hard))
        except Exception as e:
            log(f"Warning: Could not increase file limits: {e}", Colors.WARNING)

    def is_port_open(self, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('127.0.0.1', port)) == 0

    def start(self):
        log(f"Initializing {self.num_instances} Tor instances...", Colors.HEADER)
        TOR_DATA_DIR_BASE.mkdir(parents=True, exist_ok=True)
        
        for i in range(self.num_instances):
            socks_port = self.start_socks + (i * 2)
            control_port = socks_port + 1
            data_dir = TOR_DATA_DIR_BASE / f"tor_{socks_port}"
            
            self.ports.append(socks_port)
            
            if self.is_port_open(socks_port):
                log(f"  Instance {i+1}/{self.num_instances}: Port {socks_port} already active. Reusing.", Colors.CYAN)
                continue
                
            data_dir.mkdir(parents=True, exist_ok=True)
            
            cmd = [
                self.tor_cmd,
                "--SocksPort", str(socks_port),
                "--ControlPort", str(control_port),
                "--DataDirectory", str(data_dir),
                "--PidFile", str(data_dir / "tor.pid"),
                "--Log", "notice file /dev/null", # Silence logs
                "--RunAsDaemon", "0"
            ]
            
            try:
                p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                self.processes.append(p)
                log(f"  Instance {i+1}/{self.num_instances}: Started on port {socks_port}", Colors.GREEN)
            except Exception as e:
                log(f"  Instance {i+1}/{self.num_instances}: Failed to start on port {socks_port}: {e}", Colors.FAIL)

        # Wait for instances to bootstrap (simple sleep for now, could be robust)
        if self.processes:
            log("Waiting 15s for Tor instances to bootstrap...", Colors.WARNING)
            time.sleep(15)
            
    def stop(self):
        log("Stopping Tor instances...", Colors.WARNING)
        for p in self.processes:
            try:
                p.terminate()
                p.wait(timeout=2)
            except:
                try:
                    p.kill()
                except:
                    pass
        # Cleanup data dirs? Maybe keep for caching/speed on restart
        # shutil.rmtree(TOR_DATA_DIR_BASE, ignore_errors=True)

# --- Searcher ---
class GitHubTorSearcher:
    def __init__(self):
        self.base = Path(__file__).parent
        self.data_dir = self.base / "data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.output_file = self.base / "repos_to_clone.json"
        self.seen_file = self.data_dir / "seen_repos.json"
        self.queries_file = self.data_dir / "seen_queries.json"
        self.cloned_dir = self.base / "cloned_repos"
        
        # Load state
        self.seen_repos = set()
        if self.seen_file.exists():
            try:
                self.seen_repos = set(json.load(open(self.seen_file)))
            except: pass
            
        self.seen_queries = set()
        if self.queries_file.exists():
            try:
                self.seen_queries = set(json.load(open(self.queries_file)))
            except: pass
            
        self.cloned_repos = set()
        if self.cloned_dir.exists():
            self.cloned_repos = {d.name.replace("_", "/", 1) for d in self.cloned_dir.iterdir() if d.is_dir()}

        self.results = []
        self.lock = asyncio.Lock()
        self.save_lock = asyncio.Lock()
        
        self.tor_manager = TorManager()
        self.queue = asyncio.Queue()
        self.total_queries = 0
        self.completed_queries = 0
        
        # Regex patterns from github_searcher_scraper.py
        self.repo_pattern = re.compile(r'<div[^>]*search-title[^>]*>.*?href="/([^/]+/[^/"]+)"', re.DOTALL)
        self.stars_aria_pattern = re.compile(r'aria-label="(\d+)\s+stars"')
        self.stars_href_pattern = re.compile(r'href="/[^"]+/stargazers"[^>]*>.*?<span[^>]*>([\d.]+[kmKM]?)</span>', re.DOTALL)

    async def save_data(self):
        async with self.save_lock:
            # Load existing to append/merge
            existing = []
            if self.output_file.exists():
                try:
                    existing = json.load(open(self.output_file))
                except: pass
            
            existing_names = {r.get('full_name') for r in existing}
            new_results = [r for r in self.results if r['full_name'] not in existing_names]
            
            if new_results:
                final_list = existing + new_results
                with open(self.output_file, 'w') as f:
                    json.dump(final_list, f, indent=2)
                self.results = [] # Clear memory buffer
                
            with open(self.seen_file, 'w') as f:
                json.dump(list(self.seen_repos), f)
            with open(self.queries_file, 'w') as f:
                json.dump(list(self.seen_queries), f)

    async def worker(self, socks_port, worker_id):
        proxy_url = f"socks5://127.0.0.1:{socks_port}"
        
        # Each worker gets its own client session
        async with httpx.AsyncClient(proxies=proxy_url, timeout=45.0, follow_redirects=True) as client:
            while True:
                try:
                    query_item = await self.queue.get()
                except asyncio.QueueEmpty:
                    break
                    
                if query_item is None:
                    break
                
                query_str, sort, query_num = query_item
                
                # Process query
                log(f"[Worker {worker_id}] Processing Q{query_num}: {query_str[:30]}...", Colors.CYAN)
                
                for page in range(1, 101): # 100 pages
                    start_time = time.time()
                    url = f"https://github.com/search?q={query_str.replace(' ', '+')}&type=repositories&s={sort}&o=desc&p={page}"
                    
                    try:
                        headers = {"User-Agent": random.choice(USER_AGENTS)}
                        resp = await client.get(url, headers=headers)
                        
                        if resp.status_code == 429:
                            log(f"[Worker {worker_id}] Rate limit on port {socks_port}. Sleeping 60s...", Colors.FAIL)
                            await asyncio.sleep(60)
                            # Retry this page? For now, just skip to avoid complex retry logic or infinite loops
                            continue
                            
                        if resp.status_code != 200:
                            log(f"[Worker {worker_id}] Status {resp.status_code} on {url}", Colors.WARNING)
                            break # Stop pagination for this query
                            
                        # Parse
                        text = resp.text
                        matches = self.repo_pattern.finditer(text)
                        found_count = 0
                        new_count = 0
                        
                        for match in matches:
                            found_count += 1
                            name = match.group(1)
                            
                            if name in self.seen_repos or name in self.cloned_repos or name.count('/') != 1:
                                continue
                                
                            # Extract stars
                            context = text[max(0, match.start()-200):min(len(text), match.end()+3000)]
                            stars = 0
                            aria_match = self.stars_aria_pattern.search(context)
                            if aria_match:
                                stars = int(aria_match.group(1))
                            else:
                                star_match = self.stars_href_pattern.search(context)
                                if star_match:
                                    s = star_match.group(1).lower()
                                    if 'k' in s: stars = int(float(s.replace('k', '')) * 1000)
                                    elif 'm' in s: stars = int(float(s.replace('m', '')) * 1000000)
                                    else: stars = int(float(s))
                            
                            # Filter junk
                            if stars > 0 and not any(x in name for x in ['solutions', 'resources', 'topics', 'sponsors']):
                                async with self.lock:
                                    if name not in self.seen_repos:
                                        self.seen_repos.add(name)
                                        self.results.append({
                                            "full_name": name, 
                                            "clone_url": f"https://github.com/{name}.git", 
                                            "stars": stars
                                        })
                                        new_count += 1
                        
                        # Progress Log
                        pct = (self.completed_queries / self.total_queries) * 100 if self.total_queries else 0
                        log(f"[Worker {worker_id}] Q{query_num} P{page} | Found: {found_count} | New: {new_count} | Total Progress: {pct:.2f}%", Colors.ENDC)
                        
                        if found_count == 0:
                            # No results on this page, likely end of results
                            break
                            
                        # Save periodically
                        if len(self.results) > 10:
                            await self.save_data()
                            
                    except Exception as e:
                        log(f"[Worker {worker_id}] Error: {e}", Colors.FAIL)
                        break
                    
                    # Rate limit wait
                    elapsed = time.time() - start_time
                    wait_time = max(0, REQUEST_DELAY - elapsed)
                    await asyncio.sleep(wait_time)
                
                # Query done
                async with self.lock:
                    self.seen_queries.add(f"{query_str}|{sort}")
                    self.completed_queries += 1
                await self.save_data()
                self.queue.task_done()

    async def run(self):
        # Start Tor
        self.tor_manager.start()
        atexit.register(self.tor_manager.stop)
        
        # Generate Queries
        log("Generating queries...", Colors.HEADER)
        stars_ranges = [">=10000", "5000..9999", "2000..4999", "1000..1999", "500..999", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"]
        sorts = ["stars", "updated", "forks"]
        
        query_list = []
        q_num = 0
        for topic in TOPICS:
            for stars in stars_ranges:
                for sort in sorts:
                    for q_template in [
                        f"language:python topic:{topic} stars:{stars}",
                        f'language:python "{topic}" in:readme stars:{stars}',
                        f'language:python "{topic}" in:description stars:{stars}'
                    ]:
                        query_key = f"{q_template}|{sort}"
                        if query_key not in self.seen_queries:
                            q_num += 1
                            query_list.append((q_template, sort, q_num))
        
        self.total_queries = len(query_list)
        log(f"Queued {self.total_queries} queries.", Colors.GREEN)
        
        # Shuffle to distribute load/topics
        random.shuffle(query_list)
        
        for q in query_list:
            self.queue.put_nowait(q)
            
        # Start Workers
        workers = []
        for i, port in enumerate(self.tor_manager.ports):
            w = asyncio.create_task(self.worker(port, i+1))
            workers.append(w)
            
        log(f"Started {len(workers)} workers. Press Ctrl+C to stop.", Colors.HEADER)
        
        try:
            await self.queue.join()
        except KeyboardInterrupt:
            log("\nStopping...", Colors.WARNING)
        finally:
            for w in workers: w.cancel()
            self.tor_manager.stop()
            await self.save_data()

if __name__ == "__main__":
    searcher = GitHubTorSearcher()
    try:
        asyncio.run(searcher.run())
    except KeyboardInterrupt:
        pass

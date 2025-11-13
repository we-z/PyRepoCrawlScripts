#!/usr/bin/env python3
"""
GitHub Python Repository Crawler
Crawls GitHub for Python repositories and builds a 100B+ token dataset
"""

import os
import sys
import json
import time
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import tiktoken
from PIL import Image
import io

class GitHubCrawler:
    """Main crawler class for collecting Python repositories from GitHub"""
    
    def __init__(self, github_token: str, target_tokens: int = 100_000_000_000):
        self.github_token = github_token
        self.target_tokens = target_tokens
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # Directories
        self.base_dir = Path(__file__).parent
        self.repos_dir = self.base_dir / "cloned_repos"
        self.logs_dir = self.base_dir / "logs"
        self.data_dir = self.base_dir / "data"
        
        # Create directories
        self.repos_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Progress tracking
        self.progress_file = self.data_dir / "progress.json"
        self.repos_db_file = self.data_dir / "repos_database.json"
        self.progress = self._load_progress()
        self.repos_db = self._load_repos_db()
        
        # Tokenizer
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        
        # Setup logging
        self._setup_logging()
        
        # Search queries
        self.search_queries = self._generate_search_queries()
        
        self.logger.info("="*80)
        self.logger.info("GitHub Python Repository Crawler Initialized")
        self.logger.info(f"Target tokens: {target_tokens:,}")
        self.logger.info(f"Current tokens collected: {self.progress['total_tokens']:,}")
        self.logger.info(f"Repositories cloned: {self.progress['repos_cloned']}")
        self.logger.info("="*80)
        
        # Check for already-cloned repos and process them
        self._process_existing_repos()
    
    def _setup_logging(self):
        """Setup comprehensive logging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"crawler_{timestamp}.log"
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Setup logger
        self.logger = logging.getLogger('GitHubCrawler')
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"Logging to: {log_file}")
    
    def _load_progress(self) -> Dict:
        """Load progress from disk"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {
            "total_tokens": 0,
            "repos_cloned": 0,
            "repos_failed": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "search_queries_completed": [],
            "current_page": {}
        }
    
    def _load_repos_db(self) -> Dict:
        """Load repository database"""
        if self.repos_db_file.exists():
            with open(self.repos_db_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_progress(self):
        """Save progress to disk"""
        self.progress['last_update'] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
        with open(self.repos_db_file, 'w') as f:
            json.dump(self.repos_db, f, indent=2)
    
    def _process_existing_repos(self):
        """Process any already-cloned repos that aren't in the database"""
        if not self.repos_dir.exists():
            return
        
        existing_dirs = [d for d in self.repos_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        
        if not existing_dirs:
            self.logger.info("No existing cloned repositories found.")
            return
        
        self.logger.info(f"\n🔍 Checking for existing cloned repositories...")
        self.logger.info(f"Found {len(existing_dirs)} directories in cloned_repos/")
        
        new_repos_processed = 0
        for repo_dir in existing_dirs:
            # Convert directory name back to repo name format
            repo_name = repo_dir.name.replace("_", "/", 1)
            
            if repo_name not in self.repos_db:
                self.logger.info(f"📦 Processing existing repo: {repo_name}")
                
                stats = self.process_repository(repo_dir, repo_name)
                
                # Update progress
                self.progress['total_tokens'] += stats['tokens']
                self.progress['repos_cloned'] += 1
                
                # Store in database (without full metadata since we don't have it)
                self.repos_db[repo_name] = {
                    "url": "unknown",
                    "path": str(repo_dir),
                    "stats": stats,
                    "cloned_at": datetime.now().isoformat(),
                    "stars": 0,
                    "forks": 0,
                    "size": 0,
                    "note": "Processed from existing directory"
                }
                
                new_repos_processed += 1
                
        if new_repos_processed > 0:
            self.logger.info(f"✅ Processed {new_repos_processed} existing repos")
            self.logger.info(f"💾 Total tokens now: {self.progress['total_tokens']:,}")
            self._save_progress()
        else:
            self.logger.info("✅ All existing repos already in database")
        
        self.logger.info("")
    
    def _generate_search_queries(self) -> List[Dict]:
        """Generate diverse search queries for Python repositories"""
        queries = []
        
        # Popular Python topics/frameworks
        topics = [
            "machine-learning", "deep-learning", "data-science", "web-scraping",
            "django", "flask", "fastapi", "pytorch", "tensorflow", "numpy",
            "pandas", "scikit-learn", "nlp", "computer-vision", "api",
            "automation", "bot", "web", "cli", "gui", "game", "backend",
            "frontend", "fullstack", "devops", "testing", "scraper",
            "crawler", "parser", "database", "orm", "rest-api", "graphql",
            "microservices", "serverless", "cloud", "aws", "azure", "gcp",
            "docker", "kubernetes", "ci-cd", "blockchain", "crypto",
            "finance", "trading", "analytics", "visualization", "plotting",
            "jupyter", "notebook", "research", "science", "math", "statistics",
            "algorithms", "data-structures", "security", "cryptography",
            "authentication", "oauth", "jwt", "websocket", "async", "asyncio",
            "multiprocessing", "threading", "celery", "redis", "mongodb",
            "postgresql", "mysql", "sqlite", "elasticsearch", "kafka",
            "rabbitmq", "graphql", "grpc", "protobuf", "socket", "networking"
        ]
        
        # Stars-based queries
        star_ranges = [
            ">=1000", ">=500", ">=100", ">=50", ">=10", ">=5", ">=1"
        ]
        
        # Size-based queries (in KB)
        size_ranges = [
            ">=10000", ">=5000", ">=1000", ">=500", ">=100"
        ]
        
        # Generate topic-based queries
        for topic in topics:
            for stars in star_ranges[:3]:  # Use top 3 star ranges
                queries.append({
                    "query": f"language:python topic:{topic} stars:{stars}",
                    "description": f"Python repos about {topic} with {stars} stars"
                })
        
        # Generate star-based queries
        for stars in star_ranges:
            queries.append({
                "query": f"language:python stars:{stars}",
                "description": f"Python repos with {stars} stars"
            })
        
        # Generate size-based queries
        for size in size_ranges:
            queries.append({
                "query": f"language:python size:{size}",
                "description": f"Python repos with size {size} KB"
            })
        
        # Add some general queries
        general_queries = [
            "language:python sort:stars",
            "language:python sort:updated",
            "language:python sort:forks",
            "language:python is:featured",
            "language:python archived:false",
        ]
        
        for gq in general_queries:
            queries.append({
                "query": gq,
                "description": f"General query: {gq}"
            })
        
        self.logger.info(f"Generated {len(queries)} search queries")
        return queries
    
    def search_repositories(self, query: str, page: int = 1, per_page: int = 100) -> Optional[Dict]:
        """Search GitHub repositories"""
        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "page": page,
                "per_page": per_page,
                "sort": "stars",
                "order": "desc"
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 403:
                # Rate limit hit
                reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                wait_time = reset_time - int(time.time()) + 10
                if wait_time > 0:
                    self.logger.warning(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    return self.search_repositories(query, page, per_page)
            else:
                self.logger.error(f"Search failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return None
    
    def clone_repository(self, repo_url: str, repo_name: str, repo_full_name: str) -> Tuple[bool, str]:
        """Clone a repository with live output"""
        repo_path = self.repos_dir / repo_name.replace("/", "_")
        
        # Skip if already cloned
        if repo_full_name in self.repos_db:
            self.logger.info(f"⏭️  SKIP: {repo_full_name} (already processed)")
            return False, str(repo_path)
        
        if repo_path.exists():
            self.logger.info(f"📁 EXISTS: {repo_path} - removing old version")
            shutil.rmtree(repo_path)
        
        try:
            self.logger.info(f"🔄 CLONING: {repo_full_name}")
            self.logger.info(f"   URL: {repo_url}")
            self.logger.info(f"   Path: {repo_path}")
            
            # Clone with progress
            process = subprocess.Popen(
                ["git", "clone", "--depth", "1", "--quiet", repo_url, str(repo_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.logger.info(f"✅ CLONED: {repo_full_name}")
                return True, str(repo_path)
            else:
                self.logger.error(f"❌ FAILED: {repo_full_name}")
                if stderr:
                    self.logger.error(f"   Error: {stderr.strip()}")
                return False, str(repo_path)
                
        except Exception as e:
            self.logger.error(f"❌ CLONE ERROR: {repo_full_name} - {e}")
            return False, str(repo_path)
    
    def count_tokens_in_file(self, file_path: Path) -> int:
        """Count tokens in a file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Allow special tokens to be encoded as normal text
                tokens = self.tokenizer.encode(content, disallowed_special=())
                return len(tokens)
        except Exception as e:
            self.logger.debug(f"Token count error for {file_path}: {e}")
            return 0
    
    def compress_image(self, image_path: Path):
        """Compress an image file"""
        try:
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (800, 800)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save with compression
                img.save(image_path, optimize=True, quality=70)
                
        except Exception as e:
            self.logger.debug(f"Image compression error for {image_path}: {e}")
    
    def process_repository(self, repo_path: Path, repo_full_name: str) -> Dict:
        """Process a cloned repository"""
        stats = {
            "total_files": 0,
            "python_files": 0,
            "tokens": 0,
            "size_bytes": 0,
            "images_compressed": 0,
            "files_processed": 0
        }
        
        self.logger.info(f"📊 PROCESSING: {repo_full_name}")
        
        # Extensions to count tokens
        code_extensions = {'.py', '.pyx', '.pyi', '.pyw', '.ipynb'}
        text_extensions = {'.txt', '.md', '.rst', '.json', '.yaml', '.yml', '.toml', '.cfg', '.ini'}
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
        
        try:
            for file_path in repo_path.rglob('*'):
                if file_path.is_file():
                    stats["total_files"] += 1
                    file_size = file_path.stat().st_size
                    stats["size_bytes"] += file_size
                    
                    ext = file_path.suffix.lower()
                    
                    # Process Python and text files for tokens
                    if ext in code_extensions or ext in text_extensions:
                        tokens = self.count_tokens_in_file(file_path)
                        stats["tokens"] += tokens
                        stats["files_processed"] += 1
                        
                        if ext in code_extensions:
                            stats["python_files"] += 1
                    
                    # Compress images
                    elif ext in image_extensions:
                        self.compress_image(file_path)
                        stats["images_compressed"] += 1
            
            self.logger.info(f"   Files: {stats['total_files']:,} | Python: {stats['python_files']:,}")
            self.logger.info(f"   Tokens: {stats['tokens']:,} | Size: {stats['size_bytes']:,} bytes")
            self.logger.info(f"   Images compressed: {stats['images_compressed']}")
            
        except Exception as e:
            self.logger.error(f"Processing error for {repo_full_name}: {e}")
        
        return stats
    
    def run(self):
        """Main execution loop"""
        self.logger.info("\n" + "="*80)
        self.logger.info("🚀 STARTING CRAWL")
        self.logger.info("="*80 + "\n")
        
        query_index = 0
        
        try:
            while self.progress['total_tokens'] < self.target_tokens:
                # Get next query
                if query_index >= len(self.search_queries):
                    self.logger.info("🔄 Cycling back to beginning of search queries")
                    query_index = 0
                
                query_info = self.search_queries[query_index]
                query = query_info['query']
                
                # Check if query was already completed
                if query in self.progress['search_queries_completed']:
                    query_index += 1
                    continue
                
                progress_pct = (self.progress['total_tokens'] / self.target_tokens) * 100
                self.logger.info("\n" + "="*80)
                self.logger.info(f"🔍 SEARCH QUERY #{query_index + 1}: {query}")
                self.logger.info(f"   Description: {query_info['description']}")
                self.logger.info(f"   Current Progress: {progress_pct:.3f}% ({self.progress['total_tokens']:,} tokens)")
                self.logger.info("="*80)
                
                # Get current page for this query
                page = self.progress['current_page'].get(query, 1)
                
                # Search repositories
                results = self.search_repositories(query, page=page)
                
                if not results or 'items' not in results:
                    self.logger.warning(f"No results for query: {query}")
                    self.progress['search_queries_completed'].append(query)
                    query_index += 1
                    continue
                
                repos = results['items']
                total_count = results.get('total_count', 0)
                
                self.logger.info(f"   Found: {len(repos)} repos on page {page} (Total: {total_count:,})")
                
                if not repos:
                    # No more results for this query
                    self.progress['search_queries_completed'].append(query)
                    if query in self.progress['current_page']:
                        del self.progress['current_page'][query]
                    query_index += 1
                    continue
                
                # Process each repository
                for repo in repos:
                    repo_name = repo['full_name']
                    repo_url = repo['clone_url']
                    
                    # Clone repository
                    success, repo_path = self.clone_repository(repo_url, repo_name, repo_name)
                    
                    if success:
                        # Process repository
                        stats = self.process_repository(Path(repo_path), repo_name)
                        
                        # Update progress
                        self.progress['total_tokens'] += stats['tokens']
                        self.progress['repos_cloned'] += 1
                        
                        # Store in database
                        self.repos_db[repo_name] = {
                            "url": repo_url,
                            "path": repo_path,
                            "stats": stats,
                            "cloned_at": datetime.now().isoformat(),
                            "stars": repo.get('stargazers_count', 0),
                            "forks": repo.get('forks_count', 0),
                            "size": repo.get('size', 0)
                        }
                        
                        # Save progress
                        self._save_progress()
                        
                        # Show updated stats
                        self._show_inline_stats()
                        
                        self.logger.info("")
                        
                        # Check if target reached
                        if self.progress['total_tokens'] >= self.target_tokens:
                            self.logger.info("\n" + "="*80)
                            self.logger.info("🎉 TARGET REACHED!")
                            self.logger.info("="*80 + "\n")
                            break
                    else:
                        self.progress['repos_failed'] += 1
                        self._save_progress()
                    
                    # Small delay to avoid hammering
                    time.sleep(1)
                
                # Move to next page
                self.progress['current_page'][query] = page + 1
                self._save_progress()
                
                # Check if we should move to next query (GitHub limits to 1000 results)
                if page >= 10:  # 10 pages * 100 per page = 1000 repos
                    self.progress['search_queries_completed'].append(query)
                    if query in self.progress['current_page']:
                        del self.progress['current_page'][query]
                    query_index += 1
        
        except KeyboardInterrupt:
            self.logger.info("\n⚠️  Interrupted by user. Saving progress...")
            self._save_progress()
            self.logger.info("✅ Progress saved. You can resume later.")
        
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self._save_progress()
        
        finally:
            self._print_final_stats()
    
    def _show_inline_stats(self):
        """Show inline statistics after each repo"""
        progress_pct = (self.progress['total_tokens'] / self.target_tokens) * 100
        
        # Calculate totals
        total_size = sum(repo['stats']['size_bytes'] for repo in self.repos_db.values())
        total_py_files = sum(repo['stats']['python_files'] for repo in self.repos_db.values())
        
        # Calculate time-based stats
        start_time = datetime.fromisoformat(self.progress['start_time'])
        elapsed = datetime.now() - start_time
        elapsed_seconds = elapsed.total_seconds()
        
        if elapsed_seconds > 0:
            tokens_per_sec = self.progress['total_tokens'] / elapsed_seconds
            repos_per_min = (self.progress['repos_cloned'] / elapsed_seconds) * 60
        else:
            tokens_per_sec = 0
            repos_per_min = 0
        
        self.logger.info("┌" + "─"*78 + "┐")
        self.logger.info(f"│ 📊 CURRENT STATISTICS{' '*56}│")
        self.logger.info("├" + "─"*78 + "┤")
        self.logger.info(f"│ 🎯 Progress:      {self.progress['total_tokens']:>15,} / {self.target_tokens:,} tokens ({progress_pct:>6.3f}%) │")
        self.logger.info(f"│ 📦 Repos:         {self.progress['repos_cloned']:>6,} cloned  |  {self.progress['repos_failed']:>6,} failed{' '*21}│")
        self.logger.info(f"│ 📁 Python Files:  {total_py_files:>15,} files{' '*35}│")
        self.logger.info(f"│ 💾 Disk Usage:    {total_size / (1024**3):>15.2f} GB{' '*38}│")
        self.logger.info(f"│ ⚡ Speed:         {tokens_per_sec:>15,.0f} tokens/sec  ({repos_per_min:>5.1f} repos/min){' '*8}│")
        self.logger.info(f"│ ⏱️  Elapsed:       {str(elapsed).split('.')[0]:>20s}{' '*34}│")
        
        # Estimate completion time
        if tokens_per_sec > 0:
            remaining_tokens = self.target_tokens - self.progress['total_tokens']
            remaining_seconds = remaining_tokens / tokens_per_sec
            remaining_days = remaining_seconds / 86400
            remaining_hours = (remaining_seconds % 86400) / 3600
            
            if remaining_days >= 1:
                eta_str = f"{remaining_days:.1f} days"
            elif remaining_hours >= 1:
                eta_str = f"{remaining_hours:.1f} hours"
            else:
                eta_str = f"{remaining_seconds/60:.1f} minutes"
            
            self.logger.info(f"│ 🕐 Est. Time:     {eta_str:>20s}{' '*34}│")
        
        self.logger.info("└" + "─"*78 + "┘")
    
    def _print_final_stats(self):
        """Print final statistics"""
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 FINAL STATISTICS")
        self.logger.info("="*80)
        self.logger.info(f"Total tokens collected: {self.progress['total_tokens']:,}")
        self.logger.info(f"Target tokens: {self.target_tokens:,}")
        self.logger.info(f"Progress: {(self.progress['total_tokens']/self.target_tokens*100):.2f}%")
        self.logger.info(f"Repositories cloned: {self.progress['repos_cloned']}")
        self.logger.info(f"Repositories failed: {self.progress['repos_failed']}")
        self.logger.info(f"Search queries completed: {len(self.progress['search_queries_completed'])}")
        
        # Calculate total size
        total_size = sum(repo['stats']['size_bytes'] for repo in self.repos_db.values())
        self.logger.info(f"Total size: {total_size / (1024**3):.2f} GB")
        
        # Calculate total Python files
        total_py_files = sum(repo['stats']['python_files'] for repo in self.repos_db.values())
        self.logger.info(f"Total Python files: {total_py_files:,}")
        
        self.logger.info("="*80)


def main():
    """Main entry point"""
    # GitHub token must be passed as environment variable
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        print("ERROR: GITHUB_TOKEN environment variable not set!")
        print("Please set it with: export GITHUB_TOKEN='your_token_here'")
        sys.exit(1)
    
    # Target: 100 billion tokens
    target_tokens = 100_000_000_000
    
    # Create and run crawler
    crawler = GitHubCrawler(github_token, target_tokens)
    crawler.run()


if __name__ == "__main__":
    main()


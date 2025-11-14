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
from dotenv import load_dotenv

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
        self.seen_repos_file = self.data_dir / "seen_repos.json"
        self.progress = self._load_progress()
        self.repos_db = self._load_repos_db()
        self.seen_repos = self._load_seen_repos()  # Track all repos we've encountered
        
        # Search threshold management
        self.current_min_stars = self.progress.get('current_min_stars', 5000)
        self.star_threshold_levels = [5000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 1]
        
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
        
        # Save progress immediately to persist any migrations
        self._save_progress()
        
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
        default_progress = {
            "total_tokens": 0,
            "repos_cloned": 0,
            "repos_failed": 0,
            "repos_skipped": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat(),
            "search_queries_completed": [],
            "current_page": {},
            "current_min_stars": 5000,
            "threshold_expansions": 0
        }
        
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                loaded_progress = json.load(f)
            
            # Migrate old progress files - add any missing fields
            for key, default_value in default_progress.items():
                if key not in loaded_progress:
                    loaded_progress[key] = default_value
            
            return loaded_progress
        
        return default_progress
    
    def _load_repos_db(self) -> Dict:
        """Load repository database"""
        if self.repos_db_file.exists():
            with open(self.repos_db_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _load_seen_repos(self) -> set:
        """Load set of all repo IDs we've seen in search results"""
        if self.seen_repos_file.exists():
            with open(self.seen_repos_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def _save_progress(self):
        """Save progress to disk"""
        self.progress['last_update'] = datetime.now().isoformat()
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
        with open(self.repos_db_file, 'w') as f:
            json.dump(self.repos_db, f, indent=2)
        with open(self.seen_repos_file, 'w') as f:
            json.dump(list(self.seen_repos), f, indent=2)
    
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
        """Generate diverse search queries for ML/DL Python repositories"""
        queries = []
        
        # ML/DL focused topics only
        ml_topics = [
            "machine-learning", "deep-learning", "neural-network", "pytorch", 
            "tensorflow", "keras", "scikit-learn", "nlp", "natural-language-processing",
            "computer-vision", "image-processing", "object-detection", "segmentation",
            "reinforcement-learning", "generative-ai", "transformers", "llm",
            "large-language-model", "diffusion", "gan", "vae", "autoencoder",
            "classification", "regression", "clustering", "data-science",
            "kaggle", "model-training", "neural-networks", "convolutional-neural-network",
            "recurrent-neural-network", "lstm", "gru", "attention-mechanism",
            "bert", "gpt", "stable-diffusion", "yolo", "resnet", "vgg",
            "image-classification", "semantic-segmentation", "instance-segmentation",
            "face-recognition", "speech-recognition", "audio-processing",
            "time-series", "forecasting", "anomaly-detection", "recommendation-system",
            "embeddings", "feature-extraction", "transfer-learning", "fine-tuning",
            "hyperparameter-tuning", "model-optimization", "quantization",
            "onnx", "tensorrt", "model-compression", "pruning",
            "active-learning", "semi-supervised-learning", "self-supervised-learning",
            "meta-learning", "few-shot-learning", "zero-shot-learning",
            "graph-neural-network", "gnn", "knowledge-graph", "multimodal",
            "vision-transformer", "clip", "dalle", "whisper", "chatbot",
            "text-generation", "text-classification", "sentiment-analysis",
            "named-entity-recognition", "question-answering", "summarization",
            "translation", "optical-character-recognition", "ocr",
            "pose-estimation", "tracking", "video-analysis", "3d-vision"
        ]
        
        # Create EXCLUSIVE star ranges based on current threshold
        # This prevents seeing the same repos over and over
        all_thresholds = [5000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 1]
        
        # Find where we are in the threshold progression
        try:
            current_index = all_thresholds.index(self.current_min_stars)
        except ValueError:
            current_index = 0
        
        # Create exclusive ranges: 2000-4999, 1000-1999, 500-999, etc.
        star_ranges = []
        for i in range(current_index, len(all_thresholds)):
            min_stars = all_thresholds[i]
            if i > 0:
                max_stars = all_thresholds[i-1] - 1
                star_ranges.append({
                    "query": f"{min_stars}..{max_stars}",
                    "desc": f"{min_stars}-{max_stars}"
                })
            else:
                # Top tier has no upper limit
                star_ranges.append({
                    "query": f">={min_stars}",
                    "desc": f"{min_stars}+"
                })
        
        # Multiple sort orders to get diverse repos
        sort_orders = [
            ("stars", "desc", "most stars"),
            ("updated", "desc", "recently updated"),
            ("forks", "desc", "most forks"),
        ]
        
        # Generate topic + star + sort queries
        for topic in ml_topics:
            for star_range in star_ranges[:3]:  # Use top 3 star ranges for each topic
                for sort, order, sort_desc in sort_orders:
                    queries.append({
                        "query": f"language:python topic:{topic} stars:{star_range['query']}",
                        "description": f"ML/DL: {topic} ({star_range['desc']} stars, {sort_desc})",
                        "sort": sort,
                        "order": order
                    })
        
        # Add recent repos (last 2 years) across different star ranges
        recent_date = "2023-01-01"
        for topic in ml_topics[:15]:  # Top 15 topics
            # Different star ranges for recent repos
            for star_range in star_ranges[:2]:
                queries.append({
                    "query": f"language:python topic:{topic} stars:{star_range['query']} pushed:>{recent_date}",
                    "description": f"Recent: {topic} ({star_range['desc']} stars, updated 2023+)",
                    "sort": "updated",
                    "order": "desc"
                })
        
        # Broad ML/DL queries with exclusive ranges and multiple sorts
        broad_topics = [
            "machine-learning", "deep-learning", "artificial-intelligence",
            "pytorch", "tensorflow", "computer-vision", "nlp", "transformers"
        ]
        
        for broad_topic in broad_topics:
            for star_range in star_ranges[:3]:
                for sort, order, sort_desc in sort_orders:
                    queries.append({
                        "query": f"language:python {broad_topic} stars:{star_range['query']}",
                        "description": f"Broad: {broad_topic} ({star_range['desc']} stars, {sort_desc})",
                        "sort": sort,
                        "order": order
                    })
        
        # Add created date-based queries to find repos by AGE
        years = ["2024", "2023", "2022", "2021", "2020", "2019"]
        core_topics = ["machine-learning", "deep-learning", "pytorch", "tensorflow", "transformers"]
        
        for year in years:
            for topic in core_topics:
                for star_range in star_ranges[:2]:  # Top 2 ranges
                    queries.append({
                        "query": f"language:python {topic} stars:{star_range['query']} created:{year}",
                        "description": f"Year {year}: {topic} ({star_range['desc']} stars)",
                        "sort": "stars",
                        "order": "desc"
                    })
        
        # Add "in:readme" searches for specific ML/DL keywords
        readme_keywords = [
            "neural network", "machine learning", "deep learning", "transformer",
            "CNN", "RNN", "LSTM", "GAN", "VAE", "reinforcement learning",
            "computer vision", "NLP", "image classification", "object detection"
        ]
        
        for keyword in readme_keywords:
            for star_range in star_ranges[:2]:
                queries.append({
                    "query": f'language:python "{keyword}" in:readme stars:{star_range["query"]}',
                    "description": f'README: "{keyword}" ({star_range["desc"]} stars)',
                    "sort": "stars",
                    "order": "desc"
                })
        
        # Add license-based queries (different licenses attract different types of projects)
        licenses = ["mit", "apache-2.0", "gpl-3.0", "bsd-3-clause"]
        for license_type in licenses:
            for star_range in star_ranges[:2]:
                queries.append({
                    "query": f"language:python machine-learning stars:{star_range['query']} license:{license_type}",
                    "description": f"License {license_type}: ML ({star_range['desc']} stars)",
                    "sort": "stars",
                    "order": "desc"
                })
        
        # Size-based queries to catch large repos that might have been missed
        size_ranges = [">=50000", ">=20000", ">=10000", ">=5000"]
        for size in size_ranges:
            for sort, order, sort_desc in sort_orders[:2]:  # stars and updated
                queries.append({
                    "query": f"language:python machine-learning size:{size}",
                    "description": f"Large repos: size {size}KB ({sort_desc})",
                    "sort": sort,
                    "order": order
                })
        
        # Language + filename queries (catches repos without proper topics)
        filenames = ["train.py", "model.py", "inference.py", "dataset.py", "network.py"]
        for filename in filenames:
            for star_range in star_ranges[:2]:
                queries.append({
                    "query": f"language:python filename:{filename} stars:{star_range['query']}",
                    "description": f"Filename {filename} ({star_range['desc']} stars)",
                    "sort": "stars",
                    "order": "desc"
                })
        
        # Archived vs active repos (sometimes archived repos have great code)
        for star_range in star_ranges[:2]:
            queries.append({
                "query": f"language:python machine-learning stars:{star_range['query']} archived:true",
                "description": f"Archived ML repos ({star_range['desc']} stars)",
                "sort": "stars",
                "order": "desc"
            })
            queries.append({
                "query": f"language:python deep-learning stars:{star_range['query']} archived:true",
                "description": f"Archived DL repos ({star_range['desc']} stars)",
                "sort": "stars",
                "order": "desc"
            })
        
        self.logger.info(f"Generated {len(queries)} ML/DL-focused search queries (min stars: {self.current_min_stars})")
        return queries
    
    def search_repositories(self, query: str, page: int = 1, per_page: int = 100, 
                          sort: str = "stars", order: str = "desc") -> Optional[Dict]:
        """Search GitHub repositories"""
        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "page": page,
                "per_page": per_page,
                "sort": sort,
                "order": order
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
    
    def clone_repository(self, repo_url: str, repo_name: str, repo_full_name: str) -> Tuple[bool, str, bool]:
        """Clone a repository with live output
        
        Returns:
            Tuple[bool, str, bool]: (success, path, was_skipped)
        """
        repo_path = self.repos_dir / repo_name.replace("/", "_")
        
        # Skip if already cloned
        if repo_full_name in self.repos_db:
            return False, str(repo_path), True  # Indicate it was skipped
        
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
                return True, str(repo_path), False
            else:
                self.logger.error(f"❌ FAILED: {repo_full_name}")
                if stderr:
                    self.logger.error(f"   Error: {stderr.strip()}")
                return False, str(repo_path), False
                
        except Exception as e:
            self.logger.error(f"❌ CLONE ERROR: {repo_full_name} - {e}")
            return False, str(repo_path), False
    
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
            cycles_without_progress = 0
            max_empty_cycles = 2
            
            while self.progress['total_tokens'] < self.target_tokens:
                # Get next query
                if query_index >= len(self.search_queries):
                    cycles_without_progress += 1
                    
                    if cycles_without_progress >= max_empty_cycles:
                        # Check if we can lower the star threshold
                        if self._can_expand_search():
                            self.logger.info("\n" + "="*80)
                            self.logger.info("🔽 EXPANDING SEARCH - LOWERING STAR THRESHOLD")
                            self.logger.info("="*80)
                            
                            old_threshold = self.current_min_stars
                            new_threshold = self._expand_search()
                            
                            self.logger.info(f"Star threshold: {old_threshold} → {new_threshold}")
                            self.logger.info(f"This will search for repos with {new_threshold}+ stars")
                            self.logger.info("Resetting completed queries to search with new threshold...")
                            
                            # Reset search state
                            self.progress['search_queries_completed'] = []
                            self.progress['current_page'] = {}
                            self.progress['current_min_stars'] = new_threshold
                            self.progress['threshold_expansions'] = self.progress.get('threshold_expansions', 0) + 1
                            self.current_min_stars = new_threshold
                            
                            # Regenerate queries with new threshold
                            self.search_queries = self._generate_search_queries()
                            
                            self._save_progress()
                            
                            self.logger.info(f"✅ Generated {len(self.search_queries)} new queries")
                            self.logger.info("🚀 Continuing crawl with expanded search...")
                            self.logger.info("="*80 + "\n")
                            
                            # Reset counters and continue
                            cycles_without_progress = 0
                            query_index = 0
                            continue
                        else:
                            # No more thresholds to try
                            self.logger.info("\n" + "="*80)
                            self.logger.info("🏁 SEARCH FULLY EXHAUSTED")
                            self.logger.info("="*80)
                            self.logger.info(f"Completed {len(self.progress['search_queries_completed'])} queries")
                            self.logger.info(f"Threshold expansions: {self.progress.get('threshold_expansions', 0)}")
                            self.logger.info(f"Reached minimum star threshold: {self.current_min_stars}")
                            self.logger.info("\nAll available ML/DL repositories have been processed.")
                            self.logger.info("\nOptions to continue:")
                            self.logger.info("1. Wait for new repos to be created on GitHub")
                            self.logger.info("2. Manually edit threshold_levels to go even lower")
                            self.logger.info("3. Add more search topics to _generate_search_queries()")
                            self.logger.info("="*80)
                            break
                    
                    self.logger.info("🔄 Cycling back to beginning of search queries")
                    query_index = 0
                
                query_info = self.search_queries[query_index]
                query = query_info['query']
                sort = query_info.get('sort', 'stars')
                order = query_info.get('order', 'desc')
                
                # Check if query was already completed
                if query in self.progress['search_queries_completed']:
                    query_index += 1
                    continue
                
                # Reset cycle counter when we find a query to process
                cycles_without_progress = 0
                
                progress_pct = (self.progress['total_tokens'] / self.target_tokens) * 100
                self.logger.info("\n" + "="*80)
                self.logger.info(f"🔍 SEARCH QUERY #{query_index + 1}: {query}")
                self.logger.info(f"   Description: {query_info['description']}")
                self.logger.info(f"   Sort: {sort} ({order})")
                self.logger.info(f"   Current Progress: {progress_pct:.3f}% ({self.progress['total_tokens']:,} tokens)")
                self.logger.info("="*80)
                
                # Get current page for this query
                page = self.progress['current_page'].get(query, 1)
                
                # Search repositories
                results = self.search_repositories(query, page=page, sort=sort, order=order)
                
                if not results or 'items' not in results:
                    self.logger.warning(f"No results for query: {query}")
                    self.progress['search_queries_completed'].append(query)
                    query_index += 1
                    continue
                
                repos = results['items']
                total_count = results.get('total_count', 0)
                
                # Filter out repos we've already seen
                new_repos = []
                for repo in repos:
                    repo_id = str(repo['id'])
                    if repo_id not in self.seen_repos:
                        new_repos.append(repo)
                        self.seen_repos.add(repo_id)
                
                skipped_count = len(repos) - len(new_repos)
                
                self.logger.info(f"   Found: {len(repos)} repos on page {page} (Total available: {total_count:,})")
                if skipped_count > 0:
                    self.logger.info(f"   Filtered: {len(new_repos)} new, {skipped_count} already seen")
                
                if not new_repos:
                    # Try next page before giving up on this query
                    if page < 5 and len(repos) > 0:  # Try up to 5 pages
                        self.logger.info(f"   No new repos on page {page}, trying page {page + 1}...")
                        self.progress['current_page'][query] = page + 1
                        self._save_progress()
                        continue  # Stay on same query, next page
                    
                    # No new results even after trying multiple pages, move to next query
                    self.logger.info(f"   No new repos found after {page} pages, moving to next query")
                    if query not in self.progress['search_queries_completed']:
                        self.progress['search_queries_completed'].append(query)
                    if query in self.progress['current_page']:
                        del self.progress['current_page'][query]
                    self._save_progress()
                    query_index += 1
                    continue
                
                # Process each repository
                repos_processed_this_batch = 0
                for repo in new_repos:
                    repo_name = repo['full_name']
                    repo_url = repo['clone_url']
                    
                    # Clone repository
                    success, repo_path, was_skipped = self.clone_repository(repo_url, repo_name, repo_name)
                    
                    if was_skipped:
                        # Already processed, don't count as failed
                        self.progress['repos_skipped'] += 1
                        continue
                    
                    if success:
                        # Process repository
                        stats = self.process_repository(Path(repo_path), repo_name)
                        
                        # Update progress
                        self.progress['total_tokens'] += stats['tokens']
                        self.progress['repos_cloned'] += 1
                        repos_processed_this_batch += 1
                        
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
                        # Actual failure (clone error, etc)
                        self.progress['repos_failed'] += 1
                        self._save_progress()
                    
                    # Small delay to avoid hammering
                    time.sleep(1)
                
                # Move to next page
                self.progress['current_page'][query] = page + 1
                self._save_progress()
                
                # Check if we should move to next query (GitHub limits to 1000 results)
                if page >= 10:  # 10 pages * 100 per page = 1000 repos
                    if query not in self.progress['search_queries_completed']:
                        self.progress['search_queries_completed'].append(query)
                    if query in self.progress['current_page']:
                        del self.progress['current_page'][query]
                    self._save_progress()
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
        self.logger.info(f"│ ⏭️  Skipped:       {self.progress.get('repos_skipped', 0):>6,} already processed{' '*39}│")
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
    
    def _can_expand_search(self) -> bool:
        """Check if we can lower the star threshold"""
        try:
            current_index = self.star_threshold_levels.index(self.current_min_stars)
            return current_index < len(self.star_threshold_levels) - 1
        except ValueError:
            return False
    
    def _expand_search(self) -> int:
        """Lower the star threshold to the next level"""
        try:
            current_index = self.star_threshold_levels.index(self.current_min_stars)
            if current_index < len(self.star_threshold_levels) - 1:
                return self.star_threshold_levels[current_index + 1]
        except ValueError:
            pass
        return self.current_min_stars
    
    def _print_final_stats(self):
        """Print final statistics"""
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 FINAL STATISTICS")
        self.logger.info("="*80)
        self.logger.info(f"Total tokens collected: {self.progress['total_tokens']:,}")
        self.logger.info(f"Target tokens: {self.target_tokens:,}")
        self.logger.info(f"Progress: {(self.progress['total_tokens']/self.target_tokens*100):.2f}%")
        self.logger.info(f"Repositories cloned: {self.progress['repos_cloned']}")
        self.logger.info(f"Repositories failed (actual): {self.progress['repos_failed']}")
        self.logger.info(f"Repositories skipped (already processed): {self.progress.get('repos_skipped', 0)}")
        self.logger.info(f"Search queries completed: {len(self.progress['search_queries_completed'])}")
        self.logger.info(f"Threshold expansions: {self.progress.get('threshold_expansions', 0)}")
        self.logger.info(f"Final star threshold: {self.progress.get('current_min_stars', 5000)}")
        
        # Calculate total size
        total_size = sum(repo['stats']['size_bytes'] for repo in self.repos_db.values())
        self.logger.info(f"Total size: {total_size / (1024**3):.2f} GB")
        
        # Calculate total Python files
        total_py_files = sum(repo['stats']['python_files'] for repo in self.repos_db.values())
        self.logger.info(f"Total Python files: {total_py_files:,}")
        
        self.logger.info("="*80)


def main():
    """Main entry point"""
    # Load environment variables from .env file
    load_dotenv()
    
    # GitHub token must be set as environment variable or in .env file
    github_token = os.environ.get('GITHUB_TOKEN')
    
    if not github_token:
        print("ERROR: GITHUB_TOKEN not found!")
        print("Please either:")
        print("  1. Create a .env file with: GITHUB_TOKEN='your_token_here'")
        print("  2. Or set environment variable: export GITHUB_TOKEN='your_token_here'")
        sys.exit(1)
    
    # Target: 100 billion tokens
    target_tokens = 100_000_000_000
    
    # Create and run crawler
    crawler = GitHubCrawler(github_token, target_tokens)
    crawler.run()


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Git Repository Cloner
Clones repos from repos_to_clone.json and purges non-code files
"""

import os
import sys
import json
import shutil
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict

class GitCloner:
    """Clone repositories and purge non-code files"""
    
    # Extensions to KEEP
    CODE_EXTENSIONS = {
        '.py', '.pyx', '.pyi', '.pyw', '.ipynb',
        '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', 
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.jl',
        '.sh', '.bash', '.zsh', '.fish',
    }
    
    TEXT_EXTENSIONS = {
        '.md', '.rst', '.txt',
        '.json', '.yaml', '.yml', '.toml', '.xml', '.cfg', '.ini', '.conf',
        '.csv', '.tsv',
        '.html', '.css', '.scss', '.sass', '.less',
        '.lock', '.requirements',
        '.gitignore', '.gitattributes', '.editorconfig', '.env',
    }
    
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.repos_dir = self.base_dir / "cloned_repos"
        self.repos_dir.mkdir(exist_ok=True)
        
        self.input_file = self.base_dir / "repos_to_clone.json"
        self.cloned_file = self.base_dir / "repos_cloned.json"
        
        self.cloned_repos = self._load_cloned()
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        formatter = logging.Formatter('%(asctime)s | %(message)s', datefmt='%H:%M:%S')
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        self.logger = logging.getLogger('GitCloner')
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)
    
    def _load_cloned(self) -> set:
        """Load already cloned repos"""
        if self.cloned_file.exists():
            with open(self.cloned_file, 'r') as f:
                return set(json.load(f))
        return set()
    
    def _save_cloned(self):
        """Save cloned repos list"""
        with open(self.cloned_file, 'w') as f:
            json.dump(list(self.cloned_repos), f, indent=2)
    
    def clone_repository(self, repo_url: str, repo_name: str) -> bool:
        """Clone a repository with live progress"""
        repo_path = self.repos_dir / repo_name.replace("/", "_")
        
        if repo_path.exists():
            shutil.rmtree(repo_path)
        
        try:
            # Clone with progress
            process = subprocess.Popen(
                ["git", "clone", "--depth", "1", "--progress", repo_url, str(repo_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            # Show git progress on same line
            print("   ", end='', flush=True)
            
            for line in process.stderr:
                line = line.strip()
                if not line:
                    continue
                
                if 'Counting objects' in line or 'Receiving objects' in line or 'Resolving deltas' in line:
                    if 'done' in line.lower():
                        print(f"\r   {line}")
                    else:
                        print(f"\r   {line}", end='', flush=True)
            
            print()
            process.wait()
            
            return process.returncode == 0
                
        except Exception as e:
            self.logger.error(f"   Clone error: {e}")
            return False
    
    def purge_non_code_files(self, repo_path: Path) -> Dict:
        """Delete all files except code and text"""
        stats = {"files_deleted": 0, "bytes_freed": 0}
        keep_extensions = self.CODE_EXTENSIONS | self.TEXT_EXTENSIONS
        skip_patterns = {'.git', '.github', 'LICENSE', 'NOTICE', 'COPYING', 'AUTHORS'}
        
        try:
            for file_path in repo_path.rglob('*'):
                if '.git' in file_path.parts or not file_path.is_file():
                    continue
                
                ext = file_path.suffix.lower()
                filename = file_path.name
                file_size = file_path.stat().st_size
                
                if filename in skip_patterns or filename.upper() in skip_patterns:
                    continue
                
                should_keep = ext in keep_extensions or ext == ''
                
                # Delete large .txt files (data files)
                if ext == '.txt' and file_size > 1 * 1024 * 1024:
                    should_keep = False
                
                # Delete large .json files (datasets)
                if ext == '.json' and file_size > 5 * 1024 * 1024:
                    should_keep = False
                
                if not should_keep:
                    try:
                        file_path.unlink()
                        stats["files_deleted"] += 1
                        stats["bytes_freed"] += file_size
                    except:
                        pass
        except Exception as e:
            self.logger.error(f"   Purge error: {e}")
        
        return stats
    
    def run(self):
        """Clone all repos from repos_to_clone.json"""
        if not self.input_file.exists():
            self.logger.error(f"❌ {self.input_file} not found! Run github_searcher.py first.")
            return
        
        with open(self.input_file, 'r') as f:
            repos_to_clone = json.load(f)
        
        total_repos = len(repos_to_clone)
        repos_remaining = [r for r in repos_to_clone if r['full_name'] not in self.cloned_repos]
        
        self.logger.info("="*80)
        self.logger.info("📦 Git Repository Cloner")
        self.logger.info(f"Total repos to clone: {len(repos_remaining):,} (of {total_repos:,})")
        self.logger.info("="*80)
        print()
        
        cloned = 0
        failed = 0
        
        for idx, repo in enumerate(repos_remaining, 1):
            repo_name = repo['full_name']
            
            # Progress bar
            progress_pct = (idx / len(repos_remaining)) * 100
            bar_length = 40
            filled = int(bar_length * idx / len(repos_remaining))
            bar = '█' * filled + '░' * (bar_length - filled)
            
            self.logger.info(f"[{bar}] {progress_pct:>5.1f}% ({idx:,}/{len(repos_remaining):,})")
            self.logger.info(f"🔄 CLONING: {repo_name} ({repo['stars']} ⭐)")
            self.logger.info(f"   URL: {repo['clone_url']}")
            
            success = self.clone_repository(repo['clone_url'], repo_name)
            
            if success:
                self.logger.info(f"✅ CLONED: {repo_name}")
                
                # Purge non-code files
                repo_path = self.repos_dir / repo_name.replace("/", "_")
                purge_stats = self.purge_non_code_files(repo_path)
                
                if purge_stats['files_deleted'] > 0:
                    self.logger.info(f"   🗑️  Purged: {purge_stats['files_deleted']:,} files, {purge_stats['bytes_freed'] / (1024**2):.1f} MB freed")
                
                self.cloned_repos.add(repo_name)
                cloned += 1
                
                # Save progress every 10 repos
                if cloned % 10 == 0:
                    self._save_cloned()
            else:
                self.logger.error(f"❌ FAILED: {repo_name}")
                failed += 1
            
            print()
        
        self._save_cloned()
        
        self.logger.info("="*80)
        self.logger.info(f"✅ Cloning complete!")
        self.logger.info(f"Cloned: {cloned:,} | Failed: {failed:,}")
        self.logger.info("="*80)


def main():
    cloner = GitCloner()
    cloner.run()


if __name__ == "__main__":
    main()


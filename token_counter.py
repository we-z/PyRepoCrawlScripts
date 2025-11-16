#!/usr/bin/env python3
"""
Token Counter
Fast token counting for all repos in cloned_repos/ with progress bar
"""

import sys
import json
from datetime import datetime
from pathlib import Path
import tiktoken
from concurrent.futures import ThreadPoolExecutor, as_completed

class TokenCounter:
    """Fast token counting with progress bar"""
    
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
        self.output_file = self.base_dir / "token_counts.json"
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens_in_file(self, file_path: Path) -> int:
        """Count tokens in a file with size limits"""
        try:
            file_size = file_path.stat().st_size
            ext = file_path.suffix.lower()
            
            # Size limits
            if ext == '.txt' and file_size > 1 * 1024 * 1024:
                return 0
            if ext in self.CODE_EXTENSIONS and file_size > 10 * 1024 * 1024:
                return 0
            if file_size > 5 * 1024 * 1024:
                return 0
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if len(content) > 5_000_000:
                    return 0
                tokens = self.tokenizer.encode(content, disallowed_special=())
                return len(tokens)
        except:
            return 0
    
    def count_repo_tokens(self, repo_path: Path) -> Dict:
        """Count tokens in a single repo"""
        stats = {"tokens": 0, "python_files": 0, "total_files": 0}
        
        try:
            for file_path in repo_path.rglob('*'):
                if file_path.is_file() and '.git' not in file_path.parts:
                    stats["total_files"] += 1
                    ext = file_path.suffix.lower()
                    
                    if ext in self.CODE_EXTENSIONS or ext in self.TEXT_EXTENSIONS:
                        tokens = self.count_tokens_in_file(file_path)
                        if tokens > 0:
                            stats["tokens"] += tokens
                            if ext in self.CODE_EXTENSIONS:
                                stats["python_files"] += 1
        except:
            pass
        
        return stats
    
    def run(self):
        """Count tokens in all repos with progress bar"""
        if not self.repos_dir.exists():
            print("❌ No cloned_repos directory found!")
            return
        
        repo_dirs = [d for d in self.repos_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
        total_repos = len(repo_dirs)
        
        print("="*80)
        print("📊 Token Counter")
        print(f"Repos to count: {total_repos:,}")
        print("="*80)
        print()
        
        results = {}
        total_tokens = 0
        total_py_files = 0
        
        # Use parallel processing for speed
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self.count_repo_tokens, repo_dir): repo_dir for repo_dir in repo_dirs}
            
            completed = 0
            for future in as_completed(futures):
                repo_dir = futures[future]
                stats = future.result()
                
                repo_name = repo_dir.name.replace("_", "/", 1)
                results[repo_name] = stats
                
                total_tokens += stats['tokens']
                total_py_files += stats['python_files']
                completed += 1
                
                # Progress bar
                progress_pct = (completed / total_repos) * 100
                bar_length = 50
                filled = int(bar_length * completed / total_repos)
                bar = '█' * filled + '░' * (bar_length - filled)
                
                print(f"\r[{bar}] {progress_pct:>5.1f}% ({completed:,}/{total_repos:,}) | Tokens: {total_tokens:>15,} | Repo: {repo_name[:40]:40s}", end='', flush=True)
        
        print()
        print()
        
        # Save results
        with open(self.output_file, 'w') as f:
            json.dump({
                "total_tokens": total_tokens,
                "total_repos": total_repos,
                "total_py_files": total_py_files,
                "counted_at": datetime.now().isoformat(),
                "repos": results
            }, f, indent=2)
        
        print("="*80)
        print("✅ Token counting complete!")
        print(f"Total tokens: {total_tokens:,}")
        print(f"Total repos: {total_repos:,}")
        print(f"Python files: {total_py_files:,}")
        print(f"Saved to: {self.output_file}")
        print("="*80)


def main():
    counter = TokenCounter()
    counter.run()


if __name__ == "__main__":
    main()


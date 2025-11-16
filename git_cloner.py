#!/usr/bin/env python3
"""Git Cloner - Clones repos from repos_to_clone.json and purges non-code files"""
import sys, json, shutil, subprocess
from pathlib import Path

KEEP_EXT = {'.py', '.pyx', '.pyi', '.pyw', '.ipynb',
        '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp', '.cs', 
        '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.r', '.jl',
        '.sh', '.bash', '.zsh', '.fish', '.md', '.rst', '.txt',
        '.json', '.yaml', '.yml', '.toml', '.xml', '.cfg', '.ini', '.conf','.csv', '.tsv',
        '.html', '.css', '.scss', '.sass', '.less', '.lock', '.requirements',
        '.gitignore', '.gitattributes', '.editorconfig', '.env'}


class GitCloner:
    def __init__(self):
        base = Path(__file__).parent
        self.repos_dir = base / "cloned_repos"
        self.repos_dir.mkdir(exist_ok=True)
        self.cloned = set(json.load(open(base / "repos_cloned.json"))) if (base / "repos_cloned.json").exists() else set()
        self.cloned_file = base / "repos_cloned.json"
    
    def clone(self, url: str, name: str) -> bool:
        path = self.repos_dir / name.replace("/", "_")
        if path.exists(): shutil.rmtree(path)
        try:
            p = subprocess.Popen(["git", "clone", "--depth", "1", "--progress", url, str(path)],
                               stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1)
            print("   ", end='', flush=True)
            for line in p.stderr:
                if line.strip() and ('Receiving objects' in line or 'Resolving deltas' in line):
                    print(f"\r   {line.strip()}", end='' if 'done' not in line.lower() else '\n', flush=True)
            print()
            p.wait()
            return p.returncode == 0
        except: return False
    
    def purge(self, path: Path):
        stats = [0, 0]  # files, bytes
        for f in path.rglob('*'):
            if f.is_file() and '.git' not in f.parts and f.suffix.lower() not in KEEP_EXT and f.suffix != '':
                # Also purge large .txt (>1MB) and .json (>5MB)
                size = f.stat().st_size
                if (f.suffix == '.txt' and size > 1024*1024) or (f.suffix == '.json' and size > 5*1024*1024):
                    try: f.unlink(); stats[0] += 1; stats[1] += size
                    except: pass
                elif f.suffix.lower() not in KEEP_EXT:
                    try: f.unlink(); stats[0] += 1; stats[1] += size
                    except: pass
        return stats
    
    def run(self):
        input_file = self.repos_dir.parent / "repos_to_clone.json"
        if not input_file.exists():
            print("❌ repos_to_clone.json not found! Run github_searcher.py first.")
            return
        
        repos = [r for r in json.load(open(input_file)) if r['full_name'] not in self.cloned]
        total = len(repos)
        print(f"📦 Cloning {total:,} repos\n")
        
        cloned, failed = 0, 0
        for i, repo in enumerate(repos, 1):
            pct = i / total * 100
            bar = '█' * int(40 * i / total) + '░' * (40 - int(40 * i / total))
            print(f"[{bar}] {pct:>5.1f}% ({i:,}/{total:,}) | Cloned: {cloned:,} | Failed: {failed:,}")
            print(f"🔄 {repo['full_name']} ({repo['stars']} ⭐)")
            
            if self.clone(repo['clone_url'], repo['full_name']):
                print(f"✅ CLONED")
                files, bytes_freed = self.purge(self.repos_dir / repo['full_name'].replace("/", "_"))
                if files > 0: print(f"   🗑️  Purged: {files:,} files, {bytes_freed / 1024**2:.1f} MB")
                self.cloned.add(repo['full_name'])
                cloned += 1
                if cloned % 10 == 0: json.dump(list(self.cloned), open(self.cloned_file, 'w'))
            else:
                print(f"❌ FAILED")
                failed += 1
            print()
        
        json.dump(list(self.cloned), open(self.cloned_file, 'w'))
        print(f"\n✅ Done! Cloned: {cloned:,} | Failed: {failed:,}")

if __name__ == "__main__":
    GitCloner().run()


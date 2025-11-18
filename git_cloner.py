#!/usr/bin/env python3
"""Git Cloner - Clones repos from repos_to_clone.json and purges non-code files"""
import json, shutil, subprocess
from pathlib import Path


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
        files_deleted = 0
        bytes_freed = 0
        
        # Delete all files that are not .py files (skip .git directory entirely)
        for f in path.rglob('*'):
            if f.is_file() and '.git' not in f.parts:
                if f.suffix.lower() != '.py':
                    try:
                        size = f.stat().st_size
                        f.unlink()
                        files_deleted += 1
                        bytes_freed += size
                    except (OSError, PermissionError):
                        pass
        
        # Delete empty directories (excluding .git and the root path itself)
        dirs_deleted = 0
        dirs = [d for d in path.rglob('*') if d.is_dir() and '.git' not in d.parts and d != path]
        # Sort by depth descending (deepest first) to handle nested empty dirs
        dirs.sort(key=lambda d: len(d.parts), reverse=True)
        for d in dirs:
            try:
                if not any(d.iterdir()):
                    d.rmdir()
                    dirs_deleted += 1
            except (OSError, PermissionError):
                pass
        
        return [files_deleted, bytes_freed, dirs_deleted]
    
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
                files, bytes_freed, dirs_deleted = self.purge(self.repos_dir / repo['full_name'].replace("/", "_"))
                if files > 0 or dirs_deleted > 0:
                    msg = f"   🗑️  Purged: {files:,} files, {bytes_freed / 1024**2:.1f} MB"
                    if dirs_deleted > 0:
                        msg += f" | {dirs_deleted:,} empty dirs"
                    print(msg)
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


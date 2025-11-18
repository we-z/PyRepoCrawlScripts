#!/usr/bin/env python3
"""Git Cloner - Clones repos and extracts only .py files"""
import json, shutil, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time


class GitCloner:
    def __init__(self, max_workers: int = 4):
        base = Path(__file__).parent
        self.repos_dir = base / "cloned_repos"
        self.temp_dir = base / "temp_clones"
        self.repos_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.cloned = set(json.load(open(base / "repos_cloned.json"))) if (base / "repos_cloned.json").exists() else set()
        self.cloned_file = base / "repos_cloned.json"
        self.max_workers = max_workers
        self.lock = Lock()
        self.cloned_count = 0
        self.failed_count = 0
        self.completed_count = 0
    
    def extract_py_files(self, clone_path: Path, repo_name: str) -> tuple[int, int]:
        dest_dir = self.repos_dir / repo_name.replace("/", "_")
        if dest_dir.exists(): shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        files_copied = bytes_copied = 0
        used_names = set()
        for py_file in clone_path.rglob('*.py'):
            if '.git' not in py_file.parts:
                try:
                    dest_name = py_file.name
                    if dest_name in used_names:
                        dest_name = f"{py_file.stem}_{hash(py_file.relative_to(clone_path)) % 10000}{py_file.suffix}"
                    used_names.add(dest_name)
                    size = py_file.stat().st_size
                    with open(py_file, 'rb') as src, open(dest_dir / dest_name, 'wb') as dst:
                        dst.write(src.read())
                    files_copied += 1
                    bytes_copied += size
                except (OSError, PermissionError): pass
        return files_copied, bytes_copied
    
    def clone_and_extract(self, url: str, name: str) -> tuple[bool, int, float]:
        """Returns (success, files_count, bytes_mb)"""
        temp_path = self.temp_dir / name.replace("/", "_")
        if temp_path.exists(): shutil.rmtree(temp_path)
        try:
            p = subprocess.Popen(["git", "clone", "--depth", "1", "--quiet", url, str(temp_path)],
                               stderr=subprocess.PIPE, stdout=subprocess.PIPE)
            p.wait()
            if p.returncode == 0:
                files, bytes_copied = self.extract_py_files(temp_path, name)
                shutil.rmtree(temp_path)
                return True, files, bytes_copied / 1024**2
            return False, 0, 0.0
        except:
            if temp_path.exists(): shutil.rmtree(temp_path, ignore_errors=True)
            return False, 0, 0.0
    
    def _process_repo(self, repo: dict) -> tuple[str, bool, int, float, int]:
        """Worker function for parallel cloning. Returns (name, success, files, mb, stars)"""
        name = repo['full_name']
        stars = repo['stars']
        url = repo['clone_url']
        
        success, files, mb = self.clone_and_extract(url, name)
        
        with self.lock:
            if success:
                self.cloned.add(name)
                self.cloned_count += 1
                save_needed = self.cloned_count % 10 == 0
            else:
                self.failed_count += 1
                save_needed = False
            self.completed_count += 1
            
            if save_needed:
                json.dump(list(self.cloned), open(self.cloned_file, 'w'))
        
        return name, success, files, mb, stars
    
    def run(self):
        input_file = self.repos_dir.parent / "repos_to_clone.json"
        if not input_file.exists():
            print("❌ repos_to_clone.json not found! Run github_searcher.py first.")
            return
        repos = [r for r in json.load(open(input_file)) if r['full_name'] not in self.cloned]
        total = len(repos)
        print(f"📦 Cloning {total:,} repos with {self.max_workers} workers\n")
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_repo, repo): repo for repo in repos}
            
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    name, success, files, mb, stars = future.result()
                    with self.lock:
                        completed = self.completed_count
                        cloned = self.cloned_count
                        failed = self.failed_count
                        pct = completed / total * 100
                        bar = '█' * int(40 * completed / total) + '░' * (40 - int(40 * completed / total))
                        print(f"[{bar}] {pct:>5.1f}% ({completed:,}/{total:,}) | Cloned: {cloned:,} | Failed: {failed:,}")
                        if success:
                            print(f"✅ {name} ({stars} ⭐) - {files:,} files ({mb:.1f} MB)")
                        else:
                            print(f"❌ {name} ({stars} ⭐) - FAILED")
                        print()
                except Exception as e:
                    with self.lock:
                        self.failed_count += 1
                        self.completed_count += 1
                    print(f"❌ {repo['full_name']} - Exception: {e}\n")
        
        json.dump(list(self.cloned), open(self.cloned_file, 'w'))
        elapsed = time.time() - start_time
        print(f"\n✅ Done! Cloned: {self.cloned_count:,} | Failed: {self.failed_count:,} | Time: {elapsed/60:.1f} min")

if __name__ == "__main__":
    GitCloner().run()


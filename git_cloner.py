#!/usr/bin/env python3
"""Git Cloner - Clones repos and extracts only .py files (Optimized)"""
import json, shutil, subprocess, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

class GitCloner:
    def __init__(self, max_workers: int = 16):
        base = Path(__file__).parent
        self.repos_dir, self.temp_dir = base / "cloned_repos", base / "temp_clones"
        self.repos_dir.mkdir(exist_ok=True); self.temp_dir.mkdir(exist_ok=True)
        self.cloned_file = base / "repos_cloned.json"
        self.cloned = set(json.load(open(self.cloned_file))) if self.cloned_file.exists() else set()
        self.max_workers, self.lock = max_workers, Lock()
        self.cloned_count = self.failed_count = self.completed_count = self.total = 0
    
    def extract_py_files(self, clone_path: Path, repo_name: str) -> tuple[int, int]:
        dest_dir = self.repos_dir / repo_name.replace("/", "_")
        if dest_dir.exists(): shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        files_copied = bytes_copied = 0
        used_names = set()
        for py_file in clone_path.rglob('*.py'):
            if '.git' not in py_file.parts:
                try:
                    dest_name = py_file.name if py_file.name not in used_names else f"{py_file.stem}_{hash(py_file.relative_to(clone_path)) % 10000}{py_file.suffix}"
                    used_names.add(dest_name)
                    size = py_file.stat().st_size
                    shutil.copy2(py_file, dest_dir / dest_name)
                    files_copied += 1; bytes_copied += size
                except (OSError, PermissionError): pass
        return files_copied, bytes_copied

    def run_git(self, args, cwd=None, name=""):
        res = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
        if res.returncode != 0:
            with self.lock: print(f"❌ Git Error ({name}): {' '.join(args)}\n{res.stderr}")
            return False
        return True
    
    def clone_and_extract(self, url: str, name: str) -> tuple[bool, int, float]:
        path = self.temp_dir / name.replace("/", "_")
        if path.exists(): shutil.rmtree(path)
        try:
            # 1. Clone skeleton (no blobs)
            if not self.run_git(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", "--no-checkout", url, str(path)], name=name): return False, 0, 0.0
            # 2. Sparse checkout only .py files (disable cone mode to allow patterns)
            if not self.run_git(["git", "sparse-checkout", "set", "--no-cone", "**/*.py"], cwd=path, name=name): return False, 0, 0.0
            if not self.run_git(["git", "checkout"], cwd=path, name=name): return False, 0, 0.0
            
            files, size = self.extract_py_files(path, name)
            shutil.rmtree(path)
            return True, files, size / 1024**2
        except Exception as e:
            with self.lock: print(f"❌ Exception {name}: {e}")
            if path.exists(): shutil.rmtree(path, ignore_errors=True)
            return False, 0, 0.0
    
    def _process_repo(self, repo: dict) -> tuple[str, bool, int, float, int]:
        name, stars, url = repo['full_name'], repo['stars'], repo['clone_url']
        success, files, mb = self.clone_and_extract(url, name)
        with self.lock:
            if success:
                self.cloned.add(name); self.cloned_count += 1
                if self.cloned_count % 10 == 0: json.dump(list(self.cloned), open(self.cloned_file, 'w'))
            else: self.failed_count += 1
            self.completed_count += 1
        return name, success, files, mb, stars
    
    def run(self):
        input_file = self.repos_dir.parent / "repos_to_clone.json"
        if not input_file.exists(): return print("❌ repos_to_clone.json not found!")
        repos = [r for r in json.load(open(input_file)) if r['full_name'] not in self.cloned]
        self.total = len(repos)
        print(f"📦 Cloning {self.total:,} repos with {self.max_workers} workers (Sparse Mode)\n")
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self._process_repo, repo): repo for repo in repos}
            for future in as_completed(futures):
                try:
                    name, success, files, mb, stars = future.result()
                    with self.lock:
                        completed, cloned, failed = self.completed_count, self.cloned_count, self.failed_count
                        pct = completed / self.total * 100
                        bar = '█' * int(40 * pct / 100) + '░' * (40 - int(40 * pct / 100))
                        print(f"[{bar}] {pct:>5.1f}% ({completed:,}/{self.total:,}) | Cloned: {cloned:,} | Failed: {failed:,}")
                        if success: print(f"✅ {name} ({stars} ⭐) - {files:,} files ({mb:.1f} MB)")
                        else: print(f"❌ {name} ({stars} ⭐) - FAILED")
                        print()
                except Exception as e:
                    with self.lock: self.failed_count += 1; self.completed_count += 1
                    print(f"❌ {futures[future]['full_name']} - Exception: {e}\n")
        json.dump(list(self.cloned), open(self.cloned_file, 'w'))
        print(f"\n✅ Done! Cloned: {self.cloned_count:,} | Failed: {self.failed_count:,} | Time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    GitCloner().run()


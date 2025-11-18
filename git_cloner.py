#!/usr/bin/env python3
"""Git Cloner - Clones repos and extracts only .py files"""
import json, shutil, subprocess
from pathlib import Path


class GitCloner:
    def __init__(self):
        base = Path(__file__).parent
        self.repos_dir = base / "cloned_repos"
        self.temp_dir = base / "temp_clones"
        self.repos_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.cloned = set(json.load(open(base / "repos_cloned.json"))) if (base / "repos_cloned.json").exists() else set()
        self.cloned_file = base / "repos_cloned.json"
    
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
    
    def clone_and_extract(self, url: str, name: str) -> bool:
        temp_path = self.temp_dir / name.replace("/", "_")
        if temp_path.exists(): shutil.rmtree(temp_path)
        try:
            p = subprocess.Popen(["git", "clone", "--depth", "1", "--progress", url, str(temp_path)],
                               stderr=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, bufsize=1)
            for line in p.stderr:
                if line.strip() and ('Receiving objects' in line or 'Resolving deltas' in line):
                    print(f"\r   {line.strip()}", end='' if 'done' not in line.lower() else '\n', flush=True)
            p.wait()
            if p.returncode == 0:
                files, bytes_copied = self.extract_py_files(temp_path, name)
                print(f"   📄 Extracted {files:,} .py files ({bytes_copied / 1024**2:.1f} MB)")
                shutil.rmtree(temp_path)
                return True
            return False
        except:
            if temp_path.exists(): shutil.rmtree(temp_path, ignore_errors=True)
            return False
    
    def run(self):
        input_file = self.repos_dir.parent / "repos_to_clone.json"
        if not input_file.exists():
            print("❌ repos_to_clone.json not found! Run github_searcher.py first.")
            return
        repos = [r for r in json.load(open(input_file)) if r['full_name'] not in self.cloned]
        total = len(repos)
        print(f"📦 Cloning {total:,} repos\n")
        cloned = failed = 0
        for i, repo in enumerate(repos, 1):
            pct = i / total * 100
            bar = '█' * int(40 * i / total) + '░' * (40 - int(40 * i / total))
            print(f"[{bar}] {pct:>5.1f}% ({i:,}/{total:,}) | Cloned: {cloned:,} | Failed: {failed:,}")
            print(f"🔄 {repo['full_name']} ({repo['stars']} ⭐)")
            if self.clone_and_extract(repo['clone_url'], repo['full_name']):
                print("✅ EXTRACTED")
                self.cloned.add(repo['full_name'])
                cloned += 1
                if cloned % 10 == 0: json.dump(list(self.cloned), open(self.cloned_file, 'w'))
            else:
                print("❌ FAILED")
                failed += 1
            print()
        json.dump(list(self.cloned), open(self.cloned_file, 'w'))
        print(f"\n✅ Done! Cloned: {cloned:,} | Failed: {failed:,}")

if __name__ == "__main__":
    GitCloner().run()


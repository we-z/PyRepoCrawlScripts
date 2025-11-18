#!/usr/bin/env python3
"""GitHub ML/DL Repo Searcher - Outputs: repos_to_clone.json"""
import os, sys, json, time, requests, random
from pathlib import Path
from dotenv import load_dotenv

class GitHubSearcher:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"token {token}"}
        base = Path(__file__).parent
        self.output = base / "repos_to_clone.json"
        self.seen_file = base / "data" / "seen_repos.json"
        self.seen_file.parent.mkdir(exist_ok=True)
        
        # Load already cloned and seen
        repos_dir = base / "cloned_repos"
        self.cloned = {d.name.replace("_", "/", 1) for d in repos_dir.iterdir() if d.is_dir()} if repos_dir.exists() else set()
        self.seen = set(json.load(open(self.seen_file))) if self.seen_file.exists() else set()
    
    def search(self, q: str, page: int, sort: str) -> list:
        try:
            r = requests.get("https://api.github.com/search/repositories",
                           headers=self.headers, params={"q": q, "page": page, "per_page": 100, "sort": sort}, timeout=30)
            if r.status_code == 403:
                time.sleep(int(r.headers.get('X-RateLimit-Reset', time.time())) - int(time.time()) + 10)
                return self.search(q, page, sort)
            return r.json().get('items', []) if r.status_code == 200 else []
        except: return []
    
    def run(self, target: int = 50000):
        already_have = len(self.cloned)
        print("="*90)
        print(f"🔍 GitHub ML/DL Repository Searcher")
        print(f"Target: {target:,} new repos | Already have: {already_have:,} cloned repos")
        print("="*90)
        print()
        
        results = []
        topics = ["machine-learning", "deep-learning", "neural-network", "pytorch", "tensorflow", 
                  "keras", "scikit-learn", "nlp", "natural-language-processing", "computer-vision", 
                  "image-processing", "object-detection", "segmentation", "reinforcement-learning", 
                  "generative-ai", "transformers", "llm", "large-language-model", "diffusion", 
                  "gan", "vae", "autoencoder", "classification", "regression", "clustering", 
                  "data-science", "kaggle", "neural-networks", "convolutional-neural-network",
                  "recurrent-neural-network", "lstm", "gru", "attention-mechanism", "bert", 
                  "gpt", "stable-diffusion", "yolo", "resnet", "vgg", "image-classification",
                  "semantic-segmentation", "instance-segmentation", "face-recognition", 
                  "speech-recognition", "audio-processing", "time-series", "forecasting",
                  "anomaly-detection", "recommendation-system", "embeddings", "transfer-learning",
                  "few-shot-learning", "zero-shot-learning", "graph-neural-network", "gnn",
                  "vision-transformer", "clip", "whisper", "chatbot", "text-generation",
                  "sentiment-analysis", "named-entity-recognition", "question-answering",
                  "summarization", "translation", "ocr", "pose-estimation", "tracking"]
        
        query_num = 0
        for topic in topics:
            for stars in [">=500", "200..499", "100..199", "50..99", "20..49", "10..19", "5..9", "1..4"]:
                for sort in ["stars", "updated", "forks"]:
                    query_num += 1
                    query = f"language:python topic:{topic} stars:{stars}"
                    
                    for page in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
                        print(f"Query {query_num:>4}: {query[:55]:55s} | Sort: {sort:8s} | Page: {page}", end='', flush=True)
                        
                        repos_found = self.search(query, page, sort)
                        print(f" | API returned: {len(repos_found):>3} repos", end='', flush=True)
                        
                        # Skip remaining pages if this page has 0 results
                        if len(repos_found) == 0:
                            print(f" | Skipping remaining pages (0 results)")
                            break
                        
                        new = 0
                        for r in repos_found:
                            rid, name = str(r['id']), r['full_name']
                            if rid not in self.seen and name not in self.cloned:
                                self.seen.add(rid)
                                results.append({"full_name": name, "clone_url": r['clone_url'], "stars": r.get('stargazers_count', 0)})
                                new += 1
                        
                        progress = (len(results) / target) * 100
                        print(f" | New: {new:>3} | Total found: {len(results):>6,} ({progress:>5.1f}%)")
                        
                        if len(results) >= target: break
                    if len(results) >= target: break
                if len(results) >= target: break
            if len(results) >= target: break
        
        json.dump(results, open(self.output, 'a'), indent=2)
        json.dump(list(self.seen), open(self.seen_file, 'a'))
        
        print("\n" + "="*90)
        print(f"✅ Search Complete!")
        print(f"   New unique repos found: {len(results):,}")
        print(f"   Already have cloned:    {already_have:,}")
        print(f"   Total after cloning:    {already_have + len(results):,}")
        print(f"   Saved to: {self.output}")
        print("="*90)

if __name__ == "__main__":
    load_dotenv()
    token = os.environ.get('GITHUB_TOKEN')
    if not token: sys.exit("ERROR: GITHUB_TOKEN not found!")
    GitHubSearcher(token).run(50000)
    
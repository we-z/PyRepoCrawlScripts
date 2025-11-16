# 🚀 Quick Start Guide - New Modular System

## The New Way (Modular)

Instead of one huge script, we now have **three focused tools**:

## 1️⃣ Search for Repos

```bash
python3 github_searcher.py
```

**What it does:**
- Searches GitHub for ML/DL Python repos
- Uses diverse queries (topics, years, licenses, filenames, etc.)
- Filters out duplicates automatically
- Saves unique repos to `repos_to_clone.json`

**Output file:** `repos_to_clone.json`
```json
[
  {
    "full_name": "pytorch/pytorch",
    "clone_url": "https://github.com/pytorch/pytorch.git",
    "stars": 95044,
    "forks": 25896,
    "size": 1165180,
    "found_by": "language:python topic:pytorch stars:5000.."
  },
  ...
]
```

**Customize:** Edit target number of repos:
```python
searcher.run(target_repos=50000)  # Default is 50k
```

## 2️⃣ Clone Repos

```bash
python3 git_cloner.py
```

**What it does:**
- Reads `repos_to_clone.json`
- Clones each repo with live git progress
- Purges all non-code files (images, videos, models, etc.)
- Shows progress bar
- Tracks completion in `repos_cloned.json`

**Features:**
- Resumable (tracks what's already cloned)
- Shows git's native progress bars
- Automatic purging after each clone
- Progress bar shows repos cloned/remaining

## 3️⃣ Count Tokens

```bash
python3 token_counter.py
```

**What it does:**
- Scans all repos in `cloned_repos/`
- Counts tokens in parallel (4 workers)
- Shows live progress bar
- Saves results to `token_counts.json`

**Fast:** Uses parallel processing for 4x speed!

**Output file:** `token_counts.json`
```json
{
  "total_tokens": 50234567890,
  "total_repos": 50000,
  "total_py_files": 1234567,
  "counted_at": "2025-11-15T...",
  "repos": {
    "pytorch/pytorch": {
      "tokens": 21924396,
      "python_files": 4197,
      "total_files": 20016
    },
    ...
  }
}
```

## 🔄 Run Complete Pipeline

```bash
./run_all.sh
```

Runs all three scripts in sequence:
1. Search → `repos_to_clone.json`
2. Clone → `cloned_repos/`
3. Count → `token_counts.json`

## 📊 Check Progress Anytime

### How many repos found?
```bash
jq 'length' repos_to_clone.json
```

### How many repos cloned?
```bash
jq 'length' repos_cloned.json
```

### What's my token count?
```bash
jq '.total_tokens' token_counts.json
```

### How much disk space?
```bash
du -sh cloned_repos/
```

## Individual Use Cases

### Scenario 1: Just Want More Repos
```bash
python3 github_searcher.py  # Search for 50k more repos
python3 git_cloner.py       # Clone the new ones
python3 token_counter.py    # Recount everything
```

### Scenario 2: Already Have Repos, Just Count
```bash
python3 token_counter.py
```

### Scenario 3: Re-clone Failed Repos
Edit `repos_to_clone.json` to include only failed repos, then:
```bash
python3 git_cloner.py
```

### Scenario 4: Start Fresh Search
```bash
rm data/seen_repos.json data/search_progress.json
python3 github_searcher.py
```

## Advantages

### ✅ Modular
- Each script has ONE job
- Easy to understand
- Easy to modify

### ✅ Fast
- Don't re-search if you have repos
- Don't re-clone if already cloned
- Just recount tokens (fast with parallel processing)

### ✅ Resumable
- Each script tracks its own progress
- Stop and resume anytime
- No wasted work

### ✅ Debuggable
- Issues isolated to specific scripts
- Smaller files = easier to fix
- Clear separation of concerns

## File Outputs

| File | Created By | Used By | Purpose |
|------|------------|---------|---------|
| `repos_to_clone.json` | Searcher | Cloner | List of repos to clone |
| `repos_cloned.json` | Cloner | Cloner | Track cloned repos |
| `token_counts.json` | Counter | You! | Token statistics |
| `data/seen_repos.json` | Searcher | Searcher | Deduplicate searches |
| `data/search_progress.json` | Searcher | Searcher | Resume searches |

## Comparison: Old vs New

### Old Way (Monolithic):
```bash
./run_crawler.sh
# Searches, clones, counts all in one
# Can't stop and resume at different stages
# Hard to debug when something goes wrong
# 1155 lines in one file
```

### New Way (Modular):
```bash
python3 github_searcher.py  # Step 1
python3 git_cloner.py       # Step 2  
python3 token_counter.py    # Step 3
# Or just: ./run_all.sh
# Can run/resume each step independently
# Easy to debug specific issues
# 219 + 175 + 145 = 539 lines total
```

## Getting Started

### Option 1: Full Pipeline
```bash
./run_all.sh
```

### Option 2: Step by Step
```bash
# 1. Search (takes ~10-30 min for 50k repos)
python3 github_searcher.py

# 2. Clone (takes hours/days depending on count)
python3 git_cloner.py

# 3. Count tokens (takes ~5-15 min with parallel processing)
python3 token_counter.py
```

### Option 3: Just Count Your Existing Repos
```bash
python3 token_counter.py
```

## 🎯 Next Steps

1. **Test token counter on existing repos:**
```bash
python3 token_counter.py
```
This will give you accurate token count for your 19,179 existing repos!

2. **Search for more repos:**
```bash
python3 github_searcher.py
```

3. **Clone the new repos:**
```bash
python3 git_cloner.py
```

Much cleaner and easier to manage! 🎉


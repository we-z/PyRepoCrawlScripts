# Changelog

## [2.0.0] - 2025-11-13 - Major Update

### 🎯 ML/Deep Learning Focus
**BREAKING CHANGE:** Completely overhauled search queries to focus exclusively on ML/DL

#### Removed Topics:
- ❌ Web frameworks (django, flask, fastapi)
- ❌ General purpose (web, cli, gui, game, backend, frontend)
- ❌ Infrastructure (docker, kubernetes, ci-cd, database, orm)
- ❌ Generic tools (scraper, parser, bot, automation)

#### Added ML/DL Topics (70+):
- ✅ Core ML/DL: machine-learning, deep-learning, neural-network, pytorch, tensorflow, keras
- ✅ NLP: transformers, llm, bert, gpt, text-generation, sentiment-analysis, named-entity-recognition
- ✅ Computer Vision: object-detection, segmentation, yolo, resnet, pose-estimation, face-recognition
- ✅ Generative AI: stable-diffusion, gan, vae, diffusion, dalle, clip
- ✅ Advanced: reinforcement-learning, meta-learning, few-shot-learning, graph-neural-network
- ✅ Audio: speech-recognition, audio-processing, whisper
- ✅ Specialized: time-series, forecasting, anomaly-detection, recommendation-system
- ✅ Optimization: quantization, pruning, model-compression, transfer-learning, fine-tuning

### 🔍 Smart Deduplication System
**NEW:** Repository ID tracking across all searches

#### Before:
```
2025-11-13 18:42:17 | INFO | ⏭️  SKIP: benedekrozemberczki/CapsGNN (already processed)
2025-11-13 18:42:18 | INFO | ⏭️  SKIP: sicara/easy-few-shot-learning (already processed)
2025-11-13 18:42:19 | INFO | ⏭️  SKIP: gnes-ai/gnes (already processed)
... (thousands more) ...
```

#### After:
```
   Found: 100 repos on page 1 (Total available: 652)
   Filtered: 45 new, 55 already seen
```

**How it works:**
- Maintains `seen_repos.json` with all repository IDs encountered
- Filters duplicates BEFORE attempting to clone
- No more spam in logs
- Massive time savings

### 📊 Accurate Statistics
**FIXED:** Separated actual failures from skipped repos

#### Stats Display Changes:
```
Before:
│ 📦 Repos: 1,658 cloned | 3,857 failed │

After:
│ 📦 Repos: 1,658 cloned |  15 failed │
│ ⏭️  Skipped:   3,842 already processed │
```

- **Failed** = Actual clone errors (network issues, permission denied, etc.)
- **Skipped** = Already in database (from previous runs or duplicates in search)

### 🎲 Improved Search Strategy
**ENHANCED:** Better sorting and quality filters

#### Sorting:
- Default: Sort by **stars** (descending) - gets highest quality first
- Recent: Sort by **updated** (descending) - gets latest projects
- Each query has optimal sort strategy

#### Star Thresholds:
- Increased minimum star requirements
- Focuses on quality: 5000+, 2000+, 1000+, 500+, 200+, 100+
- Removed low-quality ranges (>=5, >=10 stars)

#### Recency Filter:
- Recent repos must be updated since 2023-01-01
- Ensures active, maintained projects

### 📈 Query Statistics
- **Before:** 260 queries (mixed topics, many duplicates)
- **After:** 340+ queries (all ML/DL focused, properly sorted)
- **Quality:** Much higher - all repos are ML/DL related

### 🔧 Technical Improvements

#### New Files:
- `seen_repos.json` - Tracks all repository IDs encountered
- `.env` support - GitHub token now loaded from environment

#### Modified Tracking:
- `progress.json` - Added `repos_skipped` counter
- `clone_repository()` - Now returns tuple: `(success, path, was_skipped)`

#### Search API:
- Added `sort` and `order` parameters
- Queries specify optimal sorting strategy
- Better API rate limit usage

### 📝 Documentation Updates
- Updated `USAGE.md` with all new features
- Added this `CHANGELOG.md`
- Updated `README.md` with ML/DL focus

### 🐛 Bug Fixes
- Fixed duplicate repo checking (was only checking database, not search history)
- Fixed failed counter (was counting skips as failures)
- Fixed rate limit handling for sorted queries

### ⚡ Performance Improvements
- **50-90% reduction in wasted API calls** (no duplicate checks)
- **Faster progress** (higher quality repos = more tokens)
- **Cleaner logs** (no spam from skipped repos)

---

## [1.0.0] - 2025-11-13 - Initial Release

### Features
- GitHub API integration with authentication
- Multi-query search system (260 queries)
- Automatic cloning with `git clone --depth 1`
- Token counting using tiktoken (cl100k_base)
- Image compression (PNG, JPG, etc.)
- Progress persistence (JSON database)
- Live statistics display
- Resumable crawling
- Comprehensive logging

### Target
- 100 billion tokens of Python code
- Diverse repository collection
- Full metadata tracking


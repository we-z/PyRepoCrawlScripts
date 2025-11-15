# 🚀 Updated Startup Sequence

## What Happens When You Run ./run_crawler.sh

### 1. Initialization
```
================================================================================
GitHub Python Repository Crawler Initialized
Target tokens: 100,000,000,000
Current tokens collected: 47,455,737,889
Repositories cloned: 19,047
================================================================================
```

### 2. Check for New Repos in Directory
```
🔍 Checking for existing cloned repositories...
Found 17,984 directories in cloned_repos/
✅ All existing repos already in database
```
(Or processes any new repos if found)

### 3. Purge Non-Code Files from ALL Repos
```
🗑️  Purging non-code files from existing repos...
Found 17,984 repositories
   pytorch_pytorch: 3,456 files, 451.2 MB freed
      Deleted: model.pth (125.3 MB, .pth)
      Deleted: dataset.npy (87.4 MB, .npy)
   mohit1997_DeepZip: 180 files, 50.3 MB freed
      Deleted: xor40.txt (9.5 MB, .txt)
      Deleted: xor50.txt (9.5 MB, .txt)
      Deleted: xor20.txt (9.5 MB, .txt)
   ...
✅ Purge complete: 1,500,000 files deleted, 250.00 GB freed
```

**What gets deleted:**
- All images (.jpg, .png, .gif, etc.)
- All videos (.mp4, .avi, .mov, etc.)
- All audio (.mp3, .wav, etc.)
- All model files (.pth, .h5, .ckpt, .pkl, .npy, etc.)
- All archives (.zip, .tar, .gz, etc.)
- Large .txt files >1MB (data files)
- Large .json/.csv >5MB (datasets)
- Git pack files (.pack, .idx)
- Everything except code and documentation!

### 4. Recalculate Accurate Statistics
```
📊 Recalculating accurate statistics...
   Scanning 17,984 repositories...
✅ Statistics recalculated:
   Tokens: 47,455,737,889
   Actual disk usage: 605.43 GB
   Total files on disk: 1,234,567
   Python files: 1,790,491
```

**This gives you TRUE current stats after purging!**

### 5. Start Crawling
```
================================================================================
🚀 STARTING CRAWL
================================================================================

================================================================================
🔍 SEARCH QUERY #286: language:python topic:lstm stars:100..199
   Description: ML/DL: lstm (100-199 stars, most stars)
   Sort: stars (desc)
   Current Progress: 47.456% (47,455,737,889 tokens)
================================================================================
```

## Intelligent Features

### Smart File Size Limits (No More Hangs!)

**Different limits for different file types:**
- `.txt` files: 1MB max (larger = data file, skip tokenization)
- Code files (`.py`, etc.): 10MB max
- Other files: 5MB max
- Content: 5M characters max

**Example:**
```
Skipping large .txt file (9.5 MB): xor40.txt
Skipping large code file (12.3 MB): generated_model.py
```

### Progress Logging

**During purging:**
```
   🗑️  Purging non-code files...
      Checked 1,000 files, deleted 234...
      Checked 2,000 files, deleted 567...
      Deleted: huge_dataset.csv (125.3 MB, .csv)
   ✅ Purge done: 891 files deleted (250.2 MB freed)
```

**During tokenization:**
```
   📝 Counting tokens...
      Progress: 500 files checked, 456,789 tokens so far...
      Progress: 1,000 files checked, 923,456 tokens so far...
   ✅ Tokenization complete
```

### Stats Display
```
   📊 Calculating actual disk usage...
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 CURRENT STATISTICS                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🎯 Progress:      47,455,737,889 / 100,000,000,000 tokens (47.456%)         │
│ 📦 Repos:           19,047 cloned  |      15 failed                          │
│ ⏭️  Skipped:         1,567 already processed                                 │
│ 📁 Python Files:     1,790,491 files                                         │
│ 💾 Disk Usage:          605.43 GB (actual on disk)                           │
│ ⚡ Speed:             275,634 tokens/sec  ( 6.6 repos/min)                   │
│ ⏱️  Elapsed:          1 day, 23:49:29                                         │
│ 🕐 Est. Time:             2.2 days                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

Notice: **"(actual on disk)"** - this is the real current size!

## Estimated Impact

**Before purge:** ~855 GB (as you saw from `du -sh`)
**After purge:** ~550-650 GB (removing 200-300 GB)

Your repos contain:
- Model weights (.pth, .h5, .ckpt) - can be GB each
- Datasets (.npy, .npz, large .csv/.txt) - can be GB
- Images/videos/PDFs - common in tutorial repos
- Git pack files - duplicates of the code

All of this will be purged!

## Timeline

With 17,984 repos:
- **Purge phase:** 5-15 minutes (checking ~10M files)
- **Recalc phase:** 2-5 minutes (scanning filesystem)
- **Then continues crawling**

Be patient during startup - it's doing important cleanup!

## Why This Matters

**Before:** Stats showed 1078 GB but actual size unknown
**After:** Stats show exact actual disk size (e.g., 605 GB)

You'll know exactly how much space you're using and can monitor it accurately!


# Quick Usage Guide

## ✅ What's New

The crawler now has these enhanced features:

### 🔄 Auto-Processing of Existing Repos
- On startup, the script scans `cloned_repos/` directory
- Any repos not in the database will be automatically tokenized
- Token counts are added to the total progress

### 📊 Live Statistics Display
- After each repo is processed, you'll see a beautiful stats box showing:
  - Current progress (tokens collected vs. 100B target)
  - Number of repos cloned and failed
  - Total Python files processed
  - Disk usage in GB
  - Processing speed (tokens/sec and repos/min)
  - Time elapsed
  - **Estimated time to completion**

### Example Stats Box:
```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 CURRENT STATISTICS                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🎯 Progress:         139,222,233 / 100,000,000,000 tokens ( 0.139%)         │
│ 📦 Repos:                 12 cloned  |       0 failed                        │
│ 📁 Python Files:          18,394 files                                       │
│ 💾 Disk Usage:             1.56 GB                                           │
│ ⚡ Speed:             837,239 tokens/sec  ( 4.3 repos/min)                   │
│ ⏱️  Elapsed:                0:02:46                                           │
│ 🕐 Est. Time:                1.4 days                                        │
└──────────────────────────────────────────────────────────────────────────────┘
```

## 🚀 Running the Crawler

### Option 1: Using the shell script (recommended)
```bash
./run_crawler.sh
```

### Option 2: Manual
```bash
cd /Users/wheezycapowdis/Desktop/PyRepoCrawlScripts
source venv/bin/activate
python3 github_crawler.py
```


## 📋 What Happens When You Run It

1. **Initialization**
   - Loads previous progress from `data/progress.json`
   - Loads repo database from `data/repos_database.json`
   - Sets up logging to `logs/crawler_TIMESTAMP.log`

2. **Existing Repo Check**
   - Scans `cloned_repos/` directory
   - Processes any repos not in the database
   - Updates total token count

3. **Crawling Loop**
   - Searches GitHub with diverse queries
   - Clones repos one by one with live logs
   - Shows:
     - 🔄 CLONING: repo_name
     - ✅ CLONED: repo_name (success)
     - ❌ FAILED: repo_name (errors)
     - 📊 PROCESSING: repo_name
     - File counts, token counts, images compressed
     - **STATS BOX after each repo**
   
4. **Continuous Progress Saving**
   - After each repo, progress is saved
   - You can stop (Ctrl+C) and resume anytime
   - All data is preserved

## 🎯 Current Status

Run the script and it will show:
- You have **13 repos** in `cloned_repos/`
- **12 are in the database** (139.2M tokens)
- **1 needs processing** (streamlit_streamlit)
- The script will process that one first, then continue crawling

## ⏹️ Stopping the Crawler

Press `Ctrl+C` once to gracefully stop. The crawler will:
- Save all current progress
- Save the repo database
- Display final statistics
- Allow you to resume later

## 🔁 Resuming

Just run the script again! It will:
1. Load previous progress
2. Skip already-cloned repos
3. Continue from where it left off
4. Keep accumulating tokens toward 100B goal

## 📁 File Structure

```
PyRepoCrawlScripts/
├── github_crawler.py      # Main crawler (includes inline stats)
├── show_stats.py          # Standalone stats viewer
├── run_crawler.sh         # Easy run script
├── requirements.txt       # Dependencies
├── README.md             # Full documentation
├── USAGE.md              # This file
├── cloned_repos/         # All cloned GitHub repos
├── logs/                 # Detailed logs with timestamps
└── data/                 # Progress and database JSON files
```

## 💡 Pro Tips

1. **Run in tmux/screen** for long-running sessions
2. **Check logs** if you want to see detailed info: `tail -f logs/crawler_*.log`
3. **Monitor disk space** - 100B tokens could be several TB
4. **Stats are live** - watch the time estimates adjust as the crawler learns the average repo size
5. **Progress is saved constantly** - don't worry about interruptions

## 🎉 Ready to Go!

Simply run:
```bash
./run_crawler.sh
```

And watch it collect 100B tokens of Python code! 🚀


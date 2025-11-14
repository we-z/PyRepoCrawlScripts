# 🚀 Automatic Search Expansion

## Overview

The crawler now has **built-in automatic expansion** - no separate scripts needed!

When all search queries are exhausted at the current star threshold, the crawler automatically:
1. Detects exhaustion (after 2 empty cycles)
2. Lowers the star threshold to next level
3. Resets completed queries
4. Regenerates search queries with new threshold
5. Continues crawling seamlessly

## Threshold Levels

The crawler progresses through these levels automatically:

```
5000+ ⭐ → 2000+ ⭐ → 1000+ ⭐ → 500+ ⭐ → 200+ ⭐ → 100+ ⭐ → 50+ ⭐ → 20+ ⭐ → 10+ ⭐ → 5+ ⭐ → 1+ ⭐
```

### What Each Level Includes

**5000+ stars** (Level 1) - ~200 repos
- PyTorch, TensorFlow, Keras, Scikit-learn
- Major frameworks and libraries
- Industry-standard tools

**2000+ stars** (Level 2) - ~500 repos
- Stable Diffusion implementations
- Popular NLP models
- Well-maintained tools

**1000+ stars** (Level 3) - ~1,000 repos
- Research paper implementations
- Specialized frameworks
- Community favorites

**500+ stars** (Level 4) - ~2,000 repos
- Tutorial repositories
- Course materials
- Specialized applications

**200+ stars** (Level 5) - ~5,000 repos
- Academic projects
- Research code
- Niche tools

**100+ stars** (Level 6) - ~10,000 repos
- Student projects (high quality)
- Kaggle competition code
- Experiment repositories

**50-1+ stars** (Levels 7-10) - ~100,000+ repos
- All ML/DL repos regardless of popularity
- Personal projects
- Early-stage research
- Everything Python + ML/DL

## Live Example

When the crawler exhausts queries at 5000+ stars:

```
2025-11-14 12:00:00 | INFO | 🔄 Cycling back to beginning of search queries
2025-11-14 12:00:00 | INFO | 🔄 Cycling back to beginning of search queries

2025-11-14 12:00:00 | INFO | 
================================================================================
2025-11-14 12:00:00 | INFO | 🔽 EXPANDING SEARCH - LOWERING STAR THRESHOLD
2025-11-14 12:00:00 | INFO | ================================================================================
2025-11-14 12:00:00 | INFO | Star threshold: 5000 → 2000
2025-11-14 12:00:00 | INFO | This will search for repos with 2000+ stars
2025-11-14 12:00:00 | INFO | Resetting completed queries to search with new threshold...
2025-11-14 12:00:00 | INFO | ✅ Generated 386 new queries
2025-11-14 12:00:00 | INFO | 🚀 Continuing crawl with expanded search...
2025-11-14 12:00:00 | INFO | ================================================================================

2025-11-14 12:00:00 | INFO | 
================================================================================
2025-11-14 12:00:00 | INFO | 🔍 SEARCH QUERY #1: language:python topic:machine-learning stars:>=2000
2025-11-14 12:00:00 | INFO |    Description: ML/DL: machine-learning with >=2000 stars
2025-11-14 12:00:00 | INFO |    Sort: stars (desc)
2025-11-14 12:00:00 | INFO |    Current Progress: 27.574% (27,573,752,690 tokens)
2025-11-14 12:00:00 | INFO | ================================================================================
```

## Progress Tracking

The `progress.json` file tracks:

```json
{
  "current_min_stars": 2000,
  "threshold_expansions": 3,
  ...
}
```

- `current_min_stars`: Current star threshold level
- `threshold_expansions`: Number of times threshold was lowered

## Statistics Display

After each repo, you'll see:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ 📊 CURRENT STATISTICS                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 🎯 Progress:      35,000,000,000 / 100,000,000,000 tokens (35.000%)         │
│ 📦 Repos:            12,000 cloned  |      20 failed                         │
│ ⏭️  Skipped:          4,500 already processed                                │
│ 📁 Python Files:     1,500,000 files                                         │
│ 💾 Disk Usage:          800.50 GB                                            │
│ ⚡ Speed:             400,000 tokens/sec  ( 7.5 repos/min)                   │
│ ⏱️  Elapsed:            1 day, 4:30:15                                        │
│ 🕐 Est. Time:             2.0 days                                           │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Final Statistics

When the crawler finishes or is interrupted:

```
================================================================================
📊 FINAL STATISTICS
================================================================================
Total tokens collected: 100,000,000,000
Target tokens: 100,000,000,000
Progress: 100.00%
Repositories cloned: 50,000
Repositories failed (actual): 150
Repositories skipped (already processed): 10,000
Search queries completed: 386
Threshold expansions: 7
Final star threshold: 20
Total size: 3.50 TB
Total Python files: 5,000,000
================================================================================
```

## When Fully Exhausted

If you reach the minimum threshold (1+ stars) and all repos are processed:

```
================================================================================
🏁 SEARCH FULLY EXHAUSTED
================================================================================
Completed 386 queries
Threshold expansions: 10
Reached minimum star threshold: 1

All available ML/DL repositories have been processed.

Options to continue:
1. Wait for new repos to be created on GitHub
2. Manually edit threshold_levels to go even lower
3. Add more search topics to _generate_search_queries()
================================================================================
```

## Resumability

The expansion state is fully preserved:
- Stop anytime with Ctrl+C
- Run `./run_crawler.sh` to resume
- Continues at exact same threshold level
- No repos are re-processed
- All progress maintained

## No Manual Intervention Needed

The entire process is automatic:
- ✅ Detects when to expand
- ✅ Lowers threshold automatically
- ✅ Resets queries automatically
- ✅ Generates new queries automatically
- ✅ Continues crawling automatically
- ✅ Saves all state automatically

Just run `./run_crawler.sh` once and let it work toward 100B tokens!

## Customization

If you want to modify the threshold levels, edit `github_crawler.py`:

```python
# In __init__ method
self.star_threshold_levels = [5000, 2000, 1000, 500, 200, 100, 50, 20, 10, 5, 1]

# Change to whatever levels you want:
self.star_threshold_levels = [10000, 5000, 1000, 100, 10, 1]  # Fewer, bigger jumps
self.star_threshold_levels = [5000, 4000, 3000, 2000, 1000, 500, 100]  # Finer-grained
```

The crawler will automatically progress through whatever levels you define!


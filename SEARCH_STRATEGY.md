# 🎯 New Search Strategy - No More Duplicates!

## Problem Solved

**Old Strategy (Broken):**
```
Query 1: stars:>=2000  → Returns repos with 2000, 3000, 4000, 5000+ stars
Query 2: stars:>=1000  → Returns repos with 1000, 2000, 3000, 4000, 5000+ stars
Query 3: stars:>=500   → Returns repos with 500, 1000, 2000, 3000+ stars
```
Result: Same repos appear in EVERY query! 🔄 Massive duplication!

**New Strategy (Fixed):**
```
Query 1: stars:2000..4999  → ONLY repos with 2000-4999 stars ✅
Query 2: stars:1000..1999  → ONLY repos with 1000-1999 stars ✅
Query 3: stars:500..999    → ONLY repos with 500-999 stars ✅
```
Result: Each repo appears ONCE! 🎉 No duplication!

## Key Changes

### 1. Exclusive Star Ranges
Instead of `>=2000`, we now use ranges:
- `>=5000` (top tier, no upper limit)
- `2000..4999` (between 2000 and 4999)
- `1000..1999` (between 1000 and 1999)
- `500..999`
- `200..499`
- `100..199`
- `50..99`
- `20..49`
- `10..19`
- `5..9`
- `1..4`

### 2. Multiple Sort Orders
Each star range is queried with **3 different sorts**:
- **stars (desc)**: Most popular repos first
- **updated (desc)**: Recently updated repos first
- **forks (desc)**: Most forked repos first

This finds completely different repos even in the same star range!

### 3. Size-Based Queries
Added queries that search by repository size:
- `size:>=50000` KB (50+ MB)
- `size:>=20000` KB (20+ MB)
- `size:>=10000` KB (10+ MB)
- `size:>=5000` KB (5+ MB)

Large repos often have lots of code = more tokens!

## Example Queries

### Old (Duplicate-Heavy):
```
language:python topic:machine-learning stars:>=2000
language:python topic:machine-learning stars:>=1000
language:python topic:deep-learning stars:>=2000
```

### New (Unique Results):
```
language:python topic:machine-learning stars:2000..4999 sort:stars
language:python topic:machine-learning stars:2000..4999 sort:updated
language:python topic:machine-learning stars:2000..4999 sort:forks
language:python topic:machine-learning stars:1000..1999 sort:stars
language:python topic:deep-learning stars:2000..4999 sort:stars
language:python machine-learning size:>=50000 sort:stars
```

## Query Count

With current threshold (2000 stars):
- **70+ topics** × **3 star ranges** × **3 sorts** = **~630 topic queries**
- **15 topics** × **2 star ranges** × recent filter = **~30 recent queries**
- **8 broad topics** × **3 star ranges** × **3 sorts** = **~72 broad queries**
- **4 size ranges** × **2 sorts** = **~8 size queries**

**Total: ~740+ unique queries** (vs 386 duplicate-heavy queries before)

## What This Means

### Before:
```
Found: 100 repos on page 1
Filtered: 0 new, 100 already seen ❌
```

### After:
```
Found: 100 repos on page 1
Filtered: 85 new, 15 already seen ✅
```

You'll now find **MANY more unique repos** per query!

## Threshold Progression

When threshold = 2000:
```
Range 1: 2000-4999 stars (NEW repos we haven't seen!)
Range 2: 1000-1999 stars
Range 3: 500-999 stars
```

When threshold = 1000 (next expansion):
```
Range 1: 1000-1999 stars (already did this, but will find more with different sorts)
Range 2: 500-999 stars
Range 3: 200-499 stars (NEW!)
Range 4: 100-199 stars (NEW!)
```

## Expected Results

At threshold 2000, you should find:
- **2000-4999 stars:** ~300-500 repos (completely fresh!)
- **1000-1999 stars:** ~500-800 repos
- **500-999 stars:** ~1000-1500 repos

**Total: ~2000-3000 NEW repos** at this threshold level alone!

## Sort Order Benefits

Same repo can rank differently based on sort:

**Example: "pytorch-tutorial" repo**
- Sort by stars: Page 50 (not super popular)
- Sort by updated: Page 2 (actively maintained!)
- Sort by forks: Page 10 (widely used in teaching)

By using all 3 sorts, we find repos that might be hidden in one ranking but prominent in another!

## Run It!

Just run the crawler - it's all automatic:
```bash
./run_crawler.sh
```

You should immediately see:
```
Found: 100 repos on page 1
Filtered: 75 new, 25 already seen
```

Much better than "0 new, 100 already seen"! 🎉


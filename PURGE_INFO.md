# 🗑️ Non-Code File Purging

## What Changed

### ❌ Removed: Image Compression
- Deleted `compress_image()` function
- No longer compresses images - deletes them instead
- Removed Pillow dependency

### ✅ Added: Complete Purge
- New `purge_non_code_files()` function
- Deletes ALL non-code/non-text files
- Runs on EVERY repo (existing and new)

## Files That Will Be Deleted

### Images
`.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.svg`, `.ico`, `.webp`, `.tiff`, `.tif`

### Videos
`.mp4`, `.avi`, `.mov`, `.wmv`, `.flv`, `.mkv`, `.webm`, `.m4v`, `.mpeg`, `.mpg`

### Audio
`.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.wma`, `.m4a`, `.opus`

### Archives
`.zip`, `.tar`, `.gz`, `.bz2`, `.7z`, `.rar`, `.xz`

### Fonts
`.ttf`, `.otf`, `.woff`, `.woff2`, `.eot`

### Binaries/Executables
`.exe`, `.dll`, `.so`, `.dylib`, `.bin`, `.dat`

### Documents
`.pdf`, `.doc`, `.docx`, `.ppt`, `.pptx`

### Databases
`.db`, `.sqlite`, `.sqlite3`

### Other
`.DS_Store` (Mac files)

## Files That Are KEPT

### Code Files
`.py`, `.pyx`, `.pyi`, `.pyw`, `.ipynb` (Python)
`.js`, `.ts`, `.java`, `.cpp`, `.c`, `.h` (Other languages, for context)

### Text/Config Files
`.txt`, `.md`, `.rst` (Documentation)
`.json`, `.yaml`, `.yml`, `.toml`, `.cfg`, `.ini` (Config)
`.xml`, `.html`, `.css` (Markup/styles)

### Everything else stays (code files, configs, docs)

## Why This Matters

### Before (with compression):
- Images: Compressed to 70% quality, 800x800 max
- Other media: Kept as-is
- **Result:** Still wasting GB on non-code data

### After (with purge):
- All non-code files: **DELETED**
- **Result:** 30-50% disk space savings!

## Expected Savings

Based on your 637 GB dataset:
- **Estimated savings: 150-250 GB**
- Images/videos/PDFs in ML repos are common
- Especially in tutorial/course repos

## On Startup

When you run the crawler, it will:
1. Load all existing repos
2. Purge non-code files from ALL of them
3. Show progress:
```
🗑️  Purging non-code files from existing repos...
Found 10133 repositories
   huggingface_transformers: 52 files, 125.3 MB freed
   pytorch_pytorch: 187 files, 451.2 MB freed
   ...
✅ Purge complete: 45,821 files deleted, 187.3 GB freed
```

## New Repos

Every newly cloned repo will be purged automatically:
```
🔄 CLONING: owner/repo
✅ CLONED: owner/repo
📊 PROCESSING: owner/repo
   Files: 250 | Python: 45
   Tokens: 125,000 | Size: 1,245,678 bytes
   Purged: 32 non-code files (25,674,123 bytes freed)
```

## Query Results History

Now saving which repos came from which queries in `query_results.json`:

```json
{
  "language:python topic:pytorch stars:2000..4999|stars|desc|page1": {
    "query": "language:python topic:pytorch stars:2000..4999",
    "sort": "stars",
    "order": "desc",
    "page": 1,
    "repo_ids": ["123456", "789012", ...],
    "searched_at": "2025-11-14T13:15:30",
    "found_new": 85
  }
}
```

This prevents re-searching the same query and getting the same results.

## Benefits

1. **Disk Space:** Save 150-250 GB immediately
2. **Processing Speed:** Faster token counting (fewer files)
3. **Query Efficiency:** Never search same query twice
4. **Focus:** Only keep what matters - CODE!


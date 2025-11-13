# GitHub Python Repository Crawler

A robust, production-ready crawler for collecting 100B+ tokens of Python code from GitHub to create large-scale datasets for deep learning.

## Features

- 🔍 **Multi-Query Search**: Uses dozens of diverse search queries to maximize coverage
- 📊 **Token Tracking**: Real-time tokenization using tiktoken (cl100k_base)
- 💾 **Progress Persistence**: Saves progress continuously, resumable at any time
- 📝 **Comprehensive Logging**: Live logs to both console and file
- 🖼️ **Smart Compression**: Automatically compresses images and non-code data
- ⚡ **Rate Limit Handling**: Automatically handles GitHub API rate limits
- 🔄 **Resumable**: Can stop and resume without losing progress
- 📈 **Live Statistics**: Real-time progress updates and statistics

## Requirements

- Python 3.8+
- Git installed and in PATH
- GitHub Personal Access Token with `public_repo` scope
- Sufficient disk space (100B tokens ≈ several TB of data)

## Installation

```bash
# Clone this repository
git clone <repo-url>
cd PyRepoCrawlScripts

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Basic Usage

Simply run the crawler:

```bash
python3 github_crawler.py
```

The script is pre-configured with your GitHub token and will:
1. Search GitHub for Python repositories using multiple strategies
2. Clone repositories one by one with live logging
3. Tokenize all Python and text files
4. Compress images
5. Track progress in real-time
6. Save progress continuously

### Resume After Interruption

If interrupted (Ctrl+C or system crash), simply run the script again:

```bash
python3 github_crawler.py
```

It will automatically resume from where it left off.

## Output Structure

```
PyRepoCrawlScripts/
├── cloned_repos/          # All cloned repositories
│   ├── user_repo1/
│   ├── user_repo2/
│   └── ...
├── logs/                  # Detailed logs with timestamps
│   └── crawler_YYYYMMDD_HHMMSS.log
├── data/                  # Progress tracking
│   ├── progress.json      # Current progress state
│   └── repos_database.json # Database of all cloned repos
└── github_crawler.py      # Main script
```

## Progress Tracking

The crawler maintains two JSON files:

### `data/progress.json`
```json
{
  "total_tokens": 1234567890,
  "repos_cloned": 150,
  "repos_failed": 5,
  "start_time": "2025-11-13T...",
  "last_update": "2025-11-13T...",
  "search_queries_completed": [...],
  "current_page": {...}
}
```

### `data/repos_database.json`
Contains detailed information about each cloned repository:
- URL and local path
- Token count and file statistics
- Stars, forks, and size
- Clone timestamp

## Search Strategy

The crawler uses multiple search strategies to maximize Python code collection:

1. **Topic-Based**: Searches for repos with specific topics (ML, web dev, data science, etc.)
2. **Star-Based**: Searches repos by star count (1000+, 500+, 100+, etc.)
3. **Size-Based**: Targets larger repositories
4. **Sort-Based**: Sorts by stars, updates, and forks

This multi-query approach ensures comprehensive coverage of Python repositories.

## Monitoring

### Live Console Output

The crawler provides real-time updates:
- 🔄 Clone progress for each repository
- ✅ Successful clones
- ❌ Failed clones with error messages
- 📊 Token counts and file statistics
- 📈 Overall progress percentage
- 💾 Progress save confirmations

### Log Files

Detailed logs are saved in `logs/crawler_YYYYMMDD_HHMMSS.log` including:
- Timestamp for every operation
- Detailed error messages
- API responses
- Token counting details

## Performance Estimates

Based on typical GitHub Python repositories:

- **Average repo size**: ~10-50 MB
- **Average tokens per repo**: 100K - 1M tokens
- **Repos needed for 100B tokens**: ~100,000 - 1,000,000
- **Estimated time**: Days to weeks (depending on network speed)
- **Estimated disk space**: 1-10 TB

## Rate Limits

GitHub API rate limits:
- **Authenticated**: 5,000 requests/hour
- The crawler automatically handles rate limits and waits when necessary

## Troubleshooting

### "Permission denied" errors
- Ensure your GitHub token has `public_repo` scope
- Check token hasn't expired

### "Rate limit exceeded"
- The crawler automatically waits for rate limit reset
- You can reduce requests by modifying search queries

### Disk space issues
- Monitor disk space regularly
- Consider using external drives for storage
- Old repositories can be removed if needed (they're tracked in repos_database.json)

### Clone failures
- Some repos may be empty, deleted, or have access restrictions
- These are logged and skipped automatically

## Customization

Edit `github_crawler.py` to customize:

- **Target tokens**: Change `target_tokens` in `main()`
- **Search queries**: Modify `_generate_search_queries()`
- **File extensions**: Edit `code_extensions` and `text_extensions` in `process_repository()`
- **Compression settings**: Adjust image quality in `compress_image()`

## Safety Features

- ✅ Progress saved after every repository
- ✅ Duplicate detection (skips already-cloned repos)
- ✅ Error handling for network issues
- ✅ Graceful handling of interruptions (Ctrl+C)
- ✅ Rate limit respect

## Dataset Usage

Once complete, you'll have:
- 100B+ tokens of Python code
- Comprehensive metadata in JSON format
- All repositories organized in `cloned_repos/`
- Complete provenance tracking (URLs, stars, dates)

Perfect for:
- Training code language models
- Code analysis research
- Building code search engines
- Code generation model fine-tuning

## License

The crawler itself is provided as-is. Note that cloned repositories maintain their original licenses.

## Notes

- The script uses `--depth 1` for shallow clones to save space
- Images are compressed to 800x800 max with 70% quality
- Progress is saved after every repository to prevent data loss
- The tokenizer uses OpenAI's cl100k_base encoding

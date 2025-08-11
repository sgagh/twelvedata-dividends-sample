# Twelve Data Dividends Sample Extractor

A Python-based dividend and SEC reports data extractor that fetches financial data from the Twelve Data API for analysis and processing.

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Working Effectively

### Bootstrap and Setup
Follow these exact steps to set up the development environment:

1. **Create Python virtual environment** (takes ~3 seconds):
   ```bash
   python3.12 -m venv .venv
   ```

2. **Activate virtual environment**:
   ```bash
   source .venv/bin/activate  # On Linux/Mac
   # OR
   .venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies** (takes ~5-15 seconds with network access):
   ```bash
   pip install -r requirements.txt
   ```
   
   **IMPORTANT**: In sandboxed environments without network access, this command will fail with timeouts. The application requires `python-dotenv>=1.0.0` and `requests>=2.31.0`. If pip install fails due to network restrictions, document this limitation and note that the application cannot run without these dependencies.

4. **Set up environment configuration**:
   ```bash
   cp .env.example .env
   ```
   
5. **Configure API key**: Edit `.env` file and replace `your_twelve_data_api_key_here` with an actual Twelve Data API key.

### Validation and Testing

**ALWAYS run setup validation before using the application**:
```bash
python test_setup.py
```

This validation script checks:
- `.env` file exists and has valid API key
- `symbols.txt` file exists  
- API connectivity to Twelve Data
- Returns clear success/failure messages

**Expected validation outcomes**:
- ✅ With valid API key and network access: All tests pass
- ❌ Without API key: "TWELVE_DATA_API_KEY not set" error
- ❌ Without network access: API connectivity test fails

### Running the Application

**Basic usage**:
```bash
python extract_dividends.py <start_date> <end_date> [--limit <number>] [--debug]
```

**Required arguments**:
- `start_date`: Date in YYYY-MM-DD format (e.g., 2024-01-01)
- `end_date`: Date in YYYY-MM-DD format (e.g., 2024-12-31)

**Optional arguments**:
- `--limit`: Number of symbols to process (default: 0 = all 718 symbols)
- `--debug`: Enable detailed logging for API requests and responses

**Example commands**:
```bash
# Process first 5 symbols for Q1 2024
python extract_dividends.py 2024-01-01 2024-03-31 --limit 5

# Process all symbols for 2024 with debug logging
python extract_dividends.py 2024-01-01 2024-12-31 --debug

# Quick test with single symbol
python extract_dividends.py 2024-01-01 2024-01-31 --limit 1
```

### Performance and Timing

**NEVER CANCEL: Application timing expectations**:
- **Virtual environment creation**: 3 seconds
- **Dependency installation**: 5-15 seconds (with network access)
- **Single symbol processing**: 1-3 seconds per symbol (with API access)
- **10 symbols**: ~10-30 seconds  
- **Full symbol set (718 symbols)**: 30-60 minutes depending on API rate limits
- **NEVER CANCEL** API operations - set timeouts to 90+ minutes for full runs

**Timeout recommendations**:
- Development/testing (--limit 5): Set 5-minute timeout
- Medium runs (--limit 50): Set 15-minute timeout  
- Full production runs: Set 90-minute timeout

## Validation

**ALWAYS run these validation steps after making changes**:

1. **Syntax validation**:
   ```bash
   python -m py_compile extract_dividends.py
   python -m py_compile test_setup.py
   ```

2. **Setup validation**:
   ```bash
   python test_setup.py
   ```

3. **Functionality validation** (requires API key and network access):
   ```bash
   python extract_dividends.py 2024-01-01 2024-01-31 --limit 1
   ```

4. **Debug mode testing**:
   ```bash
   python extract_dividends.py 2024-01-01 2024-01-31 --limit 1 --debug
   ```

**Expected validation outputs**:
- Script creates `logs/extract_dividends_YYYYMMDD_HHMMSS.log` file
- Script creates `output/dividends_data_<start_date>_<end_date>.json` file
- With working API: JSON file contains symbol data arrays
- Without API access: JSON file contains empty array `[]`

**Manual validation scenarios**:
- **Test date validation**: Run with invalid date format (should fail with clear error)
- **Test API error handling**: Run without valid API key (should log clear error messages)
- **Test output structure**: Verify JSON output matches expected schema with `ticker`, `instrument_name`, `exchange`, `dividends`, and `sec_reports` fields

## Common Tasks

### Directory Structure
```
repo-root/
├── .env.example          # Environment template
├── .env                  # Your API configuration (created by setup)
├── .venv/               # Python virtual environment (created by setup)
├── extract_dividends.py # Main extraction script
├── test_setup.py        # Setup validation script
├── requirements.txt     # Python dependencies
├── symbols.txt          # 718 stock symbols to process
├── prompt.md            # Original project specification
├── Readme.md            # Project documentation
├── logs/                # Generated log files (created by script)
└── output/              # Generated JSON data files (created by script)
```

### Key Files and Their Purpose

**Core application files**:
- `extract_dividends.py`: Main script with comprehensive logging, API handling, and error management
- `test_setup.py`: Environment validation and API connectivity testing
- `symbols.txt`: Contains 718 stock symbols for dividend extraction

**Configuration files**:
- `requirements.txt`: Only 2 dependencies: `python-dotenv>=1.0.0` and `requests>=2.31.0`
- `.env.example`: Template for API key configuration

**Generated content** (excluded from git):
- `logs/`: Timestamped log files with detailed execution information
- `output/`: JSON files with extracted dividend and SEC report data
- `.venv/`: Python virtual environment directory

### Understanding the Application

**What it does**:
1. Loads stock symbols from `symbols.txt` (718 symbols)
2. For each symbol, fetches:
   - Stock information from Twelve Data `/stocks` endpoint
   - SEC reports from `/edgar_filings/archive` endpoint  
   - Dividend calendar data from `/dividends_calendar` endpoint
3. Analyzes SEC report files for dividend-related content
4. Exports structured JSON with dividend and SEC report data

**API Dependencies**:
- **Requires active internet connection** to api.twelvedata.com and sec.gov
- **Requires valid Twelve Data API key** (register at twelvedata.com)
- **Rate limited**: Processing all symbols may take 30-60 minutes due to API limits

**Network requirements**:
- Outbound HTTPS access to api.twelvedata.com (port 443)
- Outbound HTTPS access to sec.gov (port 443) 
- In sandboxed environments without network access, the application will fail with connection errors

### Troubleshooting

**Common issues and solutions**:

1. **"TWELVE_DATA_API_KEY not set"**: Edit `.env` file with valid API key
2. **"Failed to resolve api.twelvedata.com"**: Network connectivity issue - ensure internet access
3. **"pip install fails with timeout"**: Network restrictions prevent package downloads
4. **"Dates must be in YYYY-MM-DD format"**: Use correct date format (e.g., 2024-01-01)
5. **Empty JSON output**: Check API key validity and network connectivity

**Debug mode benefits**:
- Shows detailed API request/response information
- Logs request timing and performance metrics
- Provides stack traces for errors
- Helps diagnose API quota and rate limiting issues

### Development Notes

**No linting configured**: The project has no pre-configured linting tools like flake8, black, or pylint. Code follows standard Python conventions.

**Testing approach**: Use `test_setup.py` for environment validation and run small symbol sets (--limit 1-5) for development testing.

**Logging philosophy**: Comprehensive logging is built-in. The application creates timestamped log files and provides real-time console output. Always use --debug mode when troubleshooting.

**Error handling**: The application gracefully handles network failures, invalid API responses, and missing data. Failed symbols are logged but don't stop processing of remaining symbols.
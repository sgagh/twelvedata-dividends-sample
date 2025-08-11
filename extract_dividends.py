#!/usr/bin/env python3
"""
Script for extracting dividends and SEC reports data from the Twelve Data API
and creating a sample JSON file.
"""

import argparse
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
def setup_logging(debug: bool = False):
    """Setup logging configuration."""
    log_level = logging.DEBUG if debug else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=[
            logging.FileHandler(f'logs/extract_dividends_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

# Configuration
API_KEY = os.getenv('TWELVE_DATA_API_KEY')
BASE_URL = 'https://api.twelvedata.com'
SEC_BASE_URL = 'https://www.sec.gov/Archives/edgar/data/'

# User agents for SEC requests
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0'
]


def load_symbols(filename: str) -> List[str]:
    """Load symbols from the symbols.txt file."""
    with open(filename, 'r') as file:
        symbols = [line.strip() for line in file if line.strip()]
    return symbols


def make_api_request(endpoint: str, params: Dict, logger: logging.Logger) -> Optional[Dict]:
    """Make a request to the Twelve Data API."""
    if not API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY environment variable is required")
    
    params['apikey'] = API_KEY
    url = f"{BASE_URL}/{endpoint}"
    
    # Log the request details (without API key for security)
    safe_params = {k: v for k, v in params.items() if k != 'apikey'}
    logger.debug(f"Making API request to {endpoint}")
    logger.debug(f"URL: {url}")
    logger.debug(f"Parameters: {safe_params}")
    
    try:
        start_time = time.time()
        response = requests.get(url, params=params, timeout=30)
        request_duration = time.time() - start_time
        
        logger.debug(f"API request completed in {request_duration:.2f} seconds")
        logger.debug(f"Response status code: {response.status_code}")
        logger.debug(f"Response headers: {dict(response.headers)}")
        
        response.raise_for_status()
        data = response.json()
        
        # Log response summary
        if isinstance(data, dict):
            if 'data' in data:
                data_length = len(data['data']) if isinstance(data['data'], list) else 1
                logger.debug(f"Response contains {data_length} data items")
            if 'status' in data:
                logger.debug(f"API status: {data['status']}")
            if 'message' in data:
                logger.debug(f"API message: {data['message']}")
        
        logger.info(f"Successfully retrieved data from {endpoint}")
        return data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for {endpoint}: {e}")
        logger.debug(f"Request details - URL: {url}, Params: {safe_params}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from {endpoint}: {e}")
        logger.debug(f"Response content: {response.text[:500]}...")
        return None


def get_symbol_info(symbol: str, logger: logging.Logger) -> Optional[Dict]:
    """Retrieve symbol info from the /stocks endpoint."""
    logger.info(f"Getting symbol info for {symbol}")
    
    data = make_api_request('stocks', {'symbol': symbol}, logger)
    
    if not data or 'data' not in data or not data['data']:
        logger.warning(f"No data found for symbol {symbol}")
        return None
    
    stock_data = data['data'][0] if isinstance(data['data'], list) else data['data']
    
    result = {
        'name': stock_data.get('name', ''),
        'exchange': stock_data.get('exchange', '')
    }
    
    logger.debug(f"Symbol info for {symbol}: {result}")
    return result


def get_sec_reports(symbol: str, start_date: str, end_date: str, logger: logging.Logger) -> List[Dict]:
    """Retrieve SEC reports from the /edgar_filings/archive endpoint."""
    logger.info(f"Getting SEC reports for {symbol}")
    
    params = {
        'symbol': symbol,
        'filled_from': start_date,
        'filled_to': end_date
    }
    
    data = make_api_request('edgar_filings/archive', params, logger)
    
    if not data or 'data' not in data:
        logger.warning(f"No SEC reports found for {symbol}")
        return []
    
    logger.debug(f"Found {len(data['data'])} SEC reports for {symbol}")
    
    reports = []
    for i, report in enumerate(data['data']):
        logger.debug(f"Processing report {i+1}/{len(data['data'])} for {symbol}")
        
        if 'files' not in report:
            logger.debug(f"Report {i+1} has no files, skipping")
            continue
            
        # Process only .htm files
        htm_files = [f for f in report['files'] if f.get('url', '').endswith('.htm')]
        logger.debug(f"Found {len(htm_files)} .htm files in report {i+1}")
        
        if not htm_files:
            logger.debug(f"No .htm files found in report {i+1}, skipping")
            continue
            
        # Check each file for dividend content
        matched_files = []
        for j, file_info in enumerate(htm_files):
            file_url = file_info.get('url', '')
            if not file_url:
                logger.debug(f"File {j+1} has no URL, skipping")
                continue
                
            # Construct full URL
            full_url = SEC_BASE_URL + file_url
            logger.debug(f"Checking file {j+1}/{len(htm_files)}: {full_url}")
            
            # Download and check content
            if check_dividend_content(full_url, logger):
                matched_files.append({
                    'url': full_url,
                    'type': file_info.get('type', ''),
                    'mime': file_info.get('mime', 'text/html')
                })
                logger.debug(f"File {j+1} contains dividend content, added to results")
            else:
                logger.debug(f"File {j+1} does not contain dividend content, skipping")
        
        # Only include reports with matched files
        if matched_files:
            reports.append({
                'url': report.get('url', ''),
                'filed_at': report.get('filed_at', ''),
                'files': matched_files
            })
            logger.debug(f"Report {i+1} added with {len(matched_files)} matching files")
        else:
            logger.debug(f"Report {i+1} has no matching files, skipping")
    
    logger.info(f"Found {len(reports)} SEC reports with dividend content for {symbol}")
    return reports


def check_dividend_content(url: str, logger: logging.Logger) -> bool:
    """Check if a file contains the word 'dividend'."""
    try:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        logger.debug(f"Downloading content from: {url}")
        logger.debug(f"Using User-Agent: {headers['User-Agent']}")
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30)
        download_duration = time.time() - start_time
        
        logger.debug(f"Download completed in {download_duration:.2f} seconds")
        logger.debug(f"Response status: {response.status_code}, Content length: {len(response.text)} chars")
        
        response.raise_for_status()
        
        # Add delay after each request
        delay = random.uniform(1, 3)
        logger.debug(f"Adding delay of {delay:.2f} seconds")
        time.sleep(delay)
        
        # Search for 'dividend' in content (case-insensitive)
        content = response.text.lower()
        has_dividend = 'dividend' in content
        
        if has_dividend:
            logger.debug(f"✓ Found 'dividend' content in {url}")
        else:
            logger.debug(f"✗ No 'dividend' content found in {url}")
            
        return has_dividend
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download {url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while checking {url}: {e}")
        return False


def get_dividends(symbol: str, start_date: str, end_date: str, logger: logging.Logger) -> List[Dict]:
    """Load dividends for the symbol from the /dividends_calendar endpoint."""
    logger.info(f"Getting dividends for {symbol}")
    
    params = {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date
    }
    
    data = make_api_request('dividends_calendar', params, logger)
    
    if not data or 'data' not in data:
        logger.warning(f"No dividends found for {symbol}")
        return []
    
    dividends = data['data'] if isinstance(data['data'], list) else [data['data']]
    logger.info(f"Found {len(dividends)} dividend records for {symbol}")
    logger.debug(f"Dividend data for {symbol}: {dividends}")
    
    return dividends


def process_symbol(symbol: str, start_date: str, end_date: str, logger: logging.Logger) -> Optional[Dict]:
    """Process a single symbol and return its data."""
    logger.info(f"Processing symbol: {symbol}")
    
    # Get symbol info
    symbol_info = get_symbol_info(symbol, logger)
    if not symbol_info:
        logger.warning(f"Skipping {symbol} - no symbol info found")
        return None
    
    # Get SEC reports
    sec_reports = get_sec_reports(symbol, start_date, end_date, logger)
    
    # Get dividends
    dividends = get_dividends(symbol, start_date, end_date, logger)
    
    result = {
        'ticker': symbol,
        'instrument_name': symbol_info['name'],
        'exchange': symbol_info['exchange'],
        'dividends': dividends,
        'sec_reports': sec_reports
    }
    
    logger.info(f"Successfully processed {symbol}: {len(dividends)} dividends, {len(sec_reports)} SEC reports")
    logger.debug(f"Full result for {symbol}: {result}")
    
    return result


def main():
    """Main function to process all symbols and generate JSON output."""
    parser = argparse.ArgumentParser(description='Extract dividends and SEC reports data')
    parser.add_argument('start_date', help='Start date for API requests (YYYY-MM-DD)')
    parser.add_argument('end_date', help='End date for API requests (YYYY-MM-DD)')
    parser.add_argument('--limit', type=int, default=0, help='Limit symbols for processing (0 = no limit)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.debug)
    
    logger.info("Starting Twelve Data dividends extractor")
    logger.info(f"Date range: {args.start_date} to {args.end_date}")
    logger.info(f"Limit: {args.limit if args.limit > 0 else 'No limit'}")
    logger.info(f"Debug mode: {'Enabled' if args.debug else 'Disabled'}")
    
    # Validate date format
    try:
        datetime.strptime(args.start_date, '%Y-%m-%d')
        datetime.strptime(args.end_date, '%Y-%m-%d')
        logger.debug("Date format validation passed")
    except ValueError:
        logger.error("Dates must be in YYYY-MM-DD format")
        return 1
    
    # Load symbols
    try:
        symbols = load_symbols('symbols.txt')
        logger.info(f"Loaded {len(symbols)} symbols from symbols.txt")
        logger.debug(f"First 10 symbols: {symbols[:10]}")
    except FileNotFoundError:
        logger.error("symbols.txt file not found")
        return 1
    
    # Apply limit if specified
    if args.limit > 0:
        symbols = symbols[:args.limit]
        logger.info(f"Processing limited to {len(symbols)} symbols")
    
    # Process symbols
    results = []
    successful_count = 0
    failed_count = 0
    
    for i, symbol in enumerate(symbols, 1):
        logger.info(f"Progress: {i}/{len(symbols)} - Processing {symbol}")
        
        try:
            symbol_data = process_symbol(symbol, args.start_date, args.end_date, logger)
            if symbol_data:
                results.append(symbol_data)
                successful_count += 1
                logger.info(f"✓ Successfully processed {symbol}")
            else:
                failed_count += 1
                logger.warning(f"✗ Skipped {symbol}")
        except Exception as e:
            failed_count += 1
            logger.error(f"✗ Error processing {symbol}: {e}", exc_info=args.debug)
            continue
    
    # Export to JSON in output folder
    os.makedirs('output', exist_ok=True)
    output_filename = f"output/dividends_data_{args.start_date}_{args.end_date}.json"
    try:
        with open(output_filename, 'w') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Exported {len(results)} symbols to {output_filename}")
        logger.info(f"Processing complete! Success: {successful_count}, Failed: {failed_count}")
        
    except Exception as e:
        logger.error(f"Error writing to file: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())

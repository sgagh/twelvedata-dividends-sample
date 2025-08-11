#!/usr/bin/env python3
"""
Script for extracting dividends and SEC reports data from the Twelve Data API
and creating a sample JSON file.
"""

import argparse
import csv
import json
import logging
import os
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from faker import Faker

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

# Initialize faker instance
fake = Faker()

def generate_random_user_agent() -> str:
    """Generate a random user agent with fake name and email, similar to Go faker logic."""
    # Generate random person data
    first_name = fake.first_name()
    last_name = fake.last_name()
    email = fake.email()
    
    # Create user agent string (similar to Go example: FirstName LastName Email)
    user_agent = f"{first_name} {last_name} {email}"
    
    return user_agent


def load_symbols(filename: str) -> List[Tuple[str, str]]:
    """Load symbols and exchanges from the symbols.csv file."""
    symbols = []
    with open(filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        for row in csv_reader:
            symbol = row['symbol_ticker'].strip()
            exchange = row['exchange'].strip()
            if symbol and exchange:
                symbols.append((symbol, exchange))
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


def get_symbol_info(symbol: str, exchange: str, logger: logging.Logger) -> Optional[Dict]:
    """Retrieve symbol info from the /stocks endpoint."""
    logger.info(f"Getting symbol info for {symbol} on {exchange}")
    
    params = {'symbol': symbol, 'exchange': exchange}
    data = make_api_request('stocks', params, logger)
    
    if not data or 'data' not in data or not data['data']:
        logger.warning(f"No data found for symbol {symbol} on {exchange}")
        return None
    
    stock_data = data['data'][0] if isinstance(data['data'], list) else data['data']
    
    result = {
        'name': stock_data.get('name', ''),
        'exchange': stock_data.get('exchange', exchange)  # Use provided exchange as fallback
    }
    
    logger.debug(f"Symbol info for {symbol}: {result}")
    return result


def get_sec_reports(symbol: str, start_date: str, end_date: str, exchange:str, logger: logging.Logger) -> List[Dict]:
    """Retrieve SEC reports from the /edgar_filings/archive endpoint."""
    logger.info(f"Getting SEC reports for {symbol}")
    
    params = {
        'symbol': symbol,
        'filled_from': start_date,
        'filled_to': end_date,
        'exchange': exchange,
        'form_type': '8-K'
    }
    
    data = make_api_request('edgar_filings/archive', params, logger)
    
    # Edgar filings API returns data in 'values' array format as per documentation
    if not data or 'values' not in data:
        logger.warning(f"No SEC reports found for {symbol}")
        return []
    
    logger.debug(f"Found {len(data['values'])} SEC reports for {symbol}")
    
    reports = []
    for i, report in enumerate(data['values']):
        logger.debug(f"Processing report {i+1}/{len(data['values'])} for {symbol}")
        
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
            file_url = file_url.replace("/ix?doc=/Archives", "/Archives")
                
            # Use the full URL as provided by the API (no need to construct)
            logger.debug(f"Checking file {j+1}/{len(htm_files)}: {file_url}")
            
            # Download and check content
            if check_dividend_content(file_url, logger):
                matched_files.append({
                    'url': file_url,
                    'type': file_info.get('type', '')
                })
                logger.debug(f"File {j+1} contains dividend content, added to results")
            else:
                logger.debug(f"File {j+1} does not contain dividend content, skipping")
        
        # Only include reports with matched files
        if matched_files:
            # Convert timestamp to date string
            filed_at_timestamp = report.get('filed_at', 0)
            filed_at_date = datetime.fromtimestamp(filed_at_timestamp).strftime('%Y-%m-%d') if filed_at_timestamp else ''
            
            reports.append({
                'url': report.get('filing_url', ''),
                'filed_at': filed_at_date,
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
        # Generate a random user agent for this request
        user_agent = generate_random_user_agent()
        headers = {'User-Agent': user_agent}
        logger.debug(f"Downloading content from: {url}")
        logger.debug(f"Using User-Agent: {headers['User-Agent']}")
        
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=30)
        download_duration = time.time() - start_time
        
        logger.debug(f"Download completed in {download_duration:.2f} seconds")
        logger.debug(f"Response status: {response.status_code}, Content length: {len(response.text)} chars")
        
        response.raise_for_status()
        
        # Add delay after each request
        delay = 1.0
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


def get_dividends(symbol: str, start_date: str, end_date: str, exchange: str, logger: logging.Logger) -> List[Dict]:
    """Load dividends for the symbol from the /dividends_calendar endpoint."""
    logger.info(f"Getting dividends for {symbol}")
    
    params = {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'exchange': exchange
    }
    
    data = make_api_request('dividends_calendar', params, logger)
    
    # Dividends calendar API returns a flat array as per documentation
    if not data or not isinstance(data, list):
        logger.warning(f"No dividends found for {symbol}")
        return []
    
    # Filter dividends to match the symbol (API might return multiple symbols)
    symbol_dividends = [d for d in data if d.get('symbol') == symbol]
    
    # Filter fields to match the expected format (only ex_date, amount)
    filtered_dividends = []
    for dividend in symbol_dividends:
        filtered_dividend = {
            'ex_date': dividend.get('ex_date', ''),
            'amount': dividend.get('amount', 0)
        }
        filtered_dividends.append(filtered_dividend)
    
    logger.info(f"Found {len(filtered_dividends)} dividend records for {symbol}")
    logger.debug(f"Dividend data for {symbol}: {filtered_dividends}")
    
    return filtered_dividends


def process_symbol(symbol: str, exchange: str, start_date: str, end_date: str, logger: logging.Logger) -> Optional[Dict]:
    """Process a single symbol and return its data."""
    logger.info(f"Processing symbol: {symbol} on {exchange}")
    
    # Get symbol info
    symbol_info = get_symbol_info(symbol, exchange, logger)
    if not symbol_info:
        logger.warning(f"Skipping {symbol} - no symbol info found")
        return None
    
    # Use the exchange from symbol_info (which uses CSV exchange as fallback)
    actual_exchange = symbol_info['exchange']
    
    # Get SEC reports
    sec_reports = get_sec_reports(symbol, start_date, end_date, actual_exchange, logger)
    if not sec_reports:
        return None
    
    # Get dividends
    dividends = get_dividends(symbol, start_date, end_date, actual_exchange, logger)
    if not dividends:
        return None
    
    result = {
        'ticker': symbol,
        'instrument_name': symbol_info['name'],
        'exchange': actual_exchange,
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
        symbols = load_symbols('symbols.csv')
        logger.info(f"Loaded {len(symbols)} symbols from symbols.csv")
        logger.debug(f"First 10 symbols: {symbols[:10]}")
    except FileNotFoundError:
        logger.error("symbols.csv file not found")
        return 1
    
    # Apply limit if specified
    if args.limit > 0:
        symbols = symbols[:args.limit]
        logger.info(f"Processing limited to {len(symbols)} symbols")
    
    # Process symbols
    results = []
    successful_count = 0
    failed_count = 0
    
    for i, (symbol, exchange) in enumerate(symbols, 1):
        logger.info(f"Progress: {i}/{len(symbols)} - Processing {symbol} on {exchange}")
        
        try:
            symbol_data = process_symbol(symbol, exchange, args.start_date, args.end_date, logger)
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

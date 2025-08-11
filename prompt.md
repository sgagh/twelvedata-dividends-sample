# Goal
Create a script for extracting dividends and SEC reports data from the Twelve Data API and create a sample JSON file.

# Technologies
Python 3.12+

Python libraries:
- dontenv (for store API key)
- requests (for API requests)

# Resources
Twelve Data API docs https://twelvedata.com/docs

# Instructions
The script should accept the following arguments:
- start_date (required) - start date for API requests 
- end_date (required)- end date for API requests
- limit (not required, default 0) - limit symbols for processing

First of all, load all symbols that have dividends from symbols.txt.

For each symbol from this list:
1. Retrieve symbol info from the `/stocks` endpoint. If the result is empty, skip this ticker. Remember instrument name and exchange from the response.
2. Retrieve symbol SEC reports from the `/edgar_filings/archive` endpoint, restrict `filled_from` and `filled_to` based on input arguments.
3. For each report, analyze related files: 
- process only files with path ending ".htm"
- add the base url `https://www.sec.gov/Archives/edgar/data/` to the file url
- load file content from SEC using request, use a random user agent for each request, add a delay after each request
- find string "dividend" in the loaded content, and if not found, skip file
1. If there are no matched files, skip report
2. Add report and matched files to the symbol result
3. Load dividends for the symbol from the `/dividends_calendar` endpoint, restrict `start_date` and `end_date` based on input arguments, include the `exchange` parameter from the symbol info retrieved in step 1, add the response to the symbol result.
4. Add symbol data to the result list

After processing all symbols, export data to the JSON file with format explained below


# Output sample for one instrument
```json
[
{
  "ticker": "WASH",
  "instrument_name": "Washington Trust Bancorp Inc.",
  "exchange": "NASDAQ",
  "dividends": [
    {
      "symbol": "WASH",
      "mic_code": "XNGS",
      "exchange": "NASDAQ",
      "ex_date": "2025-07-01",
      "amount": 0.56
    },
    {
      "symbol": "WASH",
      "mic_code": "XNGS",
      "exchange": "NASDAQ",
      "ex_date": "2025-04-01",
      "amount": 0.56
    },
    {
      "symbol": "WASH",
      "mic_code": "XNGS",
      "exchange": "NASDAQ",
      "ex_date": "2025-01-02",
      "amount": 0.56
    }
  ],
  "sec_reports": [
    {
      "url": "https://www.sec.gov/Archives/edgar/data/737468/0000737468-25-000031-index.htm",
      "filed_at": "2025-07-21",
      "files": [
        {
          "url": "737468/000073746825000031/exhibit9912025q2.htm",
          "type": "EX-99.1",
          "mime": "text/html"
        }
      ]
    },
    {
      "url": "https://www.sec.gov/Archives/edgar/data/737468/0000737468-25-000019-index.htm",
      "filed_at": "2025-04-21",
      "files": [
        {
          "url": "https://www.sec.gov/Archives/edgar/data/737468/000073746825000019/exhibit9912025q1.htm",
          "type": "EX-99.1",
          "mime": "text/html"
        }
      ]
    }
  ]
}
]
```
# E-commerce Price Scraper

This Python application fetches publicly available product prices from multiple online marketplaces and exports the results to an Excel file for easy reference.

## Features

- Retrieves product names, prices, and links from various regional e-commerce websites (e.g., US, UK, Germany, France, etc.)
- Uses asynchronous requests for faster data collection
- Generates Excel reports with clickable hyperlinks
- Simple command-line interface with customizable options
- Includes error handling and logging

## Dependencies

- aiohttp
- pandas
- beautifulsoup4
- openpyxl

## Installation

1. Clone the repository:

```bash
git clone https://github.com/muhammedmed/ecommerce-price-scraper.git
cd ecommerce-price-scraper
```

2. Install the required packages:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```bash
py price_scraper.py "Product Name"
```

Example:

```bash
py price_scraper.py "PS5"
```

This will:
1. Search for "PS5" in the default region
2. Collect up to 5 product prices (default limit)
3. Save the results to an Excel file with a timestamp
4. Automatically open the Excel file (on Windows)

### Advanced Options

```bash
py price_scraper.py "Product Name" --max-products 10 --regions us uk de --output results.xlsx
```

Available parameters:
- `--max-products` or `-m`: Maximum number of products to fetch per region (default: 5)
- `--regions` or `-r`: Regions to search (choices: us, uk, de, fr, it, es, au; default: us)
- `--output` or `-o`: Custom output Excel file name

## Example Output

The generated Excel file includes:
- Product names
- Prices
- Source site
- Clickable links to the original product pages

## Notes

- This script retrieves publicly available data from e-commerce websites. If a website changes its structure, the scraper may require updates.
- Excessive requests to a website may result in temporary access limitations.
- Users are responsible for complying with all applicable website terms of service and legal regulations when using this tool.

## Legal Disclaimer

This tool is for educational and research purposes only. It is not affiliated with, endorsed by, or approved by any e-commerce platform. Users must ensure compliance with relevant terms of service and legal requirements.

## License

MIT


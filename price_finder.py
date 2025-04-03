import argparse
import asyncio
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from urllib.parse import quote_plus

import aiohttp
import pandas as pd
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Type definitions
@dataclass
class Product:
    """Data class to store product information."""
    name: str
    price: str
    url: str
    site: str

class EbayPriceScraper:
    """Scrapes product prices from eBay."""
    
    # Class constants
    EBAY_SITES = {
        'us': 'ebay.com',
        'uk': 'ebay.co.uk',
        'de': 'ebay.de',
        'fr': 'ebay.fr',
        'it': 'ebay.it',
        'es': 'ebay.es',
        'au': 'ebay.com.au'
    }
    
    # Single reliable user agent is sufficient for most cases
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    
    def __init__(self, max_products: int = 5, regions: Optional[List[str]] = None):
        """Initialize the scraper with configuration."""
        self.max_products = max_products
        self.regions = regions or ['us']
    
    def _get_headers(self) -> dict:
        """Generate headers for requests."""
        return {
            'User-Agent': self.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    async def _extract_product_data(self, card, region: str) -> Optional[Product]:
        """Extract product information from a card element."""
        try:
            # Skip sponsored or special items
            if 'srp-river-answer' in card.get('class', []):
                return None
            
            # Extract title
            title_element = card.select_one('div.s-item__title span')
            if not title_element or 'New Listing' in title_element.text:
                return None
                
            name = title_element.text.strip()
            # Skip "Shop on eBay" ads
            if name == "Shop on eBay" or "shop on ebay" in name.lower():
                return None
            
            # Extract price
            price_element = card.select_one('.s-item__price')
            if not price_element or 'to' in price_element.text.lower():  # Skip price ranges
                return None
            price = price_element.text.strip()
            
            # Extract URL
            link_element = card.select_one('a.s-item__link')
            if not link_element or not link_element.get('href'):
                return None
            url = link_element['href']  # Keep original URL intact
            
            # Return product if all information is valid
            if name and price and url and len(name) > 5:  # Skip very short names
                return Product(
                    name=name,
                    price=price,
                    url=url,
                    site=f"eBay ({region.upper()})"
                )
            return None
            
        except Exception:
            # Less verbose error handling
            return None
    
    async def _search_region(self, session: aiohttp.ClientSession, query: str, region: str) -> List[Product]:
        """Search for products in a specific eBay region."""
        try:
            ebay_domain = self.EBAY_SITES.get(region, 'ebay.com')
            url = f"https://www.{ebay_domain}/sch/i.html?_nkw={quote_plus(query)}&_ipg=100"  # Show 100 items per page
            
            async with session.get(url, headers=self._get_headers()) as response:
                response.raise_for_status()
                html = await response.text()
                
                soup = BeautifulSoup(html, 'html.parser')
                product_cards = soup.select('div.s-item__wrapper')
                
                if not product_cards:
                    logger.warning(f"No product cards found on eBay {region}.")
                    return []
                
                # Process cards concurrently
                tasks = [
                    self._extract_product_data(card, region)
                    for card in product_cards[:self.max_products]
                ]
                products = await asyncio.gather(*tasks)
                
                # Filter out None values
                valid_products = [p for p in products if p is not None]
                
                logger.info(f"Extracted {len(valid_products)} products from eBay {region}")
                return valid_products
                
        except Exception as e:
            logger.error(f"Error searching eBay {region}: {e}")
            return []
    
    async def search(self, query: str) -> List[Product]:
        """Search for products on multiple eBay sites concurrently."""
        logger.info(f"Searching for '{query}' on {len(self.regions)} eBay sites...")
        
        async with aiohttp.ClientSession() as session:
            tasks = [
                self._search_region(session, query, region)
                for region in self.regions
            ]
            results = await asyncio.gather(*tasks)
            
            # Flatten results
            all_products = [p for products in results for p in products]
            
            return all_products

class ExcelExporter:
    """Handles exporting data to Excel files."""
    
    def export(self, products: List[Product], query: str, output_file: Optional[str] = None) -> str:
        """Export products to an Excel file."""
        if not products:
            raise ValueError("No products to export")
        
        # Prepare data for Excel
        data = [{
            'Product Name': p.name,
            'Price': p.price,
            'Site': p.site,
            'Link': ''  # Will be filled with formulas later
        } for p in products]
        
        df = pd.DataFrame(data)
        
        # Generate output filename if none provided
        if not output_file:
            # Simplified filename - uses query and timestamp
            sanitized_query = re.sub(r'[^\w\s]', '', query).replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{sanitized_query}_{timestamp}.xlsx"
        
        try:
            # Save to Excel with multiple sheets
            with pd.ExcelWriter(output_file, engine='openpyxl', mode='w') as writer:
                # First write the DataFrame
                df.to_excel(writer, sheet_name='Products', index=False)
                
                # Get worksheet
                worksheet = writer.sheets['Products']
                
                # Add formulas for links
                for idx, product in enumerate(products, start=2):  # Excel rows start at 1, header is row 1
                    cell = worksheet.cell(row=idx, column=4)  # Column D is the Link column
                    cell.value = f'=HYPERLINK("{product.url}","View Product")'
                
                # Adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column = list(column)
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = (max_length + 2)
                    worksheet.column_dimensions[column[0].column_letter].width = adjusted_width
        
        except PermissionError:
            # If file is locked, save with a new name
            base, ext = os.path.splitext(output_file)
            output_file = f"{base}_new{ext}"
            logger.warning(f"Original file was locked, saving as: {output_file}")
            return self.export(products, query, output_file)
        
        logger.info(f"Successfully saved {len(products)} products to {output_file}")
        return output_file

async def main():
    """Main function to run the price comparison tool."""
    parser = argparse.ArgumentParser(
        description="Compare product prices from multiple eBay sites.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('query', help='Product name to search for')
    parser.add_argument('--output', '-o', help='Output Excel file name')
    parser.add_argument('--max-products', '-m', type=int, default=5,
                       help='Maximum number of products to fetch per region')
    parser.add_argument('--regions', '-r', nargs='+', choices=EbayPriceScraper.EBAY_SITES.keys(),
                       default=['us'], help='eBay regions to search')
    
    args = parser.parse_args()
    
    try:
        # Initialize scraper and exporter
        scraper = EbayPriceScraper(max_products=args.max_products, regions=args.regions)
        exporter = ExcelExporter()
        
        # Search for products
        products = await scraper.search(args.query)
        
        if not products:
            logger.warning("No products found. Try a different search term.")
            return 1
        
        # Export to Excel
        output_file = exporter.export(products, args.query, args.output)
        
        # Report success to user
        print(f"Success! Found {len(products)} products. Results saved to: {output_file}")
            
        # Open Excel file if on Windows and file exists
        if os.name == 'nt' and os.path.exists(output_file):
            try:
                os.startfile(output_file)
            except Exception as e:
                logger.debug(f"Could not open Excel file: {e}")
                # Not critical if file opening fails
    
    except Exception as e:
        logger.error(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
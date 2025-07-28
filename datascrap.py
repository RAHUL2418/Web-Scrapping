import csv
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup

# Configuration
SEARCH_TERM = "Electronics"
ZIP_CODE = "10001"
RADIUS = "100"
MIN_RESULTS = 3
OUTPUT_CSV = "recycling_facilities.csv"

def setup_driver():
    """Setup Chrome driver with robust options"""
    options = Options()
    
    # Essential Chrome options for stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Disable logs
    options.add_argument("--log-level=3")
    options.add_argument("--silent")
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # Create service
    service = Service()
    
    try:
        driver = webdriver.Chrome(options=options, service=service)
        driver.set_page_load_timeout(45)
        driver.implicitly_wait(10)
        return driver
    except Exception as e:
        print(f"Failed to create Chrome driver: {e}")
        return None

def extract_facilities_from_text(html_content):
    """Extract facility data from the HTML content using text parsing"""
    facilities = []
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: Look for specific patterns in the text
    text_content = soup.get_text()
    
    # Split by phone numbers to separate facilities
    phone_pattern = r'\(\d{3}\)\s*\d{3}-\d{4}'
    sections = re.split(phone_pattern, text_content)
    phones = re.findall(phone_pattern, text_content)
    
    # Process each section with its phone
    for i, section in enumerate(sections[1:], 0):  # Skip first empty section
        try:
            lines = [line.strip() for line in section.split('\n') if line.strip()]
            
            if not lines:
                continue
                
            # Extract facility info
            facility = {
                "business_name": "N/A",
                "last_update_date": "N/A", 
                "street_address": "N/A",
                "materials_accepted": "N/A"
            }
            
            # Get phone number
            phone = phones[i] if i < len(phones) else "N/A"
            
            # Find address (usually after phone number)
            address_lines = []
            materials_started = False
            
            for line in lines[:10]:  # Check first 10 lines
                # Skip empty lines and common headers
                if not line or line.startswith('Materials accepted:'):
                    materials_started = True
                    continue
                    
                if materials_started:
                    break
                    
                # Check if it's an address (contains street number and street name)
                if re.search(r'\d+\s+[A-Za-z\s]+(St|Ave|Avenue|Street|Rd|Road|Blvd|Boulevard|Dr|Drive)', line):
                    address_lines.append(line)
                elif re.search(r'New York, NY \d{5}', line):
                    address_lines.append(line)
            
            # Combine address lines
            if address_lines:
                facility["street_address"] = ", ".join(address_lines)
            
            # Extract materials
            materials_section = section.split('Materials accepted:')
            if len(materials_section) > 1:
                materials_text = materials_section[1].split('For residents')[0].split('(')[0]
                materials_list = [m.strip() for m in materials_text.replace('\n', ' ').split() if m.strip()]
                # Clean up materials list
                cleaned_materials = []
                for material in materials_list:
                    if material and not re.match(r'^\+\d+', material) and material != 'more':
                        cleaned_materials.append(material)
                
                if cleaned_materials:
                    facility["materials_accepted"] = " ".join(cleaned_materials[:10])  # Limit length
            
            # Try to find business name (often the first substantial line or inferred from context)
            potential_names = []
            for line in lines[:5]:
                if (line and len(line) > 5 and 
                    not re.search(phone_pattern, line) and
                    not re.search(r'New York, NY', line) and
                    not line.startswith('Materials accepted:') and
                    not line.isdigit()):
                    potential_names.append(line)
            
            if potential_names:
                facility["business_name"] = potential_names[0][:50]  # Limit length
            else:
                # Generate name from address or materials
                if facility["street_address"] != "N/A":
                    street_match = re.search(r'(\d+\s+[A-Za-z\s]+(?:St|Ave|Avenue|Street))', facility["street_address"])
                    if street_match:
                        facility["business_name"] = f"Recycling Center at {street_match.group(1)}"
                elif facility["materials_accepted"] != "N/A":
                    facility["business_name"] = "Electronics Recycling Center"
                else:
                    facility["business_name"] = f"Recycling Facility {i+1}"
            
            # Only add if we have meaningful data
            if (facility["street_address"] != "N/A" or 
                facility["materials_accepted"] != "N/A"):
                facilities.append(facility)
                print(f"Extracted: {facility['business_name']}")
                
        except Exception as e:
            print(f"Error processing facility {i}: {e}")
            continue
    
    # Method 2: Try alternative parsing if Method 1 didn't work well
    if len(facilities) < 2:
        print("Trying alternative parsing method...")
        
        # Look for div elements that might contain facility info
        all_divs = soup.find_all(['div', 'section', 'article'])
        
        for div in all_divs:
            text = div.get_text(strip=True)
            if ('Materials accepted:' in text and 
                re.search(phone_pattern, text) and
                len(text) > 100):
                
                # Process this div as a potential facility
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                
                facility = {
                    "business_name": f"Facility at {lines[0][:30]}..." if lines else "Unknown Facility",
                    "last_update_date": "N/A",
                    "street_address": "N/A", 
                    "materials_accepted": "N/A"
                }
                
                # Extract phone and address
                phone_match = re.search(phone_pattern, text)
                if phone_match:
                    phone_line = phone_match.group()
                    
                # Look for address
                for line in lines:
                    if re.search(r'\d+\s+[A-Za-z\s]+(St|Ave|Street|Road)', line):
                        facility["street_address"] = line
                        break
                
                # Extract materials
                if 'Materials accepted:' in text:
                    materials_part = text.split('Materials accepted:')[1].split('For residents')[0]
                    materials_part = materials_part.split('(')[0][:200]  # Limit length
                    facility["materials_accepted"] = materials_part.strip()
                
                if facility["street_address"] != "N/A":
                    facilities.append(facility)
                    print(f"Alt method - Extracted: {facility['business_name']}")
                    
                if len(facilities) >= MIN_RESULTS:
                    break
    
    return facilities

def save_to_csv(data, filename):
    """Save data to CSV file"""
    if not data:
        print("No data to save!")
        return False
    
    try:
        with open(filename, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["business_name", "last_update_date", "street_address", "materials_accepted"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"\nSuccessfully saved {len(data)} records to '{filename}'")
        
        # Print preview of data
        print(f"\n=== CSV PREVIEW ===")
        for i, facility in enumerate(data, 1):
            print(f"{i}. {facility['business_name']}")
            print(f"   Address: {facility['street_address']}")
            print(f"   Materials: {facility['materials_accepted'][:80]}...")
            print(f"   Last Update: {facility['last_update_date']}")
            print()
        
        return True
    except Exception as e:
        print(f"Error saving to CSV: {e}")
        return False

def main():
    """Main scraping function"""
    print("Starting Earth911 Recycling Facility Scraper...")
    print(f"Searching for: {SEARCH_TERM} near {ZIP_CODE} within {RADIUS} miles")
    
    # Setup driver
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver. Please check your Chrome installation.")
        return
    
    try:
        # Construct URL
        url = f"https://search.earth911.com/?what={SEARCH_TERM}&where={ZIP_CODE}&list_filter={RADIUS}"
        print(f"\nNavigating to: {url}")
        
        # Navigate to page
        try:
            driver.get(url)
            print("Page loaded successfully")
        except TimeoutException:
            print("Page load timeout, but continuing...")
        
        # Wait a bit for dynamic content
        print("Waiting for page content to load...")
        time.sleep(8)
        
        # Try to handle any popups or overlays
        try:
            # Close any modal or popup
            close_buttons = driver.find_elements(By.CSS_SELECTOR, 
                "[class*='close'], [class*='dismiss'], [aria-label*='close'], [aria-label*='Close']")
            for btn in close_buttons:
                try:
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(1)
                except:
                    pass
        except:
            pass
        
        # Get page source
        html_content = driver.page_source
        
        # Save debug HTML
        with open("debug_page_source.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("Saved page source to debug_page_source.html")
        
        # Extract facilities
        print("\nExtracting facility data...")
        facilities = extract_facilities_from_text(html_content)
        
        if facilities:
            # Limit to required number of results
            facilities = facilities[:MIN_RESULTS]
            
            # Save to CSV
            save_to_csv(facilities, OUTPUT_CSV)
            
            print(f"\n=== SCRAPING COMPLETED SUCCESSFULLY ===")
            print(f"Total facilities extracted: {len(facilities)}")
            print(f"Output file: {OUTPUT_CSV}")
            
        else:
            print("\nNo facility data was extracted.")
            print("Please check the debug_page_source.html file to see what was loaded.")
            
            # Try to give some hints about what went wrong
            if "No results found" in html_content.lower():
                print("Hint: The search returned no results. Try different search parameters.")
            elif len(html_content) < 1000:
                print("Hint: Page content seems minimal. There might be a loading issue.")
            else:
                print("Hint: Page loaded but structure might have changed. Check debug HTML file.")
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            driver.quit()
        except:
            pass
        print("\nScraper finished.")

if __name__ == "__main__":
    main()
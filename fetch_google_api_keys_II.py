import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import os
import re
import random
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE", 'kristiyansimeonov-de6f501229f3.json')
SPREADSHEET_ID_II = os.getenv("SPREADSHEET_ID_II", "1GmsJHIFgYWe0W9VHRMzgpuyhTWXdkdUlWgg8O3QN2Uw")
SHEET_TAB_II = os.getenv("SHEET_TAB_II", "Sheet6")
# Define scopes and authorize credentials
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)

# Select the spreadsheet and worksheet
spreadsheet = gc.open_by_key(SPREADSHEET_ID_II)
worksheet = spreadsheet.worksheet(SHEET_TAB_II)  # You can change this to any tab

# Load records
data = worksheet.get_all_records()

# Headers for requests
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    'priority': 'u=0, i',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1'
}
# Helper: Get column letter by name
def get_col_letter(name):
    idx = list(data[0].keys()).index(name) + 1
    return gspread.utils.rowcol_to_a1(1, idx)[0], idx

# Helper: Color a cell
def set_cell_background_color(row, col_letter, color):
    # Check if color is a string (status) or a color dict
    if isinstance(color, str):
        # Try to find a matching color based on the status
        for status_key, color_value in colors.items():
            if status_key in color:
                color = color_value
                break
        else:
            # Default to grey if no match is found
            color = colors["Bad Request"]
    worksheet.format(f"{col_letter}{row}", {"backgroundColor": color})

# Helper: Normalize URL for comparison
def normalize_url(url):
    """Normalize URLs for more flexible matching."""
    if not url:
        return ""
    
    # Remove protocol prefix (http://, https://)
    url = re.sub(r'^https?://', '', url.lower())
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # Remove 'www.' prefix if present
    url = re.sub(r'^www\.', '', url)
    
    return url

# Helper: Check if one URL is contained in another
def is_url_match(target_url, article_link):
    """Check if target_url is contained within article_link using path-based matching."""
    if not target_url or not article_link:
        return False
        
    norm_target = normalize_url(target_url)
    norm_article = normalize_url(article_link)
    
    # Check if normalized URLs are an exact match
    if norm_target == norm_article:
        return True
    
    # Check if the target's domain and path are contained in the article link
    # Extract domains to check for domain match
    target_domain = urlparse('http://' + norm_target).netloc or norm_target.split('/')[0]
    article_domain = urlparse('http://' + norm_article).netloc or norm_article.split('/')[0]
    
    # If domains match, check if the path is contained
    if target_domain == article_domain:
        target_path = '/'.join(norm_target.split('/')[1:]) if '/' in norm_target else ''
        article_path = '/'.join(norm_article.split('/')[1:]) if '/' in norm_article else ''
        
        # Check if target path is in article path or vice versa
        return (target_path in article_path) or (article_path in target_path)
    
    # Check if full target URL is contained in article URL
    return norm_target in norm_article

# Status colors
colors = {
    "Live": {"red": 0.0, "green": 1.0, "blue": 0.0},        # Green
    "Not Found": {"red": 1.0, "green": 0.0, "blue": 0.0},   # Red
    "Bad Request": {"red": 0.7, "green": 0.7, "blue": 0.7},  # Grey
    "Connection Error": {"red": 1.0, "green": 0.6, "blue": 0.0}  # Orange
}

# Load proxies
proxy_list = []
try:
    with open('proxy.txt', 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split(':')
                if len(parts) == 4:  # Format: IP:PORT:USERNAME:PASSWORD
                    proxy = f"http://{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                    proxy_list.append(proxy)
    print(f"Loaded {len(proxy_list)} proxies")
except Exception as e:
    print(f"Warning: Could not load proxies: {str(e)}")

# Process each row
for idx, row in enumerate(data, start=2):  # Row 6 = data row 1
    article_url = row.get("URL")
    target_url = row.get("Search for these URLs")
    
    # Select a proxy if available
    proxy = None
    if proxy_list:
        proxy = random.choice(proxy_list)
        proxies = {"http": proxy, "https": proxy}

    try:
        # Make request with proxy if available
        if proxy_list:
            response = requests.get(article_url, headers=headers, proxies=proxies, timeout=20)
            print(f"Row {idx}: Using proxy {proxy.split('@')[1] if '@' in proxy else proxy}")
        else:
            response = requests.get(article_url, headers=headers, timeout=20)
            
        if response.status_code != 200:
            status = f"Bad Request ({response.status_code})"
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            links = [a['href'] for a in soup.find_all('a', href=True)]
            
            # Check if any link matches the target URL using our smart matching function
            matched_links = [link for link in links if is_url_match(target_url, link)]
            status = "Live" if matched_links else "Not Found"
            
            print(f"Row {idx}: {'MATCHED' if matched_links else 'NO MATCH'} - {article_url} -> {target_url}")
            if matched_links:
                print(f"  Matched with: {matched_links[0]}" + (f" and {len(matched_links)-1} others" if len(matched_links) > 1 else ""))
            print(f"  Found {len(links)} links on page")
    except requests.exceptions.ConnectionError:
        status = "Connection Error"
    except Exception as e:
        status = f"Bad Request ({str(e)[:30]})"
    finally:
        print(f"Processed row {idx}/{len(data)}")

    # Write Status
    status_col_letter, status_col_idx = get_col_letter("Status")
    worksheet.update_cell(idx, status_col_idx, status)
    set_cell_background_color(idx, status_col_letter, status)
    time.sleep(1)

    # Write Last scan date
    scan_col_letter, scan_col_idx = get_col_letter("Last scan date")
    kyiv_time = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M:%S")
    worksheet.update_cell(idx, scan_col_idx, kyiv_time)
    time.sleep(1)

print("✅ Scanning complete.")
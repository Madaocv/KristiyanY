import gspread
from google.oauth2.service_account import Credentials
import requests
from pprint import pformat
from bs4 import BeautifulSoup
from datetime import datetime

API_KEY = "*"
SEARCH_ENGINE_ID = "*"
BASE_URL = "https://www.googleapis.com/customsearch/v1"
SERVICE_ACCOUNT_FILE = "kristiyansimeonov-de6f501229f3.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1GmsJHIFgYWe0W9VHRMzgpuyhTWXdkdUlWgg8O3QN2Uw"
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet("AB Script")
articles = worksheet.col_values(1)
target = worksheet.col_values(2)

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
}
# Read all data
data = worksheet.get_all_records()

# Helper function to update cell background color
def set_cell_background_color(row, col, color):
    worksheet.format(f"{col}{row}", {"backgroundColor": color})

# Process rows
for idx, row in enumerate(data, start=2):  # Start at row 2 (header is row 1)
    article = row["Article"]
    target = row["Target URL"]
    status = row["Status"]
    if not status or status.strip().lower() == "false":
        try:
            response = requests.get(article, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True)]
            if target in links:
                worksheet.update_cell(idx, 4, "True")
                set_cell_background_color(idx, 'D', {"red": 0.0, "green": 1.0, "blue": 0.0})
            else:
                worksheet.update_cell(idx, 4, "False")
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        except requests.RequestException as e:
            print(f"Error processing URL {article}: {e}")
            worksheet.update_cell(idx, 4, "False")
            set_cell_background_color(idx, 'D', {"red": 1.0, "green": 0.0, "blue": 0.0})
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print(f'Scraping finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Total URLs processed {len(data)-1}')
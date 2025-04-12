import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import os
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
    worksheet.format(f"{col_letter}{row}", {"backgroundColor": color})

# Status colors
colors = {
    "Live": {"red": 0.0, "green": 1.0, "blue": 0.0},        # Green
    "Not Found": {"red": 1.0, "green": 0.0, "blue": 0.0},   # Red
    "Bad Request": {"red": 0.7, "green": 0.7, "blue": 0.7}  # Grey
}

# Process each row
for idx, row in enumerate(data, start=2):  # Row 6 = data row 1
    article_url = row.get("URL")
    target_url = row.get("Search for these URLs")

    try:
        response = requests.get(article_url, headers=headers, timeout=20)
        if response.status_code != 200:
            status = "Bad Request"
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            links = [a['href'] for a in soup.find_all('a', href=True)]
            status = "Live" if target_url in links else "Not Found"
    except Exception:
        status = "Bad Request"

    # Write Status
    status_col_letter, status_col_idx = get_col_letter("Status")
    worksheet.update_cell(idx, status_col_idx, status)
    set_cell_background_color(idx, status_col_letter, colors[status])
    time.sleep(1)

    # Write Last scan date
    scan_col_letter, scan_col_idx = get_col_letter("Last scan date")
    worksheet.update_cell(idx, scan_col_idx, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    time.sleep(1)

print("✅ Scanning complete.")
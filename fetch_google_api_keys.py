import gspread
from google.oauth2.service_account import Credentials
import requests
from pprint import pformat
from bs4 import BeautifulSoup
from datetime import datetime
import time

API_KEY = "AIzaSyD5-YsXKgrqc31B4n7fdw15gpUCEreb0ao"
SEARCH_ENGINE_ID = "c4ee0b8e1875a41f0"
BASE_URL = "https://www.googleapis.com/customsearch/v1"
SERVICE_ACCOUNT_FILE = "/home/ec2-user/KristiyanY/kristiyansimeonov-de6f501229f3.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
SPREADSHEET_ID = "1GmsJHIFgYWe0W9VHRMzgpuyhTWXdkdUlWgg8O3QN2Uw"
credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet("AB Script")
articles = worksheet.col_values(1)
target = worksheet.col_values(2)
print(f'Scheduling start: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

data = worksheet.get_all_records()

# Helper function to update cell background color
def set_cell_background_color(row, col, color):
    worksheet.format(f"{col}{row}", {"backgroundColor": color})

# Process rows
for idx, row in enumerate(data, start=2):  # Start at row 2 (header is row 1)
    print(f"Start processing idx: {idx}, {len(data)-1}")
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
                time.sleep(2)
                set_cell_background_color(idx, 'D', {"red": 0.0, "green": 1.0, "blue": 0.0})
                time.sleep(2)
            else:
                worksheet.update_cell(idx, 4, "False")
                time.sleep(2)
                set_cell_background_color(idx, 'D', {"red": 1.0, "green": 1.0, "blue": 1.0})
                time.sleep(2)
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            time.sleep(2)

        except requests.RequestException as e:
            print(f"Error processing URL {article}: {e}")
            worksheet.update_cell(idx, 4, "False")
            time.sleep(2)
            set_cell_background_color(idx, 'D', {"red": 1.0, "green": 0.0, "blue": 0.0})
            time.sleep(2)
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print(f'Scraping finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Total URLs processed {len(data)-1}')
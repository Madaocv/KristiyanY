import gspread
from google.oauth2.service_account import Credentials
import requests
from pprint import pformat
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import time
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv("API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
BASE_URL = "https://www.googleapis.com/customsearch/v1"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
gc = gspread.authorize(credentials)
spreadsheet = gc.open_by_key(SPREADSHEET_ID)
worksheet = spreadsheet.worksheet("Orders")
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
import time

def update_third_column(worksheet, row_idx, col1_name, col2_name):
    val1 = worksheet.cell(row_idx, list(data[0].keys()).index(col1_name) + 1).value
    val2 = worksheet.cell(row_idx, list(data[0].keys()).index(col2_name) + 1).value
    is_true1 = str(val1).strip().lower() == "true"
    is_true2 = str(val2).strip().lower() == "true"
    result = "True" if is_true1 and is_true2 else "False"
    worksheet.update_cell(row_idx, list(data[0].keys()).index("Main Status") + 1, result)
    time.sleep(1)
    col_letter = gspread.utils.rowcol_to_a1(1, list(data[0].keys()).index("Main Status") + 1)[0]
    color = {"red": 0.0, "green": 1.0, "blue": 0.0} if result == "True" else {"red": 1.0, "green": 1.0, "blue": 1.0}
    set_cell_background_color(row_idx, col_letter, color)
    time.sleep(1)

def update_status(worksheet, row_idx, col_name, status, color):
    col_letter = gspread.utils.rowcol_to_a1(1, list(data[0].keys()).index(col_name) + 1)[0]
    worksheet.update_cell(row_idx, list(data[0].keys()).index(col_name) + 1, status)
    time.sleep(1)
    set_cell_background_color(row_idx, col_letter, color)
    time.sleep(1)
# Use expected_headers to bypass the uniqueness check
expected_headers = ['Data', 'Status1', 'Updated', 'Notes', 'Main Status', 'Owner', 
                   'Sent by', 'Channel/Platform', 'Reseller', 'Orders sheet', 
                   'Communication', 'Type', 'Anchor screen', 'Anchor', 'Target URL', 
                   'Final', 'Аnchor status', 'URL status', 'Last scan date']
print("Loading data with expected_headers...")
data = worksheet.get_all_records(head=5, expected_headers=expected_headers)
print(f"✓ Success! Loaded {len(data)} rows")
# Helper function to update cell background color
def set_cell_background_color(row, col, color):
    worksheet.format(f"{col}{row}", {"backgroundColor": color})

# Process rows
for idx, row in enumerate(data, start=6):  # Start at row 2 (header is row 1)
    # print(f"Start processing idx: {idx}, {len(data)-1}")
    print(f"Processing row {idx}/{len(data)}")
    article = row["Final"]
    target = row["Target URL"]
    status = row["URL status"]
    anchor = row["Anchor"]
    main_status = row["Main Status"]
    anchor_status = row["Аnchor status"]
    if not main_status or main_status.strip().lower() == "false":
        try:
            response = requests.get(article, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [a['href'] for a in soup.find_all('a', href=True)]
            # links_text = [a.get_text().strip() for a in soup.find_all('a', href=True) if len(a.get_text().strip())>0]
            # Знаходимо всі індекси, де є збіг
            indices = [i for i, link in enumerate(links) if link == target]
            # Отримуємо тексти всіх знайдених посилань
            matched_texts = [soup.find_all('a', href=True)[i].get_text().strip() for i in indices]
            # FILL OUT LAST SCAN/STATUS
            if target in links:
                update_status(worksheet, idx, "URL status", "True", {"red": 0.0, "green": 1.0, "blue": 0.0})
            else:
                update_status(worksheet, idx, "URL status", "False", {"red": 1.0, "green": 1.0, "blue": 1.0})
            # UPDATE LAST SCAN DATE
            kyiv_time = datetime.now(ZoneInfo("Europe/Kyiv")).strftime("%Y-%m-%d %H:%M:%S")
            worksheet.update_cell(idx, list(data[0].keys()).index("Last scan date") + 1, kyiv_time)
            time.sleep(1)
            # FILL OUT STATUS ANCHOR/ MAIN STATUS
            if not anchor:
                continue
            if anchor and anchor in matched_texts:
                update_status(worksheet, idx, "Аnchor status", "True", {"red": 0.0, "green": 1.0, "blue": 0.0})
                time.sleep(1)
            else:
                update_status(worksheet, idx, "Аnchor status", "False", {"red": 1.0, "green": 1.0, "blue": 1.0})
                time.sleep(1)
            update_third_column(worksheet, idx, "URL status", "Аnchor status")
            time.sleep(1)

        except requests.RequestException as e:
            print(f"Error processing URL {article}: {e}")
            update_status(worksheet, idx, "URL status", "False", {"red": 1.0, "green": 0.0, "blue": 0.0})
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print(f'Scraping finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Total URLs processed {len(data)-1}')
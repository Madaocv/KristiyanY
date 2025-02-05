import gspread
from google.oauth2.service_account import Credentials
import requests
from pprint import pformat
from bs4 import BeautifulSoup
from datetime import datetime
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
import time

def update_third_column(worksheet, row_idx, col1, col2):
    """
    Перевіряє значення в двох колонках і записує у 6-ту колонку True або False.
    Фарбування:
    - Зелений, якщо обидва значення True.
    - Червоний, якщо хоча б одне False.

    :param worksheet: Об'єкт аркуша (Google Sheets API)
    :param row_idx: Номер рядка
    :param col1: Номер першої колонки для перевірки
    :param col2: Номер другої колонки для перевірки
    """
    # Отримуємо значення з двох колонок
    val1 = worksheet.cell(row_idx, col1).value
    val2 = worksheet.cell(row_idx, col2).value

    # Конвертуємо значення в булевий тип (може бути рядок "TRUE", "FALSE")
    is_true1 = str(val1).strip().lower() == "true"
    is_true2 = str(val2).strip().lower() == "true"

    # Визначаємо результат для третьої колонки (6-та колонка)
    result = "True" if is_true1 and is_true2 else "False"

    # Оновлюємо значення у 6-й колонці
    worksheet.update_cell(row_idx, 7, result)
    time.sleep(2)  # Затримка для запобігання обмеженням API

    # Визначаємо колір
    color = {"red": 0.0, "green": 1.0, "blue": 0.0} if result == "True" else {"red": 1.0, "green": 1.0, "blue": 1.0}

    # Оновлюємо колір фону
    set_cell_background_color(row_idx, 'G', color)
    time.sleep(2)

data = worksheet.get_all_records()

# Helper function to update cell background color
def set_cell_background_color(row, col, color):
    worksheet.format(f"{col}{row}", {"backgroundColor": color})

# Process rows
for idx, row in enumerate(data, start=2):  # Start at row 2 (header is row 1)
    # print(f"Start processing idx: {idx}, {len(data)-1}")
    article = row["Article"]
    target = row["Target URL"]
    status = row["Status"]
    anchor = row["Anchor"]
    main_status = row["Main Status"]
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
                worksheet.update_cell(idx, 4, "True")
                time.sleep(2)
                set_cell_background_color(idx, 'D', {"red": 0.0, "green": 1.0, "blue": 0.0})
                time.sleep(2)
            else:
                worksheet.update_cell(idx, 4, "False")
                time.sleep(2)
                set_cell_background_color(idx, 'D', {"red": 1.0, "green": 1.0, "blue": 1.0})
                time.sleep(2)
            # UPDATE LAST SCAN DATE
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            time.sleep(2)
            # FILL OUT STATUS ANCHOR/ MAIN STATUS
            if not anchor:
                continue
            if anchor and anchor in matched_texts:
                worksheet.update_cell(idx, 6, "True")
                time.sleep(2)
                set_cell_background_color(idx, 'F', {"red": 0.0, "green": 1.0, "blue": 0.0})
                time.sleep(2)
            else:
                worksheet.update_cell(idx, 6, "False")
                time.sleep(2)
                set_cell_background_color(idx, 'F', {"red": 1.0, "green": 1.0, "blue": 1.0})
                time.sleep(2)
            update_third_column(worksheet, idx, 4, 6)

        except requests.RequestException as e:
            print(f"Error processing URL {article}: {e}")
            worksheet.update_cell(idx, 4, "False")
            time.sleep(2)
            set_cell_background_color(idx, 'D', {"red": 1.0, "green": 0.0, "blue": 0.0})
            time.sleep(2)
            worksheet.update_cell(idx, 3, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print(f'Scraping finished: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, Total URLs processed {len(data)-1}')

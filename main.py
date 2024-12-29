import pandas as pd
import asyncio
import aiohttp
from tqdm.asyncio import tqdm_asyncio
import logging
import warnings
import argparse
import ast
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re
import os
from openpyxl.utils import get_column_letter
from urllib.parse import urlparse
from openpyxl.utils.exceptions import IllegalCharacterError
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font
import pandas as pd
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font
from openpyxl.styles import PatternFill, Font
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook

logging.getLogger('aiohttp').setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=UserWarning, module='aiohttp')


def process_keywords_in_url(df, input_keywords):
    def check_keywords(value):
        matches = [kw for kw in input_keywords if kw in value]
        return bool(matches), matches if matches else None
    df['1 Keyword inside URL'], df['1.1 Keyword in URL'] = zip(*df.iloc[:, 0].astype(str).apply(check_keywords))
    return df


def read_csv_to_pandas(file_path):
    df = pd.read_csv(file_path)
    first_column_name = df.columns[0]
    first_column_df = df[[first_column_name]].copy()

    # ows = first_column_df.iloc[1:500]
    return first_column_df

async def fetch_url(session, url, timeout=30):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    try:
        async with session.get(url, headers=headers, timeout=timeout) as response:
            if response.status == 200:
                content = await response.text()
                return response.status, content
            else:
                return response.status, None
    except asyncio.TimeoutError:
        return 408, None  # 408: Request Timeout
    except aiohttp.ClientError as e:
        return 502, None  # 502: Bad Gateway або клієнтська помилка
    except Exception as e:
        return 500, None  # 500: Internal Server Error

def extract_sentences_from_all_tags(html_content, keywords, title_keywords):
    """
    Parses HTML, searches for keywords, and extracts text from the parent tag, as well as the previous and next sentences.

    Args:
        html_content (str): The HTML content of the page.
        keywords (list): A list of keywords.
        title_keywords (list): A list of keywords to check in <h1> tags.

    Returns:
        dict: A dictionary with keywords ('kw in text') and found texts ('sentence', 'sentence-1', 'sentence+1').
    """
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')

    soup = BeautifulSoup(html_content, 'html.parser')
    if not soup.body:
        return {
            "kw in text": [],
            "sentence": "",
            "sentence-1": "",
            "sentence+1": "",
            "link_inside_sentence": "",
            "kw in title": [],
            "1.1 kw in title": False,
            "Word count": 0,
        }

    # Convert keywords and title_keywords to lowercase
    keywords = [kw.lower() for kw in keywords]
    title_keywords = [kw.lower() for kw in title_keywords]

    # Remove all <script> tags with the content
    for script_tag in soup.find_all("script"):
        script_tag.decompose()
    # Remove all <style> tags with the content
    for style_tag in soup.find_all("style"):
        style_tag.decompose()
    found_keywords = []
    matched_sentences = []
    previous_sentences = []
    next_sentences = []
    link_inside_sentence = []

    # Check for title_keywords in <h1>
    h1_text = " ".join(h1.get_text(separator=" ", strip=True).lower() for h1 in soup.find_all("h1"))
    found_title_keywords = [kw for kw in title_keywords if kw in h1_text]
    has_title_keyword = bool(found_title_keywords)

    # Word count in the filtered body
    body_text = soup.body.get_text(separator=" ", strip=True).lower()
    word_count = len(body_text.split())

    def get_sibling_text(tag, direction, max_attempts=5):
        """
        Searches for a neighboring text element (next or prev) on the same embedded level.
        If no text is found, continues searching in higher-level elements up to `max_attempts`.
        """
        sibling = tag.find_previous_sibling() if direction == "prev" else tag.find_next_sibling()
        attempts = 0

        while sibling and attempts < max_attempts:
            text = sibling.get_text(strip=True).lower()
            if text:
                # Split text into sentences
                sentences = re.split(r'(?<=[.!?])\s+', text)
                # Return the appropriate sentence
                if direction == "prev":
                    return sentences[-1].strip() if sentences else None
                else:
                    return sentences[0].strip() if sentences else None
            sibling = sibling.find_previous_sibling() if direction == "prev" else sibling.find_next_sibling()
            attempts += 1

        # If nothing is found, check parent siblings
        parent = tag.parent
        while parent and attempts < max_attempts:
            sibling = parent.find_previous_sibling() if direction == "prev" else parent.find_next_sibling()
            while sibling:
                text = sibling.get_text(strip=True).lower()
                if text:
                    sentences = re.split(r'(?<=[.!?])\s+', text)
                    if direction == "prev":
                        return sentences[-1].strip() if sentences else None
                    else:
                        return sentences[0].strip() if sentences else None
                sibling = sibling.find_previous_sibling() if direction == "prev" else sibling.find_next_sibling()
            parent = parent.parent
            attempts += 1

        return None

    for tag_to_remove in soup.find_all(["strong", "em", "b", "i", "u"]):
        tag_to_remove.unwrap()

    for tag in soup.body.find_all(string=True):
        text = tag.strip().lower()
        if not text:
            continue

        for keyword in keywords:
            if keyword in text:
                if tag.parent.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                    parent_tag = tag.parent
                    sentence_with_tags = f"<{parent_tag.name}>{parent_tag.get_text(strip=True)}</{parent_tag.name}>"
                    matched_sentences.append(sentence_with_tags)
                    found_keywords.append(keyword)
                    link_inside_sentence.append(tag.parent.name == "a")
                    prev_text = get_sibling_text(parent_tag, "prev")
                    next_text = get_sibling_text(parent_tag, "next")
                    previous_sentences.append(prev_text if prev_text else "")
                    next_sentences.append(next_text if next_text else "")
                    continue

                if tag.parent.name == "a" and tag.parent.parent:
                    parent_tag = tag.parent.parent
                else:
                    parent_tag = tag.parent

                parent_text = parent_tag.get_text(separator=" ", strip=True).lower()
                sentences = re.split(r'(?<=[.!?])\s+', parent_text)

                for i, sentence in enumerate(sentences):
                    if keyword in sentence:
                        matched_sentences.append(sentence.strip())
                        found_keywords.append(keyword)
                        link_inside_sentence.append(tag.parent.name == "a")

                        # Ensure the same number of sentences for previous and next
                        prev_sentence = sentences[i - 1].strip() if i > 0 else get_sibling_text(parent_tag, "prev")
                        next_sentence = sentences[i + 1].strip() if i < len(sentences) - 1 else get_sibling_text(parent_tag, "next")

                        previous_sentences.append(prev_sentence if prev_sentence else "")
                        next_sentences.append(next_sentence if next_sentence else "")

    # Ensure equal counts for sentences
    max_count = max(len(matched_sentences), len(previous_sentences), len(next_sentences))
    previous_sentences.extend([""] * (max_count - len(previous_sentences)))
    next_sentences.extend([""] * (max_count - len(next_sentences)))
    link_inside_sentence.extend([False] * (max_count - len(link_inside_sentence)))

    return {
        "kw in text": found_keywords,
        "sentence": matched_sentences,
        "sentence-1": previous_sentences,
        "sentence+1": next_sentences,
        "link_inside_sentence": link_inside_sentence,
        "kw in title": found_title_keywords,
        "1.1 kw in title": has_title_keyword,
        "Word count": word_count,
    }

async def process_urls_with_keywords(df, input_keywords, title_keywords, semaphore_limit=100):
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def process_url(session, url, keywords, title_keywords):
        async with semaphore:
            status, content = await fetch_url(session, url)
            if content and status == 200:
                result = extract_sentences_from_all_tags(content, keywords, title_keywords)
                result["status"] = status
                return result
            return {"kw in text": "", "sentence": "", "sentence-1": "", "sentence+1": "", "link_inside_sentence": "", "status": status, "kw in title": "", "1.1 kw in title": "","Word count":""}

    async with aiohttp.ClientSession() as session:
        tasks = [process_url(session, url, input_keywords, title_keywords) for url in df.iloc[:, 0]]
        results = await tqdm_asyncio.gather(*tasks)
    df["Response Status Code"] = [result["status"] for result in results]
    df["kw in title"] = [result.get("kw in title") for result in results]
    df["1.1 kw in title"] = [result.get("1.1 kw in title") for result in results]
    df["Word count"] = [result.get("Word count") for result in results]
    df["Link inside sentence"] = [result["link_inside_sentence"] for result in results]
    df["Keyword in text"] = [result.get("kw in text", []) if result else [] for result in results]
    df["Sentence -1"] = [result["sentence-1"] for result in results]
    df["Sentence"] = [result["sentence"] for result in results]
    df["Sentence +1"] = [result["sentence+1"] for result in results]
    return df

def remove_illegal_characters(value):
    try:
        if isinstance(value, list):
            return ", ".join(map(str, value))  # Перетворюємо список на рядок
        if isinstance(value, str):
            return ''.join(char for char in value if ord(char) >= 32 or char == '\n')
        if value is None:
            return ""
        return value
    except IllegalCharacterError as e:
        logging.error(f"{'>'*50}")
        logging.error(e)
        # logging.error(f"{'>'*50}")
        return ""  # Return an empty string if an illegal character is detecte


# def save_to_excel(df, output_file):
#     df = df.applymap(remove_illegal_characters)
#     with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
#         df.to_excel(writer, index=False, sheet_name="Results")
#     print(f"Result saved into {output_file}")

def clean_cell_value(value):
    """
    Cleans cell values to remove illegal characters for Excel.
    """
    if isinstance(value, list):
        value = f"\n{'.'*50}\n".join(map(str, value))  # Convert list to comma-separated string
    elif value is None:
        value = ""
    try:
        value = str(value)  # Convert value to string
        value =  ''.join(char for char in value if ord(char) >= 32 or char == '\n')
    except Exception:
        value = "Invalid Value"
    return value

def format_excel_with_sheets(df, output_file, fixed_widths=None):
    """
    Save DataFrame to Excel with three sheets: RAW, Group by domain, and Summary.
    """
    wb = Workbook()

    # Sheet 1: RAW
    ws_raw = wb.active
    ws_raw.title = "RAW"

    # Insert RAW data
    for col_idx, header in enumerate(df.columns, start=1):
        ws_raw.cell(row=1, column=col_idx, value=header).font = Font(bold=True)
    for row_idx, row in enumerate(df.itertuples(index=False), start=2):
        for col_idx, value in enumerate(row, start=1):
            ws_raw.cell(row=row_idx, column=col_idx, value=clean_cell_value(value))

    # Sheet 2: Group by domain
    ws_grouped = wb.create_sheet(title="Group by domain")

    # Add a 'Domain' column
    df['Domain'] = df.iloc[:, 0].apply(lambda x: x.split('/')[2] if isinstance(x, str) and '//' in x else '')

    grouped = df.groupby('Domain')

    # Styles
    green_fill = PatternFill(start_color="CCFFCC", end_color="CCFFCC", fill_type="solid")
    bold_font = Font(bold=True)

    # Insert headers
    for col_idx, header in enumerate(["Domain"] + list(df.columns), start=1):
        ws_grouped.cell(row=1, column=col_idx, value=header).font = bold_font

    row_idx = 2
    for domain, group in grouped:
        # Add domain row
        ws_grouped.cell(row=row_idx, column=1, value=domain).font = bold_font
        ws_grouped.row_dimensions[row_idx].fill = green_fill
        ws_grouped.row_dimensions[row_idx].outlineLevel = 1
        row_idx += 1

        # Add grouped rows
        for _, row in group.iterrows():
            for col_idx, value in enumerate(row, start=2):
                ws_grouped.cell(row=row_idx, column=col_idx, value=clean_cell_value(value))
            ws_grouped.row_dimensions[row_idx].outlineLevel = 2
            row_idx += 1

    df.to_csv("RawData.csv")
    # Sheet 3: Summary
    ws_summary = wb.create_sheet(title="Summary")

    # Domain and URL Count
    domain_counts = df['Domain'].value_counts()
    ws_summary.cell(row=1, column=1, value="Domain").font = bold_font
    ws_summary.cell(row=1, column=2, value="URL Count").font = bold_font
    ws_summary.cell(row=1, column=3, value="Keyword").font = bold_font
    ws_summary.cell(row=1, column=4, value="Count").font = bold_font

    # Aggregate keyword statistics
    keyword_counts = (
        df.explode("Keyword in text")
        .groupby(["Domain", "Keyword in text"])
        .size()
        .reset_index(name="Count")
        .dropna(subset=["Keyword in text"])
    )
    print(keyword_counts)
    # Write summary data
    summary_row_idx = 2
    for domain, count in domain_counts.items():
        # Write Domain and URL Count
        ws_summary.cell(row=summary_row_idx, column=1, value=domain)
        ws_summary.cell(row=summary_row_idx, column=2, value=count)

        # Filter keyword stats for this domain
        domain_keywords = keyword_counts[keyword_counts["Domain"] == domain]

        # Write keyword counts
        for _, row in domain_keywords.iterrows():
            ws_summary.cell(row=summary_row_idx, column=3, value=row["Keyword in text"])
            ws_summary.cell(row=summary_row_idx, column=4, value=row["Count"])
            summary_row_idx += 1

    # Adjust column widths with fixed widths
    for ws in [ws_raw, ws_grouped, ws_summary]:
        for col_idx, col in enumerate(ws.columns, start=1):
            col_letter = get_column_letter(col_idx)
            if fixed_widths and col_idx - 1 < len(fixed_widths):  # Respect fixed widths
                column_name = ws.cell(row=1, column=col_idx).value
                if column_name in fixed_widths:
                    ws.column_dimensions[col_letter].width = fixed_widths[column_name]
                else:
                    max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
                    ws.column_dimensions[col_letter].width = max_length + 2
            else:
                # Auto-adjust if no fixed width specified
                max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
                ws.column_dimensions[col_letter].width = max_length + 2

    # Save the workbook
    wb.save(output_file)
    print(f"File saved to {output_file}")


def main(input_path=None, output_file=None, input_keywords=None, title_keywords=None):
    input_path = os.path.abspath(input_path)
    output_file = os.path.abspath(output_file)
    df = read_csv_to_pandas(input_path)
    df = df.rename(columns={df.columns[0]: "Website"})
    df = asyncio.run(process_urls_with_keywords(df, input_keywords, title_keywords))
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    fixed_widths = {
        "": 25,
        "Website": 35,
        "Response Status Code": 10,
        "kw in title" : 15,
        "1.1 kw in title": 20,
        "Word count": 10,
        "Keyword in text": 20,
        "Link inside sentence": 20,
        "Sentence": 70,
        "Sentence -1": 70,
        "Sentence +1": 70
    }
    format_excel_with_sheets(df, output_file, fixed_widths=fixed_widths)
    print("*"*50)
    print(f"Results saved to: {output_file}")
    print("*"*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keywords handler")
    parser.add_argument("--input_path", required=True, help="Path to csv file")
    parser.add_argument("--input_keywords", required=True, help="List of keywords if format ['word1', 'word2', ...].")
    parser.add_argument("--title_keywords", required=True, help="List of keywords if format ['word1', 'word2', ...].")
    parser.add_argument("--output_file", required=True, help="Path & Output filename")

    args = parser.parse_args()

    try:
        input_keywords = ast.literal_eval(args.input_keywords)
        if not isinstance(input_keywords, list):
            raise ValueError("input_keywords should be a list")
    except Exception as e:
        raise ValueError('Wrong format input_keywords. Use this one ["word1", "word2", ...]') from e

    main_args = {
        "input_path" : args.input_path,
        "output_file": args.output_file,
        "input_keywords" : ast.literal_eval(args.input_keywords),
        "title_keywords" : ast.literal_eval(args.title_keywords)
    }
    main(**main_args)

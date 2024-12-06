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

async def fetch_url(session, url, timeout=10):
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

def extract_sentences_from_all_tags(html_content, keywords):
    """
    Parses HTML, searches for keywords, and extracts text from the parent tag, as well as the previous and next sentences.

    Args:
        html_content (str): The HTML content of the page.
        keywords (list): A list of keywords.

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
        }

    found_keywords = []
    matched_sentences = []
    previous_sentences = []
    next_sentences = []
    link_inside_sentence = []

    def get_sibling_text(tag, direction):
        """
        Searvh neibour text element (next or prev) in same embedded level.
        """
        sibling = tag.find_previous_sibling() if direction == "prev" else tag.find_next_sibling()
        while sibling:
            if sibling.get_text(strip=True):
                return sibling.get_text(separator=" ", strip=True)
            sibling = sibling.find_previous_sibling() if direction == "prev" else sibling.find_next_sibling()
        return None

    for tag_to_remove in soup.find_all(["strong", "em", "b", "i", "u"]):
        tag_to_remove.unwrap()

    for tag in soup.body.find_all(string=True):
        text = tag.strip()
        if not text:
            continue

        for keyword in keywords:
            if keyword in text:
                if keyword not in found_keywords:
                    found_keywords.append(keyword)

                is_linked = False
                if tag.parent.name == "a":
                    is_linked = True
                link_inside_sentence.append(is_linked)

                if tag.parent.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                    parent_tag = tag.parent
                    sentence_with_tags = f"<{parent_tag.name}>{parent_tag.get_text(strip=True)}</{parent_tag.name}>"
                    matched_sentences.append(sentence_with_tags)
                    prev_text = get_sibling_text(parent_tag, "prev")
                    next_text = get_sibling_text(parent_tag, "next")
                    if prev_text:
                        previous_sentences.append(prev_text)
                    if next_text:
                        next_sentences.append(next_text)
                    continue

                if tag.parent.name == "a" and tag.parent.parent:
                    parent_tag = tag.parent.parent
                else:
                    parent_tag = tag.parent

                parent_text = parent_tag.get_text(separator=" ", strip=True)
                sentences = re.split(r'(?<=[.!?])\s+', parent_text)

                for i, sentence in enumerate(sentences):
                    if keyword in sentence:
                        matched_sentences.append(sentence.strip())

                        # Check previous sentences at the current embedded level
                        has_local_prev = False
                        if i > 0 and sentences[i - 1].strip() not in previous_sentences:
                            previous_sentences.append(sentences[i - 1].strip())
                            has_local_prev = True

                        # Check next sentences at the current embedded level
                        has_local_next = False
                        if i < len(sentences) - 1 and sentences[i + 1].strip() not in next_sentences:
                            next_sentences.append(sentences[i + 1].strip())
                            has_local_next = True

                        # If no results on current level, search between neibours
                        if not has_local_prev:
                            prev_text = get_sibling_text(parent_tag, "prev")
                            if prev_text:
                                previous_sentences.append(prev_text)

                        if not has_local_next:
                            next_text = get_sibling_text(parent_tag, "next")
                            if next_text:
                                next_sentences.append(next_text)

    return {
        "kw in text": found_keywords,
        "sentence": "\n".join(matched_sentences),
        "sentence-1": "\n".join(filter(None, previous_sentences)),
        "sentence+1": "\n".join(filter(None, next_sentences)),
        "link_inside_sentence": "\n".join([str(obj) for obj in link_inside_sentence]),
    }

async def process_urls_with_keywords(df, input_keywords, semaphore_limit=100):
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def process_url(session, url, keywords):
        async with semaphore:
            status, content = await fetch_url(session, url)
            if content and status == 200:
                result = extract_sentences_from_all_tags(content, keywords)
                result["status"] = status
                return result
            return {"kw in text": [], "sentence": [], "sentence-1": [], "sentence+1": [], "link_inside_sentence": False, "status": status}

    async with aiohttp.ClientSession() as session:
        tasks = [process_url(session, url, input_keywords) for url in df.iloc[:, 0]]
        results = await tqdm_asyncio.gather(*tasks)
    df["Response Status Code"] = [result["status"] for result in results]
    df["Keyword in text"] = [result.get("kw in text", []) if result else [] for result in results]
    df["Link inside sentence"] = [result["link_inside_sentence"] for result in results]
    df["Sentence -1"] = [result["sentence-1"] for result in results]
    df["Sentence"] = [result["sentence"] for result in results]
    df["Sentence +1"] = [result["sentence+1"] for result in results]
    return df

def remove_illegal_characters(value):
    if isinstance(value, str):
        return ''.join(char for char in value if ord(char) >= 32 or char == '\n')
    return value

def save_to_excel(df, output_file):
    df = df.applymap(remove_illegal_characters)
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    print(f"Result saved into {output_file}")

def main(input_path=None, output_file=None, input_keywords=None):
    input_path = os.path.abspath(input_path)
    output_file = os.path.abspath(output_file)
    df = read_csv_to_pandas(input_path)
    df = process_keywords_in_url(df, input_keywords)
    df = asyncio.run(process_urls_with_keywords(df, input_keywords))
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    save_to_excel(df, output_file)
    print("*"*50)
    print(f"Results saved to: {output_file}")
    print("*"*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Keywords handler")
    parser.add_argument("--input_path", required=True, help="Path to csv file")
    parser.add_argument("--input_keywords", required=True, help="List of keywords if format ['word1', 'word2', ...].")
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
        "input_keywords" : ast.literal_eval(args.input_keywords)
    }
    main(**main_args)

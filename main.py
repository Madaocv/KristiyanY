import pandas as pd
import asyncio
import aiohttp
from aiohttp import ClientSession
from tqdm.asyncio import tqdm_asyncio
import time
import logging
import warnings
import argparse
import ast
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import re

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

    ows = first_column_df.iloc[1:500]
    return ows

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
    Аналізує HTML, шукає ключові слова та витягує текст із батьківського тега
    або батьківського parent.parent для <a> тегу.

    Args:
        html_content (str): HTML-контент сторінки.
        keywords (list): Список ключових слів.

    Returns:
        dict: Словник із ключовими словами ('kw in text') і знайденими текстами ('sentence').
    """
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')

    soup = BeautifulSoup(html_content, 'html.parser')
    if not soup.body:
        print("No <body> tag found in the HTML content.:")
        return {"kw in text": [], "sentence": [], "link_inside_sentence": False}
    # Results
    found_keywords = []
    matched_sentences = []
    link_inside_sentence = False

    for tag_to_remove in soup.find_all(["strong", "em", "b", "i", "u"]):
        tag_to_remove.unwrap()

    # Проходимо по всіх текстових елементах
    for tag in soup.body.find_all(string=True):
        text = tag.strip()
        # pass the empty tags
        if not text:
            continue
        # Checking keywoard in text
        for keyword in keywords:
            if keyword in text:
                # Add keyword if brand new
                if keyword not in found_keywords:
                    found_keywords.append(keyword)
                if tag.parent.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                    parent_tag = tag.parent
                    parent_text = parent_tag.get_text(separator=" ", strip=True)
                    # split text on sentences
                    sentences = re.split(r'(?<=[.!?])\s+', parent_text)
                    # Додаємо релевантне речення разом із тегами
                    for sentence in sentences:
                        if keyword in sentence:
                            sentence_with_tags = f"<{parent_tag.name}>{sentence.strip()}</{parent_tag.name}>"
                            if sentence_with_tags not in matched_sentences:
                                matched_sentences.append(sentence_with_tags)
                            break
                    continue
                # Якщо це текст із <a>, беремо контекст на 2 рівні вгору
                if tag.parent.name == "a" and tag.parent.parent:
                    parent_tag = tag.parent.parent
                else:
                    # Інакше беремо стандартний батьківський тег
                    parent_tag = tag.parent

                # Отримуємо весь текст із батьківського тега
                parent_text = parent_tag.get_text(separator=" ", strip=True)

                # Розбиваємо текст на речення
                sentences = re.split(r'(?<=[.!?])\s+', parent_text)

                # Фільтруємо речення, що містять ключове слово
                relevant_sentences = [
                    sentence.strip() for sentence in sentences if keyword in sentence
                ]
                for sentence in relevant_sentences:
                    if parent_tag.find("a"):
                        link_inside_sentence = True
                # Додаємо лише релевантні речення
                for sentence in relevant_sentences:
                    if sentence not in matched_sentences:
                        matched_sentences.append(sentence)

                break  # Переходимо до наступного текстового елемента

    return {"kw in text": found_keywords, "sentence": "\n".join(matched_sentences), "link_inside_sentence": link_inside_sentence}

async def process_urls_with_keywords(df, input_keywords, semaphore_limit=100):
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def process_url(session, url, keywords):
        async with semaphore:
            status, content = await fetch_url(session, url)
            if content and status == 200:
                result = extract_sentences_from_all_tags(content, keywords)
                result["status"] = status
                return result
            return {"kw in text": [], "sentence": [], "link_inside_sentence": False, "status": status}

    async with aiohttp.ClientSession() as session:
        tasks = [process_url(session, url, input_keywords) for url in df.iloc[:, 0]]
        results = await tqdm_asyncio.gather(*tasks)
    df["response status codes"] = [result["status"] for result in results]
    df["Link inside sentence"] = [result["link_inside_sentence"] for result in results]
    df["kw in text"] = [result.get("kw in text", []) if result else [] for result in results]
    df["sentence"] = [result["sentence"] for result in results]
    return df

def save_to_excel(df, output_file):
    with pd.ExcelWriter(output_file, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    print(f"Result saved into {output_file}")

def main(file_path):
    df = read_csv_to_pandas(file_path)
    input_keywords = ["art portfolio" , "website ideas" , "idea for a website" , "website design" , "mobile-friendly design" , "restaurant website" , "website for a restaurant" , "online store" , "website builder"]
    df = process_keywords_in_url(df, input_keywords)
    df = asyncio.run(process_urls_with_keywords(df, input_keywords))
    # save_to_excel(df, 'Initial_test_04_12.xlsx')
    df.to_csv('test_x1.csv')
    print(df.head(20))
    # i1 = 11
    # i2 = 12
    # value = df.iloc[i1]['sentence']
    # value2 = df.iloc[i2]['sentence']
    # print("-"*50)
    # print(value, df.iloc[i1]['Webiste'])
    # print("-"*50)
    # print(value2, df.iloc[i1]['Webiste'])
    # print("-"*50)

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
        raise ValueError("Wrong format input_keywords. Use this one ['word1', 'word2', ...]") from e
    # main("/Users/olegeliiashiv/Downloads/Template 2 - Sheet6.csv")
    main(args.input_path)


import pandas as pd
import asyncio
import aiohttp
from aiohttp import ClientSession
from tqdm.asyncio import tqdm_asyncio
import time
# import speedtest
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
    df['InURL'], df['KwInURL'] = zip(*df.iloc[:, 0].astype(str).apply(check_keywords))
    return df


def read_csv_to_pandas(file_path):
    df = pd.read_csv(file_path)
    first_column_name = df.columns[0]
    first_column_df = df[[first_column_name]].copy()

    ows = first_column_df.head(20)
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
                return content
            else:
                return None
    except asyncio.TimeoutError:
        return None
    except Exception as e:
        return None

def extract_sentences_from_all_tags(html_content, keywords):
    if isinstance(html_content, bytes):
        html_content = html_content.decode('utf-8', errors='ignore')
    soup = BeautifulSoup(html_content, 'html.parser')
    found_keywords = []
    matched_sentences = []
    keywords_lower = [kw.lower() for kw in keywords]
    for tag in soup.find_all(text=True):
        text = tag.strip()
        
        for keyword in keywords:
            if keyword in text:
                if keyword not in found_keywords:
                    found_keywords.append(keyword)
                matched_sentences.append(text)
                break
        # TODO lowercase
        # text_lower = text.lower()
        # for keyword_lower, keyword in zip(keywords_lower, keywords):
        #     if keyword_lower in text_lower:
        #         if keyword not in found_keywords:
        #             found_keywords.append(keyword)
        #         matched_sentences.append(text)
        #         break
        # END lowercase

    return {"kw in text": found_keywords, "sentence": matched_sentences}

async def process_urls_with_keywords(df, input_keywords, semaphore_limit=100):
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def process_url(session, url, keywords):
        async with semaphore:
            content = await fetch_url(session, url)
            if content:
                return extract_sentences_from_all_tags(content, keywords)

            return {"kw in text": [], "sentence": []}

    async with aiohttp.ClientSession() as session:
        tasks = [process_url(session, url, input_keywords) for url in df.iloc[:, 0]]
        results = await tqdm_asyncio.gather(*tasks)
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
    print(df.head(20))
    value = df.iloc[6]['sentence']
    value2 = df.iloc[7]['sentence']
    print("-"*50)
    print(value)
    print("-"*50)
    print(value2)
    print("-"*50)

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


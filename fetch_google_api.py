import requests
import pandas as pd
import json

API_KEY = "xxx"
SEARCH_ENGINE_ID = "xxx"
INPUT_CSV = "Master-Queries-API.csv"
INDEX = 0
OUTPUT_FILE_NAME = "google_search_results_18_test_1"
def read_csv_to_pandas(file_path):
    df = pd.read_csv(file_path)
    return df
df = read_csv_to_pandas(INPUT_CSV)
first_row = df.iloc[INDEX].to_dict()
QUERY = first_row.get("Keywords")
# QUERY = 'site:socialtradia.com intext:{influencers OR "influencer marketing"} -inurl:tag -inurl:docs -inurl:job -inurl:forum -inurl:/personal_development -inurl:/help -inurl:dev. -inurl:/faq -inurl:/events -inurl:thread -inurl:privacy -inurl:/user -inurl:shop. -inurl:/contact -inurl:/archive -inurl:press-release -inurl:/profile -inurl:/author -inurl:episode -inurl:/community -inurl:glossary -inurl:forms/'
# QUERY = 'site:userp.io intext:{influencers OR ""influencer marketing""} -inurl:tag -inurl:docs -inurl:job -inurl:forum -inurl:/personal_development -inurl:/help -inurl:dev. -inurl:/faq -inurl:/events -inurl:thread -inurl:privacy -inurl:/user -inurl:shop. -inurl:/contact -inurl:/archive -inurl:press-release -inurl:/profile -inurl:/author -inurl:episode -inurl:/community -inurl:glossary -inurl:forms/'
BASE_URL = "https://www.googleapis.com/customsearch/v1"

def get_all_results(api_key, search_engine_id, query, total_results):
    results = []
    start_index = 1  # Починаємо з першого результату
    while start_index <= total_results:
        print(f"start index: {start_index} total results: {total_results}")
        # Формуємо URL із параметрами
        url = f"{BASE_URL}?key={api_key}&cx={search_engine_id}&q={query}&start={start_index}&num=10"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if "items" in data:
                results.extend(data["items"])
            start_index += 10
        else:
            print(f"Error {response.status_code}: {response.json()}")
            break
    return results

# Викликаємо функцію
response = requests.get(f"{BASE_URL}?key={API_KEY}&cx={SEARCH_ENGINE_ID}&q={QUERY}&num=1")
# from pprint import pformat
# print(pformat(response.json()))
total_results = int(response.json()["queries"]["request"][0]["totalResults"])

all_results = get_all_results(API_KEY, SEARCH_ENGINE_ID, QUERY, total_results)

# Зберемо вибрані поля у список словників
filtered_results = []
for item in all_results:
    filtered_results.append({
        "title": item.get("title"),
        "link": item.get("link"),
        "snippet": item.get("snippet")
    })

# Створюємо DataFrame
df = pd.DataFrame(filtered_results)

# Зберігаємо в Excel або виводимо
print(df.head(5))
df.to_excel(f"{OUTPUT_FILE_NAME}.xlsx", index=False)

with open(f"{OUTPUT_FILE_NAME}.json", "w", encoding="utf-8") as file:
    json.dump(all_results, file, ensure_ascii=False, indent=4)

print(f"Data saved into {OUTPUT_FILE_NAME}.json")

    
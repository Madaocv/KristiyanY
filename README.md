# README: Keyword Finder Script

This README file provides step-by-step instructions on how to set up, configure, and run the Keyword Finder script. This script processes HTML content, searches for keywords, and extracts relevant sentences and additional context.

---

## **Prerequisites**

Ensure you have the following installed on your system:

1. **Python** (Version 3.8 or higher)
2. **pip** (Python's package manager)
3. **Git** (for cloning the repository)

---

## **Setup Instructions**

### 1. Clone the Repository

To get started, clone the repository to your local machine:

```bash
git clone https://github.com/Madaocv/KristiyanY.git
cd keyword-finder-script
```

### 2. Create and Activate a Virtual Environment (Optional)

It is recommended to use a virtual environment to avoid conflicts with other Python packages:

#### On macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

#### On Windows:
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Required Dependencies

Install all necessary Python packages using `pip`:

```bash
pip install -r requirements.txt
```

---

## **Usage**

### Command-Line Arguments

The script accepts the following arguments:

1. **`--input_path`**: The path to the input CSV file containing URLs.
2. **`--input_keywords`**: A list of keywords to search for, passed as a stringified Python list.
3. **`--output_file`**: The path where the results file will be saved. Ensure this includes a valid file name and extension (e.g., `.xlsx`).

### Example Command

```bash
python main.py --input_path="/Downloads/Template 2 - Sheet6.csv" --input_keywords='["art portfolio" , "website ideas" , "idea for a website" , "website design" , "mobile-friendly design" , "restaurant website" , "website for a restaurant" , "online store" , "website builder"]' --output_file="data/Initial_test_05_12_v6.xlsx"
```

---

## **Key Features**

1. **Keyword Detection**:
   - Extracts sentences containing specified keywords.
   - Identifies whether a keyword is wrapped in `<a>` tags and adds this information to the output.

2. **Contextual Sentence Extraction**:
   - Extracts one sentence before and after each match (when available).

3. **Output File**:
   - Results are saved in an Excel file with columns for the keyword, matching sentences, context, and additional metadata.

4. **Automatic Directory Creation**:
   - If the specified output directory does not exist, it will be created automatically.

5. **Usage trics**:
   - User can use different combinations of (output filename & set keywords) - in order to get files with different results  
---

## **Output File Structure**

The output Excel file contains the following columns:
1. **`1 Keyword inside URL`**: True/False.
2. **`1.1 Keyword in URL`**: keyword name.
3. **`Response Status Code`**: The HTTP status code for each URL.
4. **`Keyword in text`**: Keywords found in the page content.
5. **`Link inside sentence`**: Boolean indicating if the keyword was wrapped in an `<a>` tag.
6. **`Sentence`**: Sentences containing the keywords.
7. **`Sentence -1`**: The sentence preceding the match.
8. **`Sentence +1`**: The sentence following the match.


---

## **Troubleshooting**

1. **File Not Found**:
   - Ensure the input file path is correct and accessible.
   - Use absolute paths if running the script from a different directory.

2. **Output File Errors**:
   - Make sure the `--output_file` argument includes a valid file name (e.g., `results.xlsx`).
   - Ensure you have write permissions for the specified directory.

3. **Dependencies Issues**:
   - Run `pip install -r requirements.txt` to ensure all dependencies are installed.

---

## **Notes**

- If using relative paths, ensure the script is run from the directory containing the `main.py` file.
- Use Python 3.8 or higher for compatibility.

---

## **Contributing**

Contributions are welcome! Feel free to submit issues or pull requests on the repository.

---

## **License**

This project is licensed under the MIT License.
```
python main.py \
--input_path="Template2-Sheet72.csv" \
--output_file="data/5_2025_exclude_true.xlsx" \
--input_keywords='["art portfolio" , "website ideas" , "idea for a website" , "website design" , "mobile-friendly design" , "restaurant website" , "website for a restaurant" , "online store" , "website builder"]' \
--title_keywords='["art portfolio" , "website ideas" , "idea for a website" , "website design" , "mobile-friendly design" , "restaurant website" , "website for a restaurant" , "online store" , "website builder"]' \
--exclude_h_and_true=True
```
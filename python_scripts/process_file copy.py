import argparse
import os
import sys
import pandas as pd
import pdfplumber
import pytesseract
from PIL import Image

# Presidio imports for the Governance Tier
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# --- Windows Specific Configuration ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize Presidio engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# --- CUSTOM MOCK DATA RECOGNIZER ---
# Because our test SSN starts with '000', Presidio's default strict validation ignores it.
# Here we add a relaxed custom regex pattern just for our test data.
mock_ssn_pattern = Pattern(name="mock_ssn_regex", regex=r"\d{3}-\d{2}-\d{4}", score=0.85)
mock_ssn_recognizer = PatternRecognizer(supported_entity="US_SSN", patterns=[mock_ssn_pattern])
analyzer.registry.add_recognizer(mock_ssn_recognizer)
# -----------------------------------

def sanitize_text(text):
    """Governance Tier: Identifies and redacts sensitive PII/PHI."""
    if not text or not text.strip():
        return text
        
    results = analyzer.analyze(text=text, entities=["PERSON", "PHONE_NUMBER", "US_SSN"], language='en')
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
    
    return anonymized_result.text

def extract_from_pdf(file_path):
    """Extracts raw string from native digital PDFs."""
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
        sys.exit(1)
    return text

def extract_from_image(file_path):
    """Extracts text from handwritten notes and images."""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        print(f"Error reading Image: {e}")
        sys.exit(1)
    return text

def extract_from_excel(file_path):
    """Cleans and flattens messy Excel files into a Markdown table."""
    try:
        df = pd.read_excel(file_path)
        text = df.to_markdown(index=False) 
    except Exception as e:
        print(f"Error reading Excel: {e}")
        sys.exit(1)
    return text

def process_file(file_path):
    """FileRouter analyzes the file extension and dispatches to the correct parser."""
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        sys.exit(1)

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    raw_text = ""

    if ext == '.pdf':
        raw_text = extract_from_pdf(file_path)
    elif ext in ['.jpg', '.jpeg', '.png']:
        raw_text = extract_from_image(file_path)
    elif ext in ['.xlsx', '.xls', '.csv']:
        raw_text = extract_from_excel(file_path)
    else:
        print(f"Error: Unsupported file format {ext}")
        sys.exit(1)

    sanitized_text = sanitize_text(raw_text)
    print(sanitized_text.strip())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Healthcare Data Sanitizer - Parsing & Governance Tier")
    parser.add_argument('--file', type=str, required=True, help="Absolute path to the input file")
    args = parser.parse_args()

    process_file(args.file)
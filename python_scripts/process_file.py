import argparse
import os
import sys
import json
import pandas as pd
import pdfplumber
import re
import pytesseract
from PIL import Image

# Presidio imports for the Governance Tier
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_anonymizer import AnonymizerEngine

# LangChain imports for the Extraction Tier
from langchain_ollama import OllamaLLM
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Optional

# --- Windows Specific Configuration ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Initialize Presidio engines
analyzer = AnalyzerEngine()
anonymizer = AnonymizerEngine()

# Custom pattern for our mock SSN
mock_ssn_pattern = Pattern(name="mock_ssn_regex", regex=r"\d{3}-\d{2}-\d{4}", score=0.85)
mock_ssn_recognizer = PatternRecognizer(supported_entity="US_SSN", patterns=[mock_ssn_pattern])
analyzer.registry.add_recognizer(mock_ssn_recognizer)

# --- EXTRACTION TIER SETUP ---
class PatientRecord(BaseModel):
    patient_name: str = Field(description="Redacted patient name e.g. <PERSON>")
    ssn: Optional[str] = Field(default=None, description="Redacted SSN e.g. <US_SSN>")
    date: Optional[str] = Field(default=None, description="Date of consultation")
    reason_for_visit: Optional[str] = Field(default=None, description="Primary reason for visit")
    diagnosis: Optional[str] = Field(default=None, description="Diagnosis provided")
    plan: Optional[str] = Field(default=None, description="Treatment plan")

llm = OllamaLLM(model="phi3")
parser = PydanticOutputParser(pydantic_object=PatientRecord)

prompt_template = PromptTemplate(
    template="""Extract the medical record information from the following sanitized text.
Return ONLY a raw JSON object with no markdown, no code fences, no explanation.
{format_instructions}

Sanitized Text:
{text}

Return only the JSON object, nothing else:""",
    input_variables=["text"],
    partial_variables={"format_instructions": parser.get_format_instructions()},
)

# --- CORE FUNCTIONS ---
def sanitize_text(text):
    if not text or not text.strip():
        return text
    results = analyzer.analyze(text=text, entities=["PERSON", "PHONE_NUMBER", "US_SSN"], language='en')
    anonymized_result = anonymizer.anonymize(text=text, analyzer_results=results)
    return anonymized_result.text

def extract_structured_json(sanitized_text):
    try:
        _input = prompt_template.format_prompt(text=sanitized_text)
        output = llm.invoke(_input.to_string())
        
        if not output or not output.strip():
            return {"error": "LLM returned empty response", "raw_output": "null"}
        
        # Strip markdown code fences if LLM wraps output in ```json ... ```
        cleaned = re.sub(r'^```(?:json)?\s*', '', output.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        parsed_record = parser.parse(cleaned)
        return parsed_record.model_dump()
    except Exception as e:
        return {"error": "Failed to parse JSON", "raw_output": str(e)}

def extract_from_pdf(file_path):
    text = ""
    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(json.dumps({"error": f"Error reading PDF: {e}"}))
        sys.exit(1)
    return text

def extract_from_image(file_path):
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        print(json.dumps({"error": f"Error reading Image: {e}"}))
        sys.exit(1)
    return text

def extract_from_excel(file_path):
    try:
        df = pd.read_excel(file_path)
        # Return list of row strings, one per record
        rows = []
        for _, row in df.iterrows():
            rows.append(row.to_markdown())
        return rows   # returns a LIST now
    except Exception as e:
        print(json.dumps({"error": f"Error reading Excel: {e}"}))
        sys.exit(1)
    

def process_file(file_path):
    if not os.path.exists(file_path):
        print(json.dumps({"error": f"File not found at {file_path}"}))
        sys.exit(1)

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == '.pdf':
        raw_text = extract_from_pdf(file_path)
        sanitized = sanitize_text(raw_text)
        result = extract_structured_json(sanitized)
        print(json.dumps(result, indent=2))

    elif ext in ['.jpg', '.jpeg', '.png']:
        raw_text = extract_from_image(file_path)
        sanitized = sanitize_text(raw_text)
        result = extract_structured_json(sanitized)
        print(json.dumps(result, indent=2))

    elif ext in ['.xlsx', '.xls', '.csv']:
        rows = extract_from_excel(file_path)   # now a list
        all_records = []
        for i, row_text in enumerate(rows):
            sanitized = sanitize_text(row_text)
            record = extract_structured_json(sanitized)
            record["row_index"] = i   # helpful for debugging
            all_records.append(record)
        print(json.dumps(all_records, indent=2))  # prints ALL records

    else:
        print(json.dumps({"error": f"Unsupported file format {ext}"}))
        sys.exit(1)

    # 1. Redact PII
    #sanitized_text = sanitize_text(raw_text)
    
    # 2. Extract JSON using LLM
    #structured_data = extract_structured_json(sanitized_text)

    # 3. Print the final JSON string to stdout for your Flask app to capture
    ##print(json.dumps(structured_data, indent=2))

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Healthcare Data Sanitizer")
    arg_parser.add_argument('--file', type=str, required=True, help="Absolute path to the input file")
    args = arg_parser.parse_args()
    process_file(args.file)
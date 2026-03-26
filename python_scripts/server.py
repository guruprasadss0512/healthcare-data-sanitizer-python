from flask import Flask, request, jsonify
import subprocess
import os
import json  # ← Add this line explicitly

app = Flask(__name__)

PYTHON = r"C:\TTP\Projects\Healthcare_data_Sanitizer\python_scripts\.venv\Scripts\python.exe"
SCRIPT = r"C:\TTP\Projects\Healthcare_data_Sanitizer\python_scripts\process_file.py"
INPUT_DIR = r"C:\TTP\Projects\Healthcare_data_Sanitizer\input_data"
OUTPUT_FILE = r"C:\TTP\Projects\Healthcare_data_Sanitizer\output_data\sanitized_records.jsonl"

@app.route('/process', methods=['POST'])
def process():
    data = request.json
    filename = data.get('filename') if data else None

    if not filename:
        files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.pdf')]
        if not files:
            return jsonify({"error": "No PDF files found in input_data"}), 404
        filename = files[0]

    filepath = os.path.join(INPUT_DIR, filename)

    if not os.path.exists(filepath):
        return jsonify({"error": f"File not found: {filepath}"}), 404

    result = subprocess.run(
        [PYTHON, SCRIPT, "--file", filepath],
        capture_output=True,
        text=True
    )

    return jsonify({
        "filename": filename,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode
    })

@app.route('/save', methods=['POST'])  # ← New endpoint
def save():
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400
    
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(data) + '\n')
    
    return jsonify({"status": "saved", "record": data})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5680, debug=True)
import pandas as pd
import os

# Ensure the directory exists
os.makedirs('input_data', exist_ok=True)

# Mock data with sensitive PII (Name, Phone)
data = {
    'Patient Name': ['John Doe', 'Jane Smith', 'Robert Johnson'],
    'Phone Number': ['555-0198', '555-0123', '555-0147'],
    'Heart Rate (bpm)': [72, 85, 65],
    'Blood Pressure': ['120/80', '135/90', '110/70'],
    'Notes': ['Routine checkup.', 'Complains of mild headache.', 'Follow-up for hypertension.']
}

df = pd.DataFrame(data)
file_path = os.path.join('input_data', 'patient_vitals.xlsx')
df.to_excel(file_path, index=False)
print(f"Successfully created: {file_path}")
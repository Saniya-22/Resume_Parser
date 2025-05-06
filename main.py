import streamlit as st
import fitz  # PyMuPDF
import docx
import pandas as pd
import requests
import io
import os
import zipfile
import mimetypes
import tempfile
import shutil
import time
import json
import urllib.parse

# Set your Together.ai API key
TOGETHER_API_KEY = "tgp_v1_QllmweYOn2yK6hDwEC7gEWja6tpRKL35T9zgMScFWNU"

# Prompt template
def build_prompt(text):
    return f"""
You are a resume parser. Extract the following fields from the resume text below:

- Full Name
- Email
- Phone Number
- LinkedIn (if present)
- Education (Degree, Institution, Year)
- Work Experience (Job Title, Company, Duration, Description)
- Technical Skills
- Projects
- Certifications

Return the output in valid JSON.

Resume Text:
\"\"\"{text}\"\"\"
"""

# Read PDF resume
def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Read DOCX resume
def extract_text_from_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])

# Call Together API with retry logic
def parse_with_llm(text, max_retries=3):
    prompt = build_prompt(text)
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "https://api.together.xyz/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {TOGETHER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama-3-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "max_tokens": 2000
                },
                timeout=30  # Add timeout
            )
            
            if response.status_code != 200:
                st.warning(f"API request failed with status code {response.status_code}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            response_data = response.json()
            
            if 'choices' not in response_data or not response_data['choices']:
                st.warning("Invalid API response format. Retrying...")
                time.sleep(2 ** attempt)
                continue
                
            content = response_data['choices'][0]['message']['content']
            
            # Try to parse the content as JSON
            try:
                if isinstance(content, str):
                    # Clean the content to ensure it's valid JSON
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    content = content.strip()
                    
                    parsed_content = json.loads(content)
                    return parsed_content
                return content
            except json.JSONDecodeError as e:
                st.warning(f"Failed to parse JSON response: {str(e)}. Retrying...")
                time.sleep(2 ** attempt)
                continue
                
        except requests.exceptions.RequestException as e:
            st.warning(f"Request failed: {str(e)}. Retrying...")
            time.sleep(2 ** attempt)
            continue
            
    return {"Error": "Failed to parse after multiple attempts"}

# Function to process uploaded files
def process_files(uploaded_files):
    parsed_data = []
    for file in uploaded_files:
        st.info(f"Processing {file.name}...")
        
        # Determine file type
        file_type = mimetypes.guess_type(file.name)[0]
        
        # Handle ZIP files
        if file_type == "application/zip" or file.name.lower().endswith('.zip'):
            try:
                # Create a temporary directory with a unique name
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Save the uploaded file temporarily
                    temp_zip_path = os.path.join(temp_dir, "temp.zip")
                    with open(temp_zip_path, "wb") as f:
                        f.write(file.getvalue())
                    
                    # Extract all files from ZIP
                    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                        # Get list of files in the ZIP
                        file_list = zip_ref.namelist()
                        
                        for filename in file_list:
                            # Skip directories
                            if filename.endswith('/'):
                                continue
                                
                            # Only process PDF and DOCX files
                            if filename.lower().endswith(('.pdf', '.docx')):
                                try:
                                    # Create a safe filename by replacing spaces and special characters
                                    safe_filename = filename.replace(' ', '_')
                                    safe_filename = urllib.parse.quote(safe_filename)
                                    
                                    # Extract the file to a temporary location
                                    extracted_path = os.path.join(temp_dir, safe_filename)
                                    with open(extracted_path, 'wb') as f:
                                        f.write(zip_ref.read(filename))
                                    
                                    # Process the file
                                    with open(extracted_path, 'rb') as f:
                                        if filename.lower().endswith('.pdf'):
                                            resume_text = extract_text_from_pdf(f)
                                        else:
                                            resume_text = extract_text_from_docx(f)
                                        
                                        parsed = parse_with_llm(resume_text)
                                        if isinstance(parsed, dict) and "Error" not in parsed:
                                            parsed["File Name"] = os.path.basename(filename)
                                            parsed_data.append(parsed)
                                        else:
                                            st.warning(f"Failed to parse {filename}")
                                except Exception as e:
                                    st.warning(f"Error processing file {filename}: {str(e)}")
                                    continue
                
            except Exception as e:
                st.error(f"Error processing ZIP file {file.name}: {str(e)}")
                continue
        else:
            # Handle regular PDF and DOCX files
            if file_type == "application/pdf" or file.name.lower().endswith('.pdf'):
                resume_text = extract_text_from_pdf(file)
            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file.name.lower().endswith('.docx'):
                resume_text = extract_text_from_docx(file)
            else:
                st.warning(f"Unsupported file format: {file.name}")
                continue

            parsed = parse_with_llm(resume_text)
            if isinstance(parsed, dict) and "Error" not in parsed:
                parsed["File Name"] = file.name
                parsed_data.append(parsed)
            else:
                st.warning(f"Failed to parse {file.name}")
    
    return parsed_data

# Streamlit UI
st.title("AI Resume Parser (Multi-Resume to Excel)")

# Add upload options
upload_option = st.radio("Choose upload method:", ["Single File", "Multiple Files", "ZIP Folder"])

if upload_option == "Single File":
    uploaded_files = st.file_uploader("Upload a resume (PDF or DOCX)", type=["pdf", "docx"])
    if uploaded_files:
        uploaded_files = [uploaded_files]
elif upload_option == "Multiple Files":
    uploaded_files = st.file_uploader("Upload multiple resumes (PDF or DOCX)", type=["pdf", "docx"], accept_multiple_files=True)
else:  # ZIP Folder
    uploaded_files = st.file_uploader("Upload a ZIP folder containing resumes", type=["zip"])
    if uploaded_files:
        uploaded_files = [uploaded_files]

if uploaded_files:
    parsed_data = process_files(uploaded_files)
    
    if parsed_data:
        df = pd.DataFrame(parsed_data)
        st.dataframe(df)

        # Downloadable Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Parsed Resumes")
        st.download_button("Download Excel", data=output.getvalue(), file_name="parsed_resumes.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

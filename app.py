import cohere
import PyPDF2
import pandas as pd
import os
import json
from tqdm import tqdm
import zipfile
import tempfile
import streamlit as st
import re
import base64

# === Step 1: Initialize Cohere ===
co = cohere.Client("gXcxeZJAMADnZxdzhadiSweV8nZkwCKaIcIwNkuo")  # Replace with your actual key

# === Step 2: Extract text from PDF ===
def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# === Step 3: Extract fields using Cohere ===
def extract_resume_fields(resume_text):
    prompt = f"""
Extract the following information from this resume:
- Full Name
- Email Address
- Phone Number
- Address
- Skills (comma-separated)
- Year of Education or Graduation

If any field is missing or cannot be found, leave it as an empty string (""). Do not use demo data or placeholders.

Resume Text:
\"\"\"{resume_text}\"\"\"

Return it as a minified JSON object:
{{
  "Name": "",
  "Email": "",
  "Phone": "",
  "Address": "",
  "Skills": "",
  "Education Year": ""
}}
"""
    try:
        response = co.generate(
            model="command-r-plus",
            prompt=prompt,
            max_tokens=300,
            temperature=0.3
        )

        raw_text = response.generations[0].text.strip()

        cleaned_text = raw_text \
            .replace("null", '""') \
            .replace("\n", "") \
            .replace("True", '"True"') \
            .replace("False", '"False"') \
            .replace("None", '""')

        # Try loading JSON
        data = json.loads(cleaned_text)

        # Check if it actually contains expected fields
        expected_keys = ["Name", "Email", "Phone", "Address", "Skills", "Education Year"]
        for key in expected_keys:
            if key not in data:
                data[key] = ""

        # Post-process: blank out demo data
        demo_names = ["John Smith", "Jane Doe", "Test User"]
        demo_emails = ["example@email.com", "test@email.com", "john.smith@email.com"]
        demo_phones = ["123-456-7890", "000-000-0000", "111-111-1111"]
        if data["Name"].strip() in demo_names:
            data["Name"] = ""
        if data["Email"].strip().lower() in demo_emails:
            data["Email"] = ""
        if data["Phone"].strip() in demo_phones:
            data["Phone"] = ""

        # Regex fallback for email
        if not data["Email"]:
            email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", resume_text)
            if email_match:
                data["Email"] = email_match.group(0)

        # Regex fallback for phone
        if not data["Phone"]:
            phone_match = re.search(r"(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}", resume_text)
            if phone_match:
                data["Phone"] = phone_match.group(0)

        return data

    except Exception as e:
        print("⚠️ LLM failed or response was invalid:", e)
        # Return blank fields if error occurs
        return {
            "Name": "",
            "Email": "",
            "Phone": "",
            "Address": "",
            "Skills": "",
            "Education Year": ""
        }

# === Step 4: Unzip and process resumes ===
def process_zip_files(zip_paths, output_excel="Parsed_Resumes_Streamlit.xlsx"):
    all_data = []

    with tempfile.TemporaryDirectory() as tmp_dir:
        for zip_path in zip_paths:
            folder_name = os.path.splitext(os.path.basename(zip_path))[0]
            extract_path = os.path.join(tmp_dir, folder_name)
            os.makedirs(extract_path, exist_ok=True)

            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

            pdf_files = [os.path.join(root, file)
                         for root, _, files in os.walk(extract_path)
                         for file in files if file.lower().endswith('.pdf')]

            st.success(f"📦 Unzipped '{zip_path}' with {len(pdf_files)} PDFs")

            # Add a progress bar and status message
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            for i, pdf_path in enumerate(pdf_files):
                with st.spinner(f"Extracting info from resume {i+1} of {len(pdf_files)}..."):
                    try:
                        text = extract_text_from_pdf(pdf_path)
                        data = extract_resume_fields(text)
                        data["File Name"] = os.path.basename(pdf_path)
                        data["Folder"] = folder_name
                        all_data.append(data)
                        status_placeholder.info(f"✅ Processed: {os.path.basename(pdf_path)}")
                    except Exception as e:
                        st.warning(f"❌ Error with {pdf_path}: {e}")
                        all_data.append({
                            "Name": "",
                            "Email": "",
                            "Phone": "",
                            "Address": "",
                            "Skills": "",
                            "Education Year": "",
                            "File Name": os.path.basename(pdf_path),
                            "Folder": folder_name
                        })
                    # Update progress bar (dotted style via custom CSS below)
                    progress = (i + 1) / len(pdf_files)
                    progress_bar.progress(progress)
            status_placeholder.success("🎉 All resumes processed!")
            st.markdown("""
                <style>
                .stProgress > div > div > div > div {
                    background-image: repeating-linear-gradient(90deg, #4CAF50, #4CAF50 8px, #fff 8px, #fff 16px);
                }
                </style>
            """, unsafe_allow_html=True)

    df = pd.DataFrame(all_data)
    df.to_excel(output_excel, index=False)
    
    # Add magical completion effect
    st.markdown("""
        <div style="text-align: center; margin: 20px 0;">
            <div style="font-size: 24px; color: #4CAF50;">✨ Processing Complete! ✨</div>
            <div style="font-size: 16px; color: #666; margin-top: 10px;">Your resumes have been magically parsed!</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.balloons()
    return df, output_excel

# --- MAIN APP ---
def main_app():
    st.set_page_config(page_title="AI Resume Parser", page_icon="📄", layout="centered")

    st.markdown("""
        <style>
            .main {background-color: #f7f9fa;}
            h1, h3 {text-align: center;}
            .css-18e3th9 {padding: 2rem 1rem;}
            /* Full page styles */
            .stApp {
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }
            .main .block-container {
                max-width: 100% !important;
                padding: 2rem 1rem !important;
            }
            /* Responsive adjustments for mobile */
            @media (max-width: 600px) {
                .main, .css-18e3th9 {
                    padding: 0.5rem 0.2rem !important;
                    max-width: 100vw !important;
                }
                h1, h2, h3 {
                    font-size: 1.3rem !important;
                }
                .stButton>button {
                    font-size: 1.1rem !important;
                    padding: 0.7rem 1.2rem !important;
                }
                .stDataFrame, .stTable {
                    overflow-x: auto !important;
                    font-size: 0.9rem !important;
                }
            }
        </style>
    """, unsafe_allow_html=True)

    st.title("📄 AI Resume Parser")
    st.subheader("🚀 Powered by Naaz Applications")
    st.markdown("Upload ZIP files containing resumes (PDFs), and this app will parse the key fields for you using an LLM!")

    st.divider()

    # Upload section
    with st.container():
        uploaded_zips = st.file_uploader("📁 Upload one or more ZIP files", type="zip", accept_multiple_files=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("✅ Make sure your ZIPs only contain PDF resumes.")

        if uploaded_zips:
            if st.button("🔍 Start Parsing"):
                with st.spinner("Working through the resumes..."):
                    zip_paths = []
                    temp_dir = tempfile.TemporaryDirectory()
                    for file in uploaded_zips:
                        zip_path = os.path.join(temp_dir.name, file.name)
                        with open(zip_path, "wb") as f:
                            f.write(file.getbuffer())
                        zip_paths.append(zip_path)

                    df, file_path = process_zip_files(zip_paths)

                    with st.expander("📊 View Parsed Data"):
                        st.dataframe(df)

                    with open(file_path, "rb") as f:
                        st.download_button(
                            label="📥 Download Excel",
                            data=f,
                            file_name=os.path.basename(file_path),
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

    st.markdown("---")
    st.markdown("👩‍💻 Built by [Saniya Malik](#) | ✨ [Cohere API](https://cohere.com/) | ❤️ Streamlit")

# --- LOGIN PAGE ---
def login():
    # Read and encode the image
    with open("cl.jpg", "rb") as image_file:
        encoded = base64.b64encode(image_file.read()).decode()
    # Set as background
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url('data:image/jpg;base64,{encoded}');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title("🔒 Login to Naaz Applications CV Parser")
    user_id = st.text_input("User ID")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if user_id == "admin" and password == "naaz123":
            st.session_state['logged_in'] = True
            st.success("Login successful! Redirecting...")
            st.experimental_rerun()
        else:
            st.error("Invalid ID or password.")

# --- APP ENTRY POINT ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    login()
else:
    main_app()

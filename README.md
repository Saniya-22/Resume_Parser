# AI Resume Parser

A Streamlit application that uses AI to parse resumes from PDF files and extract key information.

## Features

- Upload multiple ZIP files containing PDF resumes
- Automatic extraction of key information using AI
- Export results to Excel
- Secure login system
- Full-page responsive design

## Deployment Instructions

1. Create a Streamlit account at [streamlit.io](https://streamlit.io)
2. Install the Streamlit CLI:
   ```bash
   pip install streamlit
   ```
3. Login to Streamlit:
   ```bash
   streamlit login
   ```
4. Deploy the app:
   ```bash
   streamlit deploy app.py
   ```

## Environment Variables

The app requires a Cohere API key. Set it as an environment variable:

```bash
export COHERE_API_KEY="your_api_key_here"
```

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the app locally:
   ```bash
   streamlit run app.py
   ```

## Security Note

Make sure to:

- Keep your Cohere API key secure
- Change the default login credentials
- Use environment variables for sensitive information

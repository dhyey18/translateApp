import streamlit as st
import os
import time
from google import genai
from google.genai import types
import markdown
from xhtml2pdf import pisa
from io import BytesIO
import tempfile

# ================= PAGE CONFIGURATION =================
st.set_page_config(
    page_title="Gemini PDF Translator",
    page_icon="📄",
    layout="wide"
)

# ================= HELPER FUNCTIONS =================

def convert_markdown_to_pdf_bytes(markdown_text):
    """
    Converts Markdown text to a PDF file object (BytesIO).
    """
    if not markdown_text:
        return None

    # 1. Convert Markdown to HTML
    html_body = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    
    # 2. Add Professional Styling (CSS)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{ font-family: Helvetica, sans-serif; font-size: 11pt; line-height: 1.6; color: #333; }}
            h1 {{ color: #ffffff; background-color: #2c3e50; padding: 15px; text-align: center; }}
            h2 {{ color: #2980b9; border-bottom: 2px solid #ecf0f1; padding-bottom: 5px; margin-top: 20px; }}
            h3 {{ color: #16a085; font-weight: bold; margin-top: 15px; }}
            ul, ol {{ margin-bottom: 12px; padding-left: 20px; }}
            li {{ margin-bottom: 6px; }}
            blockquote {{ background-color: #f9f9f9; border-left: 4px solid #bdc3c7; margin: 15px 0; padding: 10px; font-style: italic; }}
            code {{ background-color: #f4f4f4; padding: 2px 4px; font-family: Courier; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

    # 3. Create PDF in memory
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(
        BytesIO(html_content.encode('utf-8')),
        dest=pdf_buffer,
        encoding='utf-8'
    )

    if pisa_status.err:
        return None
    
    pdf_buffer.seek(0)
    return pdf_buffer

def process_translation(api_key, uploaded_file):
    """
    Handles the API communication using the new google-genai SDK (v1.0+).
    """
    # 1. Initialize Client
    client = genai.Client(api_key=api_key)

    # 2. Save uploaded file to a temporary path (SDK requires a file path)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        # 3. Upload File using the new Files API
        with st.spinner("Uploading PDF to Gemini..."):
            # The new SDK uploads and returns a file object reference directly
            file_ref = client.files.upload(file=tmp_file_path)
            
        # 4. Generate Content
        with st.spinner("Translating handwritten notes... (Using Gemini 2.5 Flash)"):
            
            prompt = """
            You are an expert translator. The document contains handwritten notes (likely in Gujarati).
            1. Read the handwriting carefully.
            2. Translate the content directly into English.
            3. Formatting: 
               - Start with a Level 1 Header (# Title) for the Main Topic.
               - Use Level 2 Headers (##) for sub-sections.
               - Use bullet points for lists.
               - Convert diagrams to nested lists.
            4. Do not include original text, only English.
            """
            
            # New SDK syntax: pass file reference directly in contents list
            response = client.models.generate_content(
                model="gemini-2.5-flash", 
                contents=[file_ref, prompt]
            )
            
            return response.text

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None
    finally:
        # Cleanup temp file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

# ================= UI LAYOUT =================

st.title("✨ Dhyey's Handwritten Notes Translator")
st.markdown("Thoughtfully designed and carefully developed with love especially for my young and beautifull Sasu Ji :)")
st.markdown("Upload a PDF of handwritten notes and convert them to a clean, formatted English PDF.")


# Sidebar for Configuration
with st.sidebar:
    st.header("Configuration")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Using Model: gemini-2.5-flash")

# Main File Uploader
uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

if uploaded_file is not None and api_key:
    st.success(f"File uploaded: {uploaded_file.name}")
    
    if st.button("Translate & Convert", type="primary"):
        translation_text = process_translation(api_key, uploaded_file)
        
        if translation_text:
            st.subheader("Translation Preview")
            st.markdown(translation_text)
            
            pdf_bytes = convert_markdown_to_pdf_bytes(translation_text)
            
            if pdf_bytes:
                st.success("PDF Generated Successfully!")
                st.download_button(
                    label="📥 Download Translated PDF",
                    data=pdf_bytes,
                    file_name="Translated_Notes.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Failed to generate PDF layout.")

elif uploaded_file is not None and not api_key:
    st.warning("Please enter your Gemini API Key in the sidebar to proceed.")

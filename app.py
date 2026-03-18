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
    page_title="Dhyey's Notes Translator",
    page_icon="📄",
    layout="wide"
)

# ================= LANGUAGE CONFIG =================

LANGUAGE_CONFIG = {
    "English": {
        "code": "en",
        "font_note": "Uses standard Helvetica font.",
        "prompt_instruction": """
            You are an expert translator. The document contains handwritten notes (likely in Gujarati or another Indian language).
            1. Read the handwriting carefully.
            2. Translate the content directly into **English**.
            3. Formatting:
               - Start with a Level 1 Header (# Title) for the Main Topic.
               - Use Level 2 Headers (##) for sub-sections.
               - Use bullet points for lists.
               - Convert diagrams to nested lists.
            4. Do not include original text, only English.
        """,
        "css_font": "Helvetica, sans-serif",
    },
    "Hindi": {
        "code": "hi",
        "font_note": "Hindi uses Devanagari script. A Google Font will be embedded for proper rendering.",
        "prompt_instruction": """
            You are an expert translator fluent in Hindi. The document contains handwritten notes (likely in Gujarati or English).
            1. Read the handwriting carefully.
            2. Translate the content directly into **Hindi (Devanagari script)**.
            3. Formatting:
               - Start with a Level 1 Header (# शीर्षक) for the Main Topic.
               - Use Level 2 Headers (##) for sub-sections.
               - Use bullet points for lists.
               - Convert diagrams to nested lists.
            4. Do not include original text, only Hindi in Devanagari script.
        """,
        "css_font": "'Noto Sans Devanagari', sans-serif",
        "google_font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap",
    },
    "Gujarati": {
        "code": "gu",
        "font_note": "Gujarati uses its own script. A Google Font will be embedded for proper rendering.",
        "prompt_instruction": """
            You are an expert translator fluent in Gujarati. The document contains handwritten notes (possibly in English or Hindi).
            1. Read the handwriting carefully.
            2. Translate the content directly into **Gujarati (Gujarati script)**.
            3. Formatting:
               - Start with a Level 1 Header (# શીર્ષક) for the Main Topic.
               - Use Level 2 Headers (##) for sub-sections.
               - Use bullet points for lists.
               - Convert diagrams to nested lists.
            4. Do not include original text, only Gujarati script.
        """,
        "css_font": "'Noto Sans Gujarati', sans-serif",
        "google_font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@400;700&display=swap",
    },
}

# ================= HELPER FUNCTIONS =================

def convert_markdown_to_pdf_bytes(markdown_text, language="English"):
    """
    Converts Markdown text to a PDF file object (BytesIO).
    Handles multi-language fonts via embedded Google Fonts (for screen) or system fonts.
    """
    if not markdown_text:
        return None

    config = LANGUAGE_CONFIG[language]
    css_font = config["css_font"]

    # Embed Google Font link if needed (for Hindi/Gujarati)
    font_import = ""
    if "google_font_url" in config:
        font_import = f'<link href="{config["google_font_url"]}" rel="stylesheet">'

    # Convert Markdown to HTML
    html_body = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        {font_import}
        <style>
            @page {{ size: A4; margin: 2cm; }}
            body {{
                font-family: {css_font};
                font-size: 11pt;
                line-height: 1.8;
                color: #333;
            }}
            h1 {{
                color: #ffffff;
                background-color: #2c3e50;
                padding: 15px;
                text-align: center;
                font-family: {css_font};
            }}
            h2 {{
                color: #2980b9;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 5px;
                margin-top: 20px;
                font-family: {css_font};
            }}
            h3 {{
                color: #16a085;
                font-weight: bold;
                margin-top: 15px;
                font-family: {css_font};
            }}
            ul, ol {{ margin-bottom: 12px; padding-left: 20px; }}
            li {{ margin-bottom: 6px; }}
            blockquote {{
                background-color: #f9f9f9;
                border-left: 4px solid #bdc3c7;
                margin: 15px 0;
                padding: 10px;
                font-style: italic;
            }}
            code {{ background-color: #f4f4f4; padding: 2px 4px; font-family: Courier; }}
        </style>
    </head>
    <body>
        {html_body}
    </body>
    </html>
    """

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


def process_translation(api_key, uploaded_file, target_language="English"):
    """
    Handles the API communication using the google-genai SDK.
    Translates to the specified target language.
    """
    client = genai.Client(api_key=api_key)
    config = LANGUAGE_CONFIG[target_language]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        with st.spinner("Uploading PDF to Gemini..."):
            file_ref = client.files.upload(file=tmp_file_path)

        spinner_msg = f"Translating to {target_language}... (Using Gemini 2.5 Flash)"
        with st.spinner(spinner_msg):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[file_ref, config["prompt_instruction"]]
            )
            return response.text

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


# ================= CUSTOM STYLES =================

st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    .language-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-english { background: #dbeafe; color: #1d4ed8; }
    .badge-hindi   { background: #fce7f3; color: #9d174d; }
    .badge-gujarati{ background: #d1fae5; color: #065f46; }
    .info-box {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13px;
        color: #78350f;
        margin-top: 6px;
    }
</style>
""", unsafe_allow_html=True)

# ================= UI LAYOUT =================

st.title("✨ Dhyey's Handwritten Notes Translator")
st.markdown("Thoughtfully designed with love 💛")
st.markdown("Upload a PDF of handwritten notes and convert them to a clean, formatted PDF — in **English**, **Hindi**, or **Gujarati**.")

st.divider()

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")
    api_key = st.text_input("Gemini API Key", type="password", help="Get your key from Google AI Studio")
    st.info("Model: gemini-2.5-flash")

    st.markdown("---")
    st.markdown("**Supported Languages**")
    st.markdown("""
    <span class="language-badge badge-english">🇬🇧 English</span><br><br>
    <span class="language-badge badge-hindi">🇮🇳 Hindi</span><br><br>
    <span class="language-badge badge-gujarati">🟢 Gujarati</span>
    """, unsafe_allow_html=True)

# Main layout: two columns
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Upload & Settings")

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    st.markdown("#### 🌐 Target Translation Language")
    target_language = st.radio(
        "Translate notes into:",
        options=list(LANGUAGE_CONFIG.keys()),
        horizontal=True,
        label_visibility="collapsed"
    )

    # Show font note for non-Latin scripts
    lang_config = LANGUAGE_CONFIG[target_language]
    if "google_font_url" in lang_config:
        st.markdown(f"""<div class="info-box">
            ℹ️ <b>{target_language}</b> uses a non-Latin script. The translated text will render correctly in the preview below.
            For the best PDF output with native script, ensure fonts are available on your system or use the preview.
        </div>""", unsafe_allow_html=True)

    if uploaded_file:
        st.success(f"✅ File ready: **{uploaded_file.name}**")

    translate_clicked = st.button(
        f"🔄 Translate to {target_language}",
        type="primary",
        disabled=not (uploaded_file and api_key)
    )

    if uploaded_file and not api_key:
        st.warning("⚠️ Please enter your Gemini API Key in the sidebar.")

with col2:
    st.subheader("📄 Translation Output")

    if translate_clicked and uploaded_file and api_key:
        translation_text = process_translation(api_key, uploaded_file, target_language)

        if translation_text:
            st.markdown(translation_text)
            st.divider()

            pdf_bytes = convert_markdown_to_pdf_bytes(translation_text, target_language)

            if pdf_bytes:
                st.success("🎉 PDF Generated Successfully!")
                lang_code = LANGUAGE_CONFIG[target_language]["code"]
                st.download_button(
                    label=f"📥 Download Translated PDF ({target_language})",
                    data=pdf_bytes,
                    file_name=f"Translated_Notes_{lang_code}.pdf",
                    mime="application/pdf",
                )
            else:
                st.error("❌ Failed to generate PDF. The translation preview above is still available.")
        else:
            st.error("❌ Translation failed. Please check your API key and try again.")
    else:
        st.markdown("""
        <div style="
            background: #f0f4ff;
            border: 2px dashed #93c5fd;
            border-radius: 12px;
            padding: 40px 20px;
            text-align: center;
            color: #6b7280;
            margin-top: 20px;
        ">
            <div style="font-size: 48px;">📝</div>
            <div style="font-size: 16px; margin-top: 10px;">
                Your translated content will appear here.<br>
                Upload a PDF and click <b>Translate</b> to begin.
            </div>
        </div>
        """, unsafe_allow_html=True)

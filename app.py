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
        "prompt_instruction": """You are an expert translator and document formatter.

Your task: Translate ALL content from the uploaded PDF document into English.

Instructions:
1. Read every word carefully — including headings, sub-headings, bullet points, and body text.
2. Translate EVERYTHING into English. Do not skip any section.
3. If the original is in Gujarati, Hindi, or any other language, translate it fully into English.
4. Formatting rules:
   - Use a Level 1 Header (# Title) for the main topic.
   - Use Level 2 Headers (## Heading) for each sub-section.
   - Use bullet points (- item) for lists.
   - Convert any diagrams or tables into nested bullet lists.
5. Output ONLY the translated English text in Markdown format. Do not include the original language text.
6. Do not add any commentary, disclaimers, or notes about the translation process.

Begin translation now:""",
        "css_font": "Helvetica, sans-serif",
    },
    "Hindi": {
        "code": "hi",
        "font_note": "Hindi uses Devanagari script. A Google Font will be embedded for proper rendering.",
        "prompt_instruction": """आप एक विशेषज्ञ अनुवादक और दस्तावेज़ फ़ॉर्मेटर हैं।

आपका कार्य: अपलोड किए गए PDF दस्तावेज़ की सभी सामग्री को हिंदी में अनुवाद करें।

निर्देश:
1. हर शब्द को ध्यान से पढ़ें — शीर्षक, उप-शीर्षक, बुलेट पॉइंट और मुख्य पाठ सहित।
2. सब कुछ हिंदी (देवनागरी लिपि) में अनुवाद करें। किसी भी अनुभाग को न छोड़ें।
3. स्वरूपण नियम:
   - मुख्य विषय के लिए Level 1 Header (# शीर्षक) का उपयोग करें।
   - प्रत्येक उप-अनुभाग के लिए Level 2 Headers (## उप-शीर्षक) का उपयोग करें।
   - सूचियों के लिए बुलेट पॉइंट (- आइटम) का उपयोग करें।
4. केवल हिंदी में अनुवादित Markdown पाठ आउटपुट करें। मूल भाषा का पाठ शामिल न करें।
5. अनुवाद प्रक्रिया के बारे में कोई टिप्पणी, अस्वीकरण या नोट न जोड़ें।

अभी अनुवाद शुरू करें:""",
        "css_font": "'Noto Sans Devanagari', sans-serif",
        "google_font_url": "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap",
    },
    "Gujarati": {
        "code": "gu",
        "font_note": "Gujarati uses its own script. A Google Font will be embedded for proper rendering.",
        "prompt_instruction": """તમે એક નિષ્ણાત અનુવાદક અને દસ્તાવેજ ફોર્મેટર છો.

તમારું કાર્ય: અપલોડ કરેલ PDF દસ્તાવેજની તમામ સામગ્રીને ગુજરાતીમાં અનુવાદ કરો.

સૂચનાઓ:
1. દરેક શબ્દ ધ્યાનથી વાંચો — શીર્ષકો, પેટા-શીર્ષકો, બુલેટ પોઈન્ટ અને મુખ્ય ટેક્સ્ટ સહિત.
2. બધું ગુજરાતી (ગુજરાતી લિપિ)માં અનુવાદ કરો. કોઈ પણ વિભાગ છોડશો નહીં.
3. ફોર્મેટિંગ નિયમો:
   - મુખ્ય વિષય માટે Level 1 Header (# શીર્ષક) વાપરો.
   - દરેક પેટા-વિભાગ માટે Level 2 Headers (## પેટા-શીર્ષક) વાપરો.
   - યાદીઓ માટે બુલેટ પોઈન્ટ (- આઇટમ) વાપરો.
4. ફક્ત ગુજરાતીમાં અનુવાદિત Markdown ટેક્સ્ટ આઉટપુટ કરો. મૂળ ભાષાનો ટેક્સ્ટ સામેલ કરશો નહીં.
5. અનુવાદ પ્રક્રિયા વિશે કોઈ ટિપ્પણી, અસ્વીકરણ અથવા નોંધ ઉમેરશો નહીં.

હવે અનુવાદ શરૂ કરો:""",
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

    KEY FIX: The prompt instruction now comes FIRST in the contents list,
    followed by the file. This ensures Gemini treats the instruction as the
    primary directive before reading the document.
    """
    client = genai.Client(api_key=api_key)
    config = LANGUAGE_CONFIG[target_language]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        with st.spinner("Uploading PDF to Gemini..."):
            file_ref = client.files.upload(file=tmp_file_path)

            # Wait for file to be fully processed before sending to model
            # This avoids translation failures on large PDFs
            max_wait = 30  # seconds
            waited = 0
            while waited < max_wait:
                file_status = client.files.get(name=file_ref.name)
                if file_status.state.name == "ACTIVE":
                    break
                time.sleep(2)
                waited += 2

        spinner_msg = f"Translating to {target_language}... (Using Gemini 2.5 Flash)"
        with st.spinner(spinner_msg):
            # FIX: Put the instruction text FIRST, then the file.
            # This ordering makes Gemini follow the translation directive
            # instead of just summarizing or echoing the document.
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    config["prompt_instruction"],  # Instruction first
                    file_ref,                       # Document second
                ],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)  # Faster, no chain-of-thought
                )
            )

            result_text = response.text

            # Safety check: if response is suspiciously short, warn the user
            if result_text and len(result_text.strip()) < 100:
                st.warning("⚠️ The translation result seems very short. The PDF may not have been read correctly, or the document is very brief.")

            return result_text

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


# ================= CUSTOM STYLES =================

st.markdown("""
<style>
    /* ── Light mode defaults ── */
    :root {
        --app-bg:            #f5f7fa;
        --placeholder-bg:    #f0f4ff;
        --placeholder-border:#93c5fd;
        --placeholder-text:  #6b7280;
        --info-bg:           #fffbeb;
        --info-border:       #f59e0b;
        --info-text:         #78350f;
        --badge-en-bg:       #dbeafe;
        --badge-en-text:     #1d4ed8;
        --badge-hi-bg:       #fce7f3;
        --badge-hi-text:     #9d174d;
        --badge-gu-bg:       #d1fae5;
        --badge-gu-text:     #065f46;
    }

    /* ── Dark mode overrides ── */
    @media (prefers-color-scheme: dark) {
        :root {
            --app-bg:            #0e1117;
            --placeholder-bg:    #1a1f2e;
            --placeholder-border:#3b5bdb;
            --placeholder-text:  #9ca3af;
            --info-bg:           #1f1a0e;
            --info-border:       #d97706;
            --info-text:         #fcd34d;
            --badge-en-bg:       #1e3a5f;
            --badge-en-text:     #93c5fd;
            --badge-hi-bg:       #3b1a2e;
            --badge-hi-text:     #f9a8d4;
            --badge-gu-bg:       #0f2e20;
            --badge-gu-text:     #6ee7b7;
        }
    }

    /* Streamlit also injects [data-theme="dark"] on the root element */
    [data-theme="dark"] {
        --app-bg:            #0e1117;
        --placeholder-bg:    #1a1f2e;
        --placeholder-border:#3b5bdb;
        --placeholder-text:  #9ca3af;
        --info-bg:           #1f1a0e;
        --info-border:       #d97706;
        --info-text:         #fcd34d;
        --badge-en-bg:       #1e3a5f;
        --badge-en-text:     #93c5fd;
        --badge-hi-bg:       #3b1a2e;
        --badge-hi-text:     #f9a8d4;
        --badge-gu-bg:       #0f2e20;
        --badge-gu-text:     #6ee7b7;
    }

    .stApp { background-color: var(--app-bg); }

    .language-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 600;
        margin-right: 6px;
    }
    .badge-english  { background: var(--badge-en-bg);  color: var(--badge-en-text); }
    .badge-hindi    { background: var(--badge-hi-bg);  color: var(--badge-hi-text); }
    .badge-gujarati { background: var(--badge-gu-bg);  color: var(--badge-gu-text); }

    .info-box {
        background: var(--info-bg);
        border-left: 4px solid var(--info-border);
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13px;
        color: var(--info-text);
        margin-top: 6px;
    }

    .placeholder-box {
        background: var(--placeholder-bg);
        border: 2px dashed var(--placeholder-border);
        border-radius: 12px;
        padding: 40px 20px;
        text-align: center;
        color: var(--placeholder-text);
        margin-top: 20px;
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
        <div class="placeholder-box">
            <div style="font-size: 48px;">📝</div>
            <div style="font-size: 16px; margin-top: 10px;">
                Your translated content will appear here.<br>
                Upload a PDF and click <b>Translate</b> to begin.
            </div>
        </div>
        """, unsafe_allow_html=True)

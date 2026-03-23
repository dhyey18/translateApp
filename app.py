import streamlit as st
import os
import time
from google import genai
from google.genai import types
import markdown
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
        "css_font": "Georgia, 'Times New Roman', serif",
        "font_link": "",
    },
    "Hindi": {
        "code": "hi",
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
        "font_link": "https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap",
    },
    "Gujarati": {
        "code": "gu",
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
        "font_link": "https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@400;700&display=swap",
    },
}

# ================= EXPORT FUNCTIONS =================

def build_html(markdown_text, language="English"):
    """
    Converts Markdown to a fully self-contained, styled HTML file.
    - Loads Google Fonts via <link> so Gujarati/Hindi render perfectly in any browser.
    - Includes a print tip so users can Ctrl+P → Save as PDF from the browser.
      (Browser PDF printing handles Unicode fonts correctly; xhtml2pdf does NOT.)
    """
    if not markdown_text:
        return None

    cfg = LANGUAGE_CONFIG[language]
    font_link_tag = (
        f'<link rel="stylesheet" href="{cfg["font_link"]}">'
        if cfg["font_link"] else ""
    )
    css_font = cfg["css_font"]
    lang_code = cfg["code"]
    html_body = markdown.markdown(markdown_text, extensions=["extra", "nl2br"])

    html = f"""<!DOCTYPE html>
<html lang="{lang_code}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Translated Notes – {language}</title>
  {font_link_tag}
  <style>
    /* ── Print styles (Ctrl+P → Save as PDF) ── */
    @media print {{
      .no-print {{ display: none !important; }}
      body {{ margin: 0; max-width: 100%; padding: 0; }}
      h1 {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}

    /* ── Base ── */
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: {css_font};
      font-size: 13pt;
      line-height: 1.9;
      color: #1a1a1a;
      background: #ffffff;
      max-width: 860px;
      margin: 0 auto;
      padding: 40px 32px 80px;
    }}

    /* ── Print tip banner ── */
    .print-tip {{
      display: flex;
      align-items: center;
      gap: 10px;
      background: #eff6ff;
      border: 1px solid #bfdbfe;
      border-radius: 10px;
      padding: 12px 18px;
      margin-bottom: 32px;
      font-size: 11pt;
      color: #1e40af;
    }}
    .print-tip kbd {{
      background: #dbeafe;
      border-radius: 4px;
      padding: 1px 6px;
      font-family: monospace;
      font-size: 10pt;
    }}

    /* ── Headings ── */
    h1 {{
      font-family: {css_font};
      color: #ffffff;
      background: linear-gradient(135deg, #2c3e50 0%, #3d5a80 100%);
      padding: 20px 28px;
      border-radius: 10px;
      text-align: center;
      margin-bottom: 32px;
      font-size: 22pt;
      letter-spacing: 0.3px;
    }}
    h2 {{
      font-family: {css_font};
      color: #2980b9;
      border-bottom: 2px solid #e8f0fe;
      padding-bottom: 6px;
      margin: 32px 0 14px;
      font-size: 15pt;
    }}
    h3 {{
      font-family: {css_font};
      color: #16a085;
      margin: 20px 0 10px;
      font-size: 13pt;
    }}

    /* ── Body copy ── */
    p {{ margin-bottom: 12px; }}
    ul, ol {{ margin: 0 0 14px 28px; }}
    li {{ margin-bottom: 7px; }}
    blockquote {{
      background: #f8f9fa;
      border-left: 4px solid #ced4da;
      margin: 18px 0;
      padding: 12px 18px;
      border-radius: 0 8px 8px 0;
      font-style: italic;
      color: #555;
    }}
    code {{
      background: #f3f4f6;
      padding: 2px 6px;
      border-radius: 4px;
      font-family: 'Courier New', Courier, monospace;
      font-size: 11pt;
    }}
    pre {{ background: #f3f4f6; padding: 14px; border-radius: 8px; overflow-x: auto; }}
    pre code {{ background: none; padding: 0; }}
  </style>
</head>
<body>
  <div class="print-tip no-print">
    💡 <strong>Save as PDF:</strong> Press <kbd>Ctrl+P</kbd> (Windows/Linux) or <kbd>⌘+P</kbd> (Mac) → choose <em>"Save as PDF"</em>
  </div>
  {html_body}
</body>
</html>"""

    return BytesIO(html.encode("utf-8"))


def build_markdown(markdown_text):
    """Raw Markdown — open in any editor, Notion, Obsidian, etc."""
    if not markdown_text:
        return None
    return BytesIO(markdown_text.encode("utf-8"))


def build_txt(markdown_text):
    """Plain UTF-8 text — strips Markdown symbols, works for every script/language."""
    if not markdown_text:
        return None
    # Simple symbol strip so the plain text reads cleanly
    import re
    text = markdown_text
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)   # remove # headers
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)                  # bold
    text = re.sub(r"\*(.*?)\*", r"\1", text)                       # italic
    text = re.sub(r"^[-*+]\s+", "• ", text, flags=re.MULTILINE)   # bullets
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)          # links
    return BytesIO(text.encode("utf-8"))


# ================= TRANSLATION =================

def process_translation(api_key, uploaded_file, target_language="English"):
    client = genai.Client(api_key=api_key)
    config = LANGUAGE_CONFIG[target_language]

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    try:
        with st.spinner("Uploading PDF to Gemini..."):
            file_ref = client.files.upload(file=tmp_file_path)

            # Wait until Gemini finishes processing the file
            max_wait, waited = 30, 0
            while waited < max_wait:
                if client.files.get(name=file_ref.name).state.name == "ACTIVE":
                    break
                time.sleep(2)
                waited += 2

        with st.spinner(f"Translating to {target_language}… (Gemini 2.5 Flash)"):
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[config["prompt_instruction"], file_ref],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                ),
            )
            result = response.text

        if result and len(result.strip()) < 100:
            st.warning("⚠️ Result looks very short — the PDF may not have been read correctly.")

        return result

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
    --app-bg:             #f5f7fa;
    --placeholder-bg:     #f0f4ff;
    --placeholder-border: #93c5fd;
    --placeholder-text:   #6b7280;
    --info-bg:            #fffbeb;
    --info-border:        #f59e0b;
    --info-text:          #78350f;
    --badge-en-bg:        #dbeafe; --badge-en-text: #1d4ed8;
    --badge-hi-bg:        #fce7f3; --badge-hi-text: #9d174d;
    --badge-gu-bg:        #d1fae5; --badge-gu-text: #065f46;
    --dl-bg:              #f0fdf4; --dl-border: #86efac; --dl-text: #14532d;
  }

  /* ── Dark mode overrides (OS-level) ── */
  @media (prefers-color-scheme: dark) {
    :root {
      --app-bg:             #0e1117;
      --placeholder-bg:     #1a1f2e;
      --placeholder-border: #3b5bdb;
      --placeholder-text:   #9ca3af;
      --info-bg:            #1f1a0e;
      --info-border:        #d97706;
      --info-text:          #fcd34d;
      --badge-en-bg:        #1e3a5f; --badge-en-text: #93c5fd;
      --badge-hi-bg:        #3b1a2e; --badge-hi-text: #f9a8d4;
      --badge-gu-bg:        #0f2e20; --badge-gu-text: #6ee7b7;
      --dl-bg:              #0f2e1a; --dl-border: #16a34a; --dl-text: #86efac;
    }
  }

  /* ── Dark mode overrides (Streamlit toggle) ── */
  [data-theme="dark"] {
    --app-bg:             #0e1117;
    --placeholder-bg:     #1a1f2e;
    --placeholder-border: #3b5bdb;
    --placeholder-text:   #9ca3af;
    --info-bg:            #1f1a0e;
    --info-border:        #d97706;
    --info-text:          #fcd34d;
    --badge-en-bg:        #1e3a5f; --badge-en-text: #93c5fd;
    --badge-hi-bg:        #3b1a2e; --badge-hi-text: #f9a8d4;
    --badge-gu-bg:        #0f2e20; --badge-gu-text: #6ee7b7;
    --dl-bg:              #0f2e1a; --dl-border: #16a34a; --dl-text: #86efac;
  }

  .stApp { background-color: var(--app-bg); }

  .language-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 13px; font-weight: 600; margin-right: 6px;
  }
  .badge-english  { background: var(--badge-en-bg); color: var(--badge-en-text); }
  .badge-hindi    { background: var(--badge-hi-bg); color: var(--badge-hi-text); }
  .badge-gujarati { background: var(--badge-gu-bg); color: var(--badge-gu-text); }

  .info-box {
    background: var(--info-bg);
    border-left: 4px solid var(--info-border);
    padding: 10px 16px; border-radius: 6px;
    font-size: 13px; color: var(--info-text); margin-top: 6px;
  }

  .placeholder-box {
    background: var(--placeholder-bg);
    border: 2px dashed var(--placeholder-border);
    border-radius: 12px; padding: 40px 20px;
    text-align: center; color: var(--placeholder-text); margin-top: 20px;
  }

  .download-section {
    background: var(--dl-bg);
    border: 1px solid var(--dl-border);
    border-radius: 10px; padding: 16px 20px; margin-top: 16px;
  }
  .download-label {
    font-size: 13px; font-weight: 600;
    color: var(--dl-text); margin-bottom: 10px;
  }
</style>
""", unsafe_allow_html=True)

# ================= UI LAYOUT =================

st.title("✨ Dhyey's Notes Translator")
st.markdown("Thoughtfully designed with love 💛")
st.markdown("Upload a PDF of handwritten notes and convert them to clean, formatted text — in **English**, **Hindi**, or **Gujarati**.")
st.divider()

# ── Sidebar ──
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

# ── Main columns ──
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📤 Upload & Settings")

    uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

    st.markdown("#### 🌐 Target Translation Language")
    target_language = st.radio(
        "Translate notes into:",
        options=list(LANGUAGE_CONFIG.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )

    cfg = LANGUAGE_CONFIG[target_language]
    if cfg["font_link"]:
        st.markdown(f"""<div class="info-box">
            ℹ️ <b>{target_language}</b> uses a non-Latin script. Download the
            <b>HTML</b> file for perfect rendering — all fonts load automatically
            in your browser.
        </div>""", unsafe_allow_html=True)

    if uploaded_file:
        st.success(f"✅ File ready: **{uploaded_file.name}**")

    translate_clicked = st.button(
        f"🔄 Translate to {target_language}",
        type="primary",
        disabled=not (uploaded_file and api_key),
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

            lang_code = cfg["code"]

            # ── Build all three download formats ──
            html_bytes = build_html(translation_text, target_language)
            md_bytes   = build_markdown(translation_text)
            txt_bytes  = build_txt(translation_text)

            st.markdown('<div class="download-section">', unsafe_allow_html=True)
            st.markdown('<div class="download-label">📥 Download translated notes as:</div>', unsafe_allow_html=True)

            dl1, dl2, dl3 = st.columns(3)

            with dl1:
                st.download_button(
                    label="🌐 HTML",
                    data=html_bytes,
                    file_name=f"translated_{lang_code}.html",
                    mime="text/html",
                    help="Open in browser → Ctrl+P → Save as PDF. Best for Hindi/Gujarati scripts.",
                    use_container_width=True,
                )
            with dl2:
                st.download_button(
                    label="📝 Markdown",
                    data=md_bytes,
                    file_name=f"translated_{lang_code}.md",
                    mime="text/markdown",
                    help="Open in Notion, Obsidian, VS Code, or any Markdown editor.",
                    use_container_width=True,
                )
            with dl3:
                st.download_button(
                    label="📄 Plain Text",
                    data=txt_bytes,
                    file_name=f"translated_{lang_code}.txt",
                    mime="text/plain",
                    help="Clean plain text — works everywhere, any language.",
                    use_container_width=True,
                )

            st.markdown("</div>", unsafe_allow_html=True)

            st.caption(
                "💡 **Best for PDF:** Download the HTML file, open it in Chrome/Safari/Firefox, "
                "then press **Ctrl+P** (or ⌘+P) → **Save as PDF**. "
                "This correctly renders Hindi and Gujarati scripts — something the old PDF library could not do."
            )

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

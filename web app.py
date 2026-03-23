import os
import html
import tempfile
import streamlit as st

# ──────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────

st.set_page_config(
    page_title="Local File Converter",
    layout="centered"
)

st.html("""
<style>
.block-container {
    max-width: 820px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}

h1, h2, h3 {
    letter-spacing: 0.5px;
}

.stButton > button {
    width: 100%;
    background: #8b0000;
    color: #e6e6eb;
    border: 1px solid #2a0a0a;
    border-radius: 6px;
    font-weight: 600;
}
.stButton > button:hover {
    background: #a11212;
    color: #f2f2f2;
}

[data-testid="stFileUploader"] {
    border: 1px solid #1f1f2a;
    border-radius: 6px;
    padding: 0.4rem;
    background: #121217;
}

[data-baseweb="select"] > div {
    background-color: #121217;
    border: 1px solid #1f1f2a;
    border-radius: 6px;
}

hr {
    border: none;
    border-top: 1px solid #1a1a22;
    margin: 1.5rem 0;
}
</style>
""")

# ──────────────────────────────────────────────
# CONVERSION FUNCTIONS
# ──────────────────────────────────────────────

def convert_image(input_path, output_format):
    from PIL import Image

    img = Image.open(input_path)

    if output_format.upper() in ("JPEG", "JPG") and img.mode in ("RGBA", "P", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        alpha = img.getchannel("A") if "A" in img.getbands() else None
        if alpha:
            background.paste(img, mask=alpha)
        else:
            background.paste(img)
        img = background

    base = os.path.splitext(input_path)[0]
    ext = "jpg" if output_format.upper() == "JPEG" else output_format.lower()
    output_path = f"{base}_converted.{ext}"

    img.save(output_path, format=output_format.upper())
    return output_path


def convert_document(input_path, output_format):
    import_ext = os.path.splitext(input_path)[1].lower()
    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_converted.{output_format.lower()}"

    text = ""

    if import_ext == ".docx":
        from docx import Document
        doc = Document(input_path)
        text = "\n".join(p.text for p in doc.paragraphs)

    elif import_ext == ".txt":
        with open(input_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

    elif import_ext == ".pdf":
        import PyPDF2
        with open(input_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)

    elif import_ext == ".epub":
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup

        book = epub.read_epub(input_path)
        chapters = []

        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_content(), "html.parser")
                chapters.append(soup.get_text("\n", strip=True))

        text = "\n\n".join(chapters)

    else:
        raise ValueError("Unsupported file type")

    if output_format.lower() == "txt":
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

    elif output_format.lower() == "docx":
        from docx import Document
        doc = Document()
        for line in text.splitlines():
            doc.add_paragraph(line)
        doc.save(output_path)

    elif output_format.lower() == "pdf":
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)

        for line in text.splitlines():
            safe = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 7, safe if safe else " ")

        pdf.output(output_path)

    elif output_format.lower() == "epub":
        from ebooklib import epub

        book = epub.EpubBook()
        book.set_identifier("id")
        book.set_title("Converted File")
        book.set_language("en")

        content = html.escape(text).replace("\n", "<br>")
        chapter = epub.EpubHtml(title="Content", file_name="content.xhtml")
        chapter.content = f"<h1>Converted</h1><p>{content}</p>"

        book.add_item(chapter)
        book.toc = (chapter,)
        book.spine = ["nav", chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        epub.write_epub(output_path, book)

    return output_path


def convert_audio_video(input_path, output_format):
    import moviepy.editor as mp

    base = os.path.splitext(input_path)[0]
    output_path = f"{base}_converted.{output_format.lower()}"

    clip = mp.VideoFileClip(input_path)

    if output_format.lower() in ["mp3", "wav"]:
        clip.audio.write_audiofile(output_path)
    else:
        clip.write_videofile(output_path)

    clip.close()
    return output_path


# ──────────────────────────────────────────────
# FORMAT DETECTION
# ──────────────────────────────────────────────

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif"}
DOC_EXTS   = {".docx", ".txt", ".pdf", ".epub"}
MEDIA_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".mp3", ".wav"}

DOC_OUTPUTS = {
    ".docx": ["TXT", "PDF", "EPUB"],
    ".txt": ["DOCX", "PDF", "EPUB"],
    ".pdf": ["TXT", "DOCX", "EPUB"],
    ".epub": ["TXT", "DOCX", "PDF"],
}


def get_output_formats(filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext in IMAGE_EXTS:
        return "image", ["PNG", "JPEG", "WEBP", "BMP", "GIF"]
    elif ext in DOC_EXTS:
        return "document", DOC_OUTPUTS[ext]
    elif ext in MEDIA_EXTS:
        return "media", ["MP4", "MP3", "WAV"]
    return None, []


# ──────────────────────────────────────────────
# UI
# ──────────────────────────────────────────────

st.title("Local File Converter")
st.caption("Convert images, documents, and media files")

st.divider()

uploaded_file = st.file_uploader("Choose a file")

if uploaded_file:
    category, formats = get_output_formats(uploaded_file.name)

    if not formats:
        st.error("Unsupported file type")
    else:
        st.write(f"Detected file type: {category.upper()}")

        fmt = st.selectbox("Convert to", formats)

        if st.button("Convert"):
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, uploaded_file.name)

                with open(path, "wb") as f:
                    f.write(uploaded_file.read())

                if category == "image":
                    out = convert_image(path, fmt)
                elif category == "document":
                    out = convert_document(path, fmt)
                else:
                    out = convert_audio_video(path, fmt)

                with open(out, "rb") as f:
                    st.download_button(
                        "Download file",
                        f.read(),
                        file_name=os.path.basename(out)
                    )

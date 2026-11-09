import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import os

# WebBaseLoader warns if this isn't set, since some sites use it to identify
# well-behaved scrapers vs. bots.
os.environ.setdefault("USER_AGENT", "agenticai-course-demo/1.0")

from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyPDFLoader,
    WebBaseLoader,
    CSVLoader,
    NotionDirectoryLoader,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def show(label: str, docs: List[Document], preview_chars: int = 150) -> None:
    print(f"\n{'=' * 70}")
    print(f"{label} - {len(docs)} document(s) loaded")
    print("=" * 70)
    for i, doc in enumerate(docs[:3], start=1):
        preview = doc.page_content.strip().replace("\n", " ")[:preview_chars]
        print(f"{i}. metadata={doc.metadata}")
        print(f"   content: {preview}...")

# -----------------------------
# 1. PDF Loader
# Splits a PDF into one Document per page, with page number in metadata.
# Reuses the Principles-of-Data-Science.pdf already used in 9_general/rag.
# -----------------------------
pdf_path = os.path.join(BASE_DIR, "..", "..", "9_general", "rag", "Principles-of-Data-Science.pdf")
pdf_docs = PyPDFLoader(pdf_path).load()
show("1. PyPDFLoader", pdf_docs)

# -----------------------------
# 2. Web Loader
# Fetches a live web page and strips it down to its text content via
# BeautifulSoup. One Document per URL by default.
# -----------------------------
web_docs = WebBaseLoader(["https://en.wikipedia.org/wiki/Artificial_intelligence"]).load()
show("2. WebBaseLoader", web_docs)

# -----------------------------
# 3. CSV Loader
# One Document per ROW, with each column rendered as "column: value" text
# and the row's column values also kept in metadata.
# Reuses the documents.csv already used by the 04_rag demos.
# -----------------------------
csv_path = os.path.join(BASE_DIR, "..", "04_rag", "documents.csv")
csv_docs = CSVLoader(csv_path).load()
show("3. CSVLoader", csv_docs)

# -----------------------------
# 4. Notion Loader
# Reads every .md file out of a directory (this is the format Notion's
# "Export as Markdown" produces) - one Document per page.
# -----------------------------
notion_path = os.path.join(BASE_DIR, "sample_notion_export")
notion_docs = NotionDirectoryLoader(notion_path).load()
show("4. NotionDirectoryLoader", notion_docs)

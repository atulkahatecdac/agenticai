import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import base64
import os
import sys
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv(override=True)

# The scanned form contains Spanish text - reconfigure stdout to UTF-8 so
# printing the extracted text doesn't crash on Windows' default codepage.
sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_PATH = os.path.join(BASE_DIR, "ocr.jpg")

# gpt-4o-mini is vision-capable, so no separate OCR library (pytesseract etc.)
# is needed - the image goes straight into the chat message as an
# "image_url" content block, same as the X-ray example in
# 08_langgraph_cycles_HIL_persistence/08_7_medical_diagnosis_subgraphs.py.
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

with open(IMAGE_PATH, "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

message = HumanMessage(content=[
    {
        "type": "text",
        "text": (
            "This is a scanned paper form being digitized for a document-processing "
            "pipeline demo. Perform OCR on it: transcribe every visible character - "
            "printed labels, handwritten or typed entries, and checkbox states - "
            "exactly as they appear, preserving the original line breaks and layout. "
            "Do not translate, summarize, or omit any field."
        ),
    },
    {"type": "image_url", "image_url": {"url": f"data:image/jpg;base64,{image_b64}"}},
])

response = llm.invoke([message])
print(response.content)

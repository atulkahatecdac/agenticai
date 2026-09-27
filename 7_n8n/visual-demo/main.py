from fastapi import FastAPI, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from PIL import Image
from io import BytesIO
import os
import uuid

import torch
import torch.nn.functional as F

from facenet_pytorch import MTCNN, InceptionResnetV1


app = FastAPI()


# Folder holding the database photos (P001.jpg ... P050.jpg)
IMAGE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "synthetic_people_demo")
)

# Folder where user-uploaded photos are kept so the result page can show them
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# Face detector
mtcnn = MTCNN(
    image_size=160,
    margin=20,
    keep_all=False,
    post_process=True
)


# Face embedding model
model = InceptionResnetV1(
    pretrained="vggface2"
).eval()


@app.get("/")
def root():
    return {
        "service": "Local Vision Embedding Service",
        "status": "running"
    }


@app.post("/embedding")
async def create_embedding(image: UploadFile, save: bool = Form(True)):

    # Read uploaded image
    contents = await image.read()

    try:
        img = Image.open(
            BytesIO(contents)
        ).convert("RGB")
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image"
        )

    # Detect and crop face
    face = mtcnn(img)

    if face is None:
        raise HTTPException(
            status_code=400,
            detail="No face detected"
        )

    # Add batch dimension
    face = face.unsqueeze(0)

    # Generate embedding
    with torch.no_grad():
        embedding = model(face)

    # Normalize vector
    embedding = F.normalize(
        embedding,
        p=2,
        dim=1
    )

    vector = embedding[0].tolist()

    # Keep a copy so the browser can load it from /uploads/<upload_file>
    upload_file = None
    if save:
        upload_file = f"{uuid.uuid4().hex}.jpg"
        img.save(os.path.join(UPLOAD_DIR, upload_file), "JPEG")

    return {
        "filename": image.filename,
        "upload_file": upload_file,
        "dimensions": len(vector),
        "embedding": vector
    }


def serve_file(folder, file_name):

    # basename() blocks path tricks like ../../secret.txt
    path = os.path.join(folder, os.path.basename(file_name))

    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail="Image not found"
        )

    return FileResponse(path)


@app.get("/images/{image_file}")
def get_image(image_file: str):
    return serve_file(IMAGE_DIR, image_file)


@app.get("/uploads/{upload_file}")
def get_upload(upload_file: str):
    return serve_file(UPLOAD_DIR, upload_file)


if __name__ == "__main__":
    import uvicorn

    # 0.0.0.0 so the Dockerized n8n can reach it via host.docker.internal:8001
    uvicorn.run(app, host="0.0.0.0", port=8001)

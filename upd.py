import uvicorn
import zipfile
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import urllib.parse

app = FastAPI()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename.strip())  # strip spaces
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    return {"filename": file.filename.strip()}

@app.post("/upload-folder")
async def upload_folder(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename.strip())
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Extract ZIP
    if file.filename.endswith(".zip"):
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            zip_ref.extractall(UPLOAD_DIR)

    return {"status": "folder uploaded and extracted"}

@app.get("/files")
async def list_files():
    files = os.listdir(UPLOAD_DIR)
    # return proper links with URL encoding
    file_links = [
        f"http://192.168.1.5:8000/download/{urllib.parse.quote(file)}"
        for file in files
    ]
    return {"files": file_links}

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        return {"error": "File not found"}
    return FileResponse(file_path, filename=filename)
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
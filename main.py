import uvicorn
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from typing import List
from PIL import Image
from io import BytesIO
from zipfile import ZipFile
from pdf2image import convert_from_bytes
import traceback

app = FastAPI()

origins = [
    "http://localhost:5173",  # Vite default
    "http://localhost:3000",  # CRA/Next.js default
]


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # or ["*"] for all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- PDF → JPG ----------------
@app.post("/pdf-to-jpg")
async def convert_pdf_to_jpg(
    file: UploadFile = File(...),
    password: str = Form(None)  # optional password
):
    try:
        contents = await file.read()

        # Check if PDF is encrypted
        reader = PdfReader(BytesIO(contents))
        if reader.is_encrypted:
            if not password or not reader.decrypt(password):
                return JSONResponse(
                    status_code=403,
                    content={"error": "PDF is password protected. Provide the correct password."}
                )

            # Rebuild decrypted PDF in memory
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            decrypted_io = BytesIO()
            writer.write(decrypted_io)
            decrypted_io.seek(0)
            contents = decrypted_io.read()

        # Now safely convert
        images = convert_from_bytes(contents, fmt="jpeg")

        if len(images) == 1:
            img_io = BytesIO()
            images[0].save(img_io, format="JPEG")
            img_io.seek(0)
            return StreamingResponse(img_io, media_type="image/jpeg", headers={
                "Content-Disposition": "attachment; filename=converted.jpg"
            })
        else:
            zip_io = BytesIO()
            with ZipFile(zip_io, "w") as zip_file:
                for i, img in enumerate(images):
                    img_bytes = BytesIO()
                    img.save(img_bytes, format="JPEG")
                    img_bytes.seek(0)
                    zip_file.writestr(f"page_{i+1}.jpg", img_bytes.read())
            zip_io.seek(0)
            return StreamingResponse(zip_io, media_type="application/zip", headers={
                "Content-Disposition": "attachment; filename=converted_images.zip"
            })

    except Exception as e:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------- JPG → PDF ----------------
@app.post("/jpg-to-pdf")
async def convert_images_to_pdf(files: List[UploadFile] = File(...)):
    try:
        images = [Image.open(BytesIO(await f.read())).convert("RGB") for f in files]

        if not images:
            return JSONResponse(status_code=400, content={"error": "No valid images provided"})

        pdf_io = BytesIO()
        images[0].save(pdf_io, format="PDF", save_all=True, append_images=images[1:])
        pdf_io.seek(0)

        return StreamingResponse(pdf_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=converted.pdf"
        })
    except Exception:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Failed to convert JPG to PDF"})

# ---------------- Lock PDF ----------------
@app.post("/lock-pdf")
async def lock_pdf(file: UploadFile = File(...), password: str = Form("secure123")):
    try:
        contents = await file.read()
        reader = PdfReader(BytesIO(contents))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)

        output_io = BytesIO()
        writer.write(output_io)
        output_io.seek(0)

        return StreamingResponse(output_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=locked.pdf"
        })
    except Exception:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Failed to lock PDF"})

# ---------------- Unlock PDF ----------------
@app.post("/unlock-pdf")
async def unlock_pdf(file: UploadFile = File(...), password: str = Form(...)):
    try:
        contents = await file.read()
        reader = PdfReader(BytesIO(contents))

        if reader.is_encrypted:
            if not reader.decrypt(password):
                return JSONResponse(status_code=403, content={"error": "Incorrect password or decryption failed"})

        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)

        output_io = BytesIO()
        writer.write(output_io)
        output_io.seek(0)

        return StreamingResponse(output_io, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=unlocked.pdf"
        })
    except Exception:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Failed to unlock PDF"})

# ---------------- Compress PDF ----------------
@app.post("/compress-pdf")
async def compress_pdf(file: UploadFile = File(...), compression_ratio: int = Form(50)):
    try:
        if not (1 <= compression_ratio <= 100):
            return JSONResponse(status_code=400, content={"error": "Compression ratio must be between 1 and 100"})

        contents = await file.read()
        pdf_in = fitz.open(stream=contents, filetype="pdf")

        for page_index in range(len(pdf_in)):
            images = pdf_in.get_page_images(page_index)
            for img in images:
                xref = img[0]
                base_image = pdf_in.extract_image(xref)
                image_bytes = base_image["image"]

                image = Image.open(BytesIO(image_bytes)).convert("RGB")
                img_io = BytesIO()
                image.save(img_io, format="JPEG", quality=compression_ratio)
                img_io.seek(0)

                pdf_in.update_stream(xref, img_io.read())

        out_stream = BytesIO()
        pdf_in.save(out_stream)
        out_stream.seek(0)

        return StreamingResponse(out_stream, media_type="application/pdf", headers={
            "Content-Disposition": "attachment; filename=compressed.pdf"
        })
    except Exception:
        print("Error:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": "Failed to compress PDF"})

# ---------------- Run ----------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



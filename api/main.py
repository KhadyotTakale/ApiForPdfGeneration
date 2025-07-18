import os
import io
import time
import shutil
import requests
import threading
from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

PDF_DIR = "invoices"
os.makedirs(PDF_DIR, exist_ok=True)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PDFRequest(BaseModel):
    url: str
    id: str
    callback_url: str

def delete_file_later(path: str, delay: int = 7200):
    def _delete():
        time.sleep(delay)
        if os.path.exists(path):
            os.remove(path)
            print(f"🗑️ Deleted {path}")
    threading.Thread(target=_delete, daemon=True).start()

def send_callback(callback_url: str, pdf_url: str, invoice_id: str):
    try:
        response = requests.post(callback_url, json={
            "id": invoice_id,
            "pdf_url": pdf_url
        }, timeout=10)
        print(f"✅ Callback sent ({response.status_code})")
    except Exception as e:
        print("❌ Callback failed:", str(e))

@app.post("/generate-pdf")
def generate_pdf(
    payload: PDFRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(default=None)
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    invoice_id = payload.id
    filename = f"{invoice_id}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(payload.url, wait_until="networkidle")
            try:
                page.wait_for_selector("body", timeout=5000)
            except PlaywrightTimeout:
                print("⚠️ Body not found in time.")
            pdf_bytes = page.pdf(format="A4", print_background=True)
            browser.close()

            with open(filepath, "wb") as f:
                f.write(pdf_bytes)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    pdf_url = f"https://web-production-1675c.up.railway.app/invoices/{invoice_id}.pdf"

    background_tasks.add_task(send_callback, payload.callback_url, pdf_url, invoice_id)

    delete_file_later(filepath, delay=7200)

    return {"status": "PDF generated", "id": invoice_id, "pdf_url": pdf_url}

@app.get("/invoices/{filename}")
def serve_pdf(filename: str):
    filepath = os.path.join(PDF_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(filepath, media_type="application/pdf", filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

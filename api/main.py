from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from playwright.sync_api import sync_playwright
import tempfile
import os
import uvicorn

app = FastAPI()

class PDFRequest(BaseModel):
    url: str

@app.get("/")  # ✅ Add this so Railway shows homepage
def read_root():
    return {"message": "✅ API is live and working"}

@app.post("/generate-pdf")
def generate_pdf(request: PDFRequest):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 1800}, device_scale_factor=2)
            page = context.new_page()
            page.goto(request.url, wait_until="networkidle")
            page.wait_for_timeout(3000)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                page.pdf(path=tmp.name, format="A4", print_background=True, scale=1)
                browser.close()
                return FileResponse(tmp.name, filename="invoice.pdf", media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))  # ✅ Use Railway's dynamic port
    uvicorn.run("api.main:app", host="0.0.0.0", port=port)

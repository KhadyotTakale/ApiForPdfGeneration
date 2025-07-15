import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from urllib.parse import urlparse
import io

app = FastAPI()

class PDFRequest(BaseModel):
    url: str

@app.post("/generate-pdf")
def generate_pdf(payload: PDFRequest):
    # Extract ID from URL
    path = urlparse(payload.url).path
    invoice_id = path.rstrip("/").split("/")[-1]
    print("Extracted ID:", invoice_id)

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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    return StreamingResponse(
        content=io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={invoice_id}.pdf",
            "X-INVOICE-ID": invoice_id  # ✅ You can see this in Postman response headers
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

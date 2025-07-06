import os
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware  
from pydantic import BaseModel
from playwright.sync_api import sync_playwright

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

@app.post("/generate-pdf")
def generate_pdf(request: PDFRequest):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 1800})
            page = context.new_page()

            print(f"Generating PDF for: {request.url}") 

            page.goto(request.url, wait_until="networkidle")
            page.wait_for_timeout(3000)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                pdf_path = tmp.name
                page.pdf(
                    path=pdf_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
                    scale=1,
                    display_header_footer=False
                )

            browser.close()

            return FileResponse(
                pdf_path,
                filename="invoice.pdf",
                media_type="application/pdf",
                headers={"Content-Disposition": "attachment; filename=invoice.pdf"},
                background=lambda: os.remove(pdf_path)  
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

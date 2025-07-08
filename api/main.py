import os
import uuid
import requests
from io import BytesIO
from fastapi import FastAPI, HTTPException, Header, Request, BackgroundTasks
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

START_WEBHOOK_URL = os.getenv("START_WEBHOOK_URL", "http://localhost:8000/start-webhook")

class PDFRequest(BaseModel):
    url: str
    callback_url: str

def send_webhook(url: str, data: dict, token: str = ""):
    try:
        headers = {"Authorization": token} if token else {}
        requests.post(url, json=data, headers=headers, timeout=5)
    except Exception as e:
        print(f"Webhook to {url} failed:", e)

@app.post("/generate-pdf")
def generate_pdf(
    payload: PDFRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    wimsup_api_key: str = Header(default=None, alias="WIMSUP-API-KEY"),
    authorization: str = Header(default=None)
):
    token = wimsup_api_key or (authorization if authorization and authorization.lower().startswith("bearer ") else None)
    if not token:
        raise HTTPException(status_code=401, detail="Missing WIMSUP-API-KEY or Bearer token")

    request_id = str(uuid.uuid4())

    header_keys = list(request.headers.keys())
    first_payload = {
        "id": request_id,
        "url": payload.url,
        "callback_url": payload.callback_url,
        "headers": header_keys
    }

    try:
        response = requests.post(
            START_WEBHOOK_URL,
            json=first_payload,
            headers={"Authorization": token},
            timeout=5
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail="Start webhook failed")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Start webhook error: {str(e)}")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 1800})
            page = context.new_page()
            page.goto(payload.url, wait_until="networkidle")

            try:
                page.wait_for_selector("body", timeout=5000)
            except PlaywrightTimeout:
                print("⚠️ <body> not found in time.")

            pdf_bytes = page.pdf(
                format="A4",
                print_background=True,
                margin={"top": "0px", "bottom": "0px", "left": "0px", "right": "0px"},
                scale=1,
                display_header_footer=False
            )
            browser.close()

    except Exception as e:
        error_data = {"id": request_id, "error": str(e)}
        background_tasks.add_task(send_webhook, payload.callback_url, error_data)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    success_data = {"id": request_id, "pdf_url": "inline"}  
    background_tasks.add_task(send_webhook, payload.callback_url, success_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=invoice.pdf"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


# @app.post("/start-webhook")
# def mock_start_webhook(data: dict):
#     print("📡 Start webhook hit:")
#     print(data)
#     return {"status": "received"}

# @app.post("/mock-callback")
# def mock_callback(data: dict):
#     print("✅ Callback received:")
#     print(data)
#     return {"status": "callback received"}

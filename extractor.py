"""
extractor.py
Reads electricity bill image/PDF using Groq Vision (Free)
"""

import groq
import base64
import os
import json
import re
import fitz
from dotenv import load_dotenv

load_dotenv()
client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))


def load_bill_as_base64(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        doc = fitz.open(file_path)
        page = doc[0]
        pix = page.get_pixmap(dpi=200)
        img_path = file_path.replace(".pdf", "_converted.png")
        pix.save(img_path)
        doc.close()
        with open(img_path, "rb") as f:
            return base64.b64encode(f.read()).decode(), "image/png"
    else:
        media_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                     ".png": "image/png", ".webp": "image/webp"}
        media_type = media_map.get(ext, "image/jpeg")
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode(), media_type


def extract_bill_data(file_path: str) -> dict:
    try:
        img_data, media_type = load_bill_as_base64(file_path)
    except Exception as e:
        raise ValueError(f"Could not read bill file: {str(e)}")

    prompt = """
You are analyzing a Maharashtra MSEDCL electricity bill.
Extract the following fields carefully.
Return ONLY a valid JSON object. No explanation, no markdown, no extra text.

{
  "consumer_name": "full name on bill",
  "consumer_no": "consumer number as string",
  "fixed_charges": numeric value only,
  "sanctioned_load": "e.g. 1KW or 3.30KW",
  "connection_type": "e.g. LT I Res 1-Phase",
  "bill_amount": numeric total payable amount,
  "monthly_units": [
    {"month": "YYYY-MM-01", "units": numeric}
  ]
}

Rules:
- Extract ALL monthly unit readings from bar chart or history table
- Sort monthly_units oldest to newest
- If a field is not found, use null
- Return ONLY the JSON object, nothing else
"""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{media_type};base64,{img_data}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }]
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        raise ConnectionError(f"Groq API error: {str(e)}")

    try:
        raw = re.sub(r"```json|```", "", raw).strip()
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Could not parse response as JSON. Raw:\n{raw}")

    required = ["consumer_name", "consumer_no", "monthly_units"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    return data
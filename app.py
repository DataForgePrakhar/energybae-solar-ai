"""
app.py
Energybae Solar Bill to Quotation System
Flask web application — Upload bill → AI reads → Excel output
"""

import os
import uuid
from datetime import datetime

from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

from customers import save_customer, load_all_customers, load_customer, update_customer, delete_customer
from mailer import send_quotation_email
import os
import uuid
from datetime import datetime

from extractor import extract_bill_data
from excel_filler import fill_excel, get_summary_from_excel

load_dotenv()

app = Flask(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
app.config["UPLOAD_FOLDER"]   = "uploads"
app.config["OUTPUT_FOLDER"]   = "outputs"
app.config["TEMPLATE_PATH"]   = "solar_template.xlsx"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB max upload

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "pdf"}


# ── Helpers ───────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def cleanup_old_files(folder: str, max_files: int = 50):
    """Keep folders clean — delete oldest files if limit exceeded."""
    files = sorted(
        [os.path.join(folder, f) for f in os.listdir(folder)],
        key=os.path.getctime
    )
    while len(files) > max_files:
        os.remove(files.pop(0))


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "bill" not in request.files:
        return jsonify({"error": "No file uploaded. Please select a bill image or PDF."}), 400

    file = request.files["bill"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Please upload JPG, PNG, WEBP or PDF."}), 400

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)

    try:
        file.save(upload_path)
    except Exception as e:
        return jsonify({"error": f"Could not save uploaded file: {str(e)}"}), 500

    try:
        data = extract_bill_data(upload_path)
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        return jsonify({"error": f"Unexpected error during extraction: {str(e)}"}), 500

    # Generate output Excel filename
    full_name = data.get("consumer_name", "Customer")
    first_name = full_name.strip().split()[-1].title()

    monthly = data.get("monthly_units", [])
    if monthly:
        last_month = monthly[-1].get("month", "")
        try:
            month_label = datetime.strptime(last_month, "%Y-%m-%d").strftime("%b%Y")
        except:
            try:
                month_label = datetime.strptime(last_month, "%Y-%m-01").strftime("%b%Y")
            except:
                month_label = datetime.now().strftime("%b%Y")
    else:
        month_label = datetime.now().strftime("%b%Y")

    output_filename = f"Energybae_Solar_Quotation_{first_name}_{month_label}.xlsx"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    try:
        fill_excel(data, app.config["TEMPLATE_PATH"], output_path)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Could not generate Excel: {str(e)}"}), 500

    summary = get_summary_from_excel(data)

    # ── Save customer to history ──────────────────────────────
    save_customer(data, summary, output_filename)

    return jsonify({
        "success": True,
        "consumer_name":    data.get("consumer_name"),
        "consumer_no":      data.get("consumer_no"),
        "sanctioned_load":  data.get("sanctioned_load"),
        "connection_type":  data.get("connection_type"),
        "bill_amount":      data.get("bill_amount"),
        "monthly_units":    data.get("monthly_units", []),
        "summary":          summary,
        "download_file":    output_filename,
        "months_extracted": len(data.get("monthly_units", []))
    })


@app.route("/download/<filename>")
def download(filename):
    filename = secure_filename(filename)
    file_path = os.path.join(app.config["OUTPUT_FOLDER"], filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found or expired."}), 404

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/health")
def health():
    return jsonify({
        "status": "running",
        "template_exists": os.path.exists(app.config["TEMPLATE_PATH"]),
        "gemini_key_set": bool(os.getenv("GEMINI_API_KEY"))
    })


# ── Customer Routes ───────────────────────────────────────────────────────────

@app.route("/customer")
def customer_page():
    return render_template("customer.html")


@app.route("/customers")
def customers():
    return jsonify(load_all_customers())


@app.route("/customers/<customer_id>")
def get_customer(customer_id):
    customer = load_customer(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify(customer)


@app.route("/customers/<customer_id>/update", methods=["POST"])
def update_customer_route(customer_id):
    updated_data = request.json
    if not updated_data:
        return jsonify({"error": "No data provided"}), 400
    success = update_customer(customer_id, updated_data)
    return jsonify({"success": success})


@app.route("/customers/<customer_id>/regenerate", methods=["POST"])
def regenerate(customer_id):
    customer = load_customer(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    first_name = customer.get("consumer_name", "Customer").strip().split()[-1].title()
    monthly = customer.get("monthly_units", [])
    month_label = datetime.now().strftime("%b%Y")
    if monthly:
        try:
            month_label = datetime.strptime(
                monthly[-1].get("month", ""), "%Y-%m-01").strftime("%b%Y")
        except:
            pass

    output_filename = f"Energybae_Solar_Quotation_{first_name}_{month_label}.xlsx"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    try:
        fill_excel(customer, app.config["TEMPLATE_PATH"], output_path)
        update_customer(customer_id, {"latest_file": output_filename})
        return jsonify({"success": True, "download_file": output_filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/customers/<customer_id>/send-email", methods=["POST"])
def send_email(customer_id):
    customer = load_customer(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    to_email = request.json.get("email", "").strip()
    if not to_email or "@" not in to_email:
        return jsonify({"error": "Invalid email address"}), 400

    filename = customer.get("latest_file", "")
    excel_path = os.path.join(app.config["OUTPUT_FOLDER"], filename)

    result = send_quotation_email(to_email, customer, excel_path)
    return jsonify(result)


@app.route("/customers/<customer_id>/delete", methods=["POST"])
def delete_customer_route(customer_id):
    success = delete_customer(customer_id)
    return jsonify({"success": success})


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("outputs", exist_ok=True)

    print("\n🌿 Energybae Solar Quotation System")
    print("   Running at: http://localhost:5000\n")
    app.run(debug=True)
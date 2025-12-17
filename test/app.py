
import os
import io
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError
from pypdf import PdfReader

# Local imports
from extraction_schema import ProcurementData
from db_setup import setup_database

# --- Initialization ---
load_dotenv()
app = Flask(__name__)

# Constants
DB_NAME = 'ProcRequests.db'
LLM_MODEL = "gpt-4"  # Using your available model
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)


# --- Helper Logic ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def extract_text_from_pdf(file_bytes):
    """
    Extracts readable text from a PDF stream. 
    Prevents Context Length errors by avoiding binary data.
    """
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        # Extract from first 3 pages (where invoice/offer data usually lives)
        for page in reader.pages[:3]:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"PDF Parsing Error: {e}")
        return ""


def extract_data_via_ai(document_text):
    """
    Improved extraction using Few-Shot prompting and strict field mapping.
    """
    system_prompt = (
        "You are a professional procurement data extractor. Your goal is to parse vendor offers into a specific JSON format.\n\n"
        "STRICT RULES:\n"
        "1. Extract ONLY the following fields: requestor_name, title, vendor_name, vat_id, total_cost, department, extracted_description_text, order_lines.\n"
        "2. 'order_lines' must be a list of objects with these EXACT keys: description, unit_price, amount, unit, total_price.\n"
        "3. All price and amount fields MUST be numbers (floats/integers). Remove currency symbols like € or $.\n"
        "4. If a field like 'requestor_name' is missing, default to 'Vladimir Keil'.\n"
        "5. If 'department' is missing, default to 'Operations'.\n"
        "6. 'extracted_description_text' should be a summary of all items (e.g. 'Photoshop and Illustrator Licenses').\n\n"
        "--- PERFECT EXAMPLE ---\n"
        "Input: 'Global Tech Solutions, VAT: DE987654321. Offer for Creative Marketing. 10x Photoshop @ 150 each, Total 1500.'\n"
        "Output: {\n"
        '  "requestor_name": "Vladimir Keil",\n'
        '  "title": "Software Licenses",\n'
        '  "vendor_name": "Global Tech Solutions",\n'
        '  "vat_id": "DE987654321",\n'
        '  "total_cost": 1500.0,\n'
        '  "department": "Creative Marketing",\n'
        '  "extracted_description_text": "Adobe Photoshop License 10 units",\n'
        '  "order_lines": [\n'
        '    {"description": "Adobe Photoshop License", "unit_price": 150.0, "amount": 10.0, "unit": "licenses", "total_price": 1500.0}\n'
        '  ]\n'
        "}\n"
        "--- END EXAMPLE ---\n\n"
        "Return ONLY the raw JSON object for the text provided by the user."
    )
    
    # Stay within gpt-4 context limits
    truncated_text = document_text[:12000]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document Text:\n{truncated_text}"}
        ],
        temperature=0  # Set to 0 for maximum consistency and accuracy
    )
    
    content = response.choices[0].message.content.strip()
    
    # Remove markdown code blocks if the AI includes them
    if "```" in content:
        content = content.split("```")[1].replace("json", "").strip()

    try:
        # 1. Try to validate with Pydantic first
        return ProcurementData.model_validate_json(content).model_dump()
    except Exception as e:
        print(f"Validation failed, attempting manual JSON fix: {e}")
        try:
            # 2. Fallback: Parse raw JSON and manually fix common mismatches
            raw_data = json.loads(content)
            
            # Auto-fix common field name hallucinations
            if "items" in raw_data and "order_lines" not in raw_data:
                raw_data["order_lines"] = raw_data.pop("items")
            
            for line in raw_data.get("order_lines", []):
                if "item" in line: line["description"] = line.pop("item")
                if "price" in line: line["unit_price"] = line.pop("price")
                if "quantity" in line: line["amount"] = line.pop("quantity")
                if "total" in line: line["total_price"] = line.pop("total")
                
            return raw_data
        except Exception:
            # 3. Final Fallback: Return empty data if everything fails
            return {
                'requestor_name': 'Vladimir Keil', 'title': 'Extraction Error',
                'vendor_name': 'Unknown', 'vat_id': 'N/A', 'total_cost': 0.0,
                'department': 'Operations', 'order_lines': [], 'extracted_description_text': ''
            }

# --- Routes ---

@app.route('/')
def overview():
    """Dashboard showing existing procurement requests."""
    conn = get_db_connection()
    requests_list = conn.execute("SELECT * FROM requests ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('overview.html', requests=requests_list)


@app.route('/new_request', methods=['GET', 'POST'])
def new_request():
    """Handles manual entry and AI-assisted pre-filling."""
    # List of groups for the dropdown
    all_groups = ["Facility Management Services", "IT & Telecommunication", "Logistics", 
                  "Marketing & Advertising", "Production"]
    
    # Default data to prevent Jinja2 UndefinedError
    data = {
        'requestor_name': 'Vladimir Keil', 'title': '', 'vendor_name': '',
        'vat_id': '', 'total_cost': 0.0, 'department': 'Operations',
        'order_lines': [], 'commodity_group': ''
    }

    if request.method == 'POST':
        # --- PHASE 1: AI Scan Request ---
        if 'offer_file' in request.files and request.files['offer_file'].filename != '':
            file = request.files['offer_file']
            raw_bytes = file.read()
            clean_text = extract_text_from_pdf(raw_bytes)
            
            if clean_text:
                ai_data = extract_data_via_ai(clean_text)
                if ai_data:
                    data.update(ai_data)
            
            return render_template('new_request.html', data=data, all_groups=all_groups)

        # --- PHASE 2: Manual Form Submission (Save to DB) ---
        form = request.form
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO requests (requestor_name, title, vendor_name, vat_id, 
                                         commodity_group, department, total_cost, status) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'Open')""",
                (form['requestor_name'], form['title'], form['vendor_name'], form['vat_id'],
                 form['commodity_group'], form['department'], float(form['total_cost']))
            )
            conn.commit()
            return redirect(url_for('overview'))
        except Exception as e:
            return f"Database Error: {e}", 500
        finally:
            conn.close()

    return render_template('new_request.html', data=data, all_groups=all_groups)


@app.route('/update_status/<int:req_id>', methods=['POST'])
def update_status(req_id):
    """API endpoint for changing status and logging in history."""
    new_status = request.json.get('status')
    user = request.json.get('user', 'Procurement Manager')
    
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status = ? WHERE request_id = ?", (new_status, req_id))
    
    # Log to status_history (audit trail)
    conn.execute(
        "INSERT INTO status_history (request_id, new_status, changer_user) VALUES (?, ?, ?)",
        (req_id, new_status, user)
    )
    conn.commit()
    conn.close()
    return jsonify({"success": True})


if __name__ == '__main__':
    setup_database()
    app.run(debug=True)
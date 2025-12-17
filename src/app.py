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
LLM_MODEL = "gpt-4" 
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# The official master list of 50 Commodity Groups
COMMODITY_GROUPS = [
    "Accommodation Rentals", "Membership Fees", "Workplace Safety", "Consulting",
    "Financial Services", "Fleet Management", "Recruitment Services", "Professional Development",
    "Miscellaneous Services", "Insurance", "Electrical Engineering", "Facility Management Services",
    "Security", "Renovations", "Office Equipment", "Energy Management", "Maintenance",
    "Cafeteria and Kitchenettes", "Cleaning", "Audio and Visual Production", "Books/Videos/CDs",
    "Printing Costs", "Software Development for Publishing", "Material Costs", "Shipping for Production",
    "Digital Product Development", "Pre-production", "Post-production Costs", "Hardware",
    "IT Services", "Software", "Courier, Express, and Postal Services", "Warehousing and Material Handling",
    "Transportation Logistics", "Delivery Services", "Advertising", "Outdoor Advertising",
    "Marketing Agencies", "Direct Mail", "Customer Communication", "Online Marketing",
    "Events", "Promotional Materials", "Warehouse and Operational Equipment", "Production Machinery",
    "Spare Parts", "Internal Transportation", "Production Materials", "Consumables", "Maintenance and Repairs"
]

# --- Helper Logic ---

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def extract_text_from_pdf(file_bytes):
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
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
    Improved extraction using Few-Shot prompting, strict field mapping, 
    and official Commodity Group classification.
    """
    # Convert list to a string for the prompt
    group_list_str = ", ".join(COMMODITY_GROUPS)

    system_prompt = (
        "You are a professional procurement data extractor. Your goal is to parse vendor offers into a specific JSON format.\n\n"
        "STRICT RULES:\n"
        "1. Extract ONLY these fields: requestor_name, title, vendor_name, vat_id, total_cost, department, extracted_description_text, order_lines, commodity_group.\n"
        f"2. 'commodity_group' MUST be exactly one from this list: {group_list_str}.\n"
        "3. 'order_lines' must use EXACT keys: description, unit_price, amount, unit, total_price.\n"
        "4. Remove currency symbols (€, $) from numbers.\n"
        "5. Defaults: requestor_name='Vladimir Keil', department='Operations'.\n\n"
        "--- EXAMPLE ---\n"
        "Input: 'Apple Store Offer for 5 MacBooks for the IT Dept, Total 5000.'\n"
        "Output: {\n"
        '  "requestor_name": "Vladimir Keil", "title": "New Laptops", "vendor_name": "Apple Store", '
        '  "vat_id": "Unknown", "total_cost": 5000.0, "department": "IT Dept", "commodity_group": "Hardware", '
        '  "extracted_description_text": "5x MacBook Laptops", '
        '  "order_lines": [{"description": "MacBook", "unit_price": 1000.0, "amount": 5, "unit": "pcs", "total_price": 5000.0}]\n'
        "}\n"
        "--- END EXAMPLE ---\n\n"
        "Return ONLY the raw JSON object."
    )
    
    truncated_text = document_text[:12000]

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document Text:\n{truncated_text}"}
        ],
        temperature=0
    )
    
    content = response.choices[0].message.content.strip()
    if "```" in content:
        content = content.split("```")[1].replace("json", "").strip()

    try:
        # Validate with Pydantic
        return ProcurementData.model_validate_json(content).model_dump()
    except Exception as e:
        print(f"AI Validation Error: {e}")
        try:
            # Fallback manual cleanup
            raw_data = json.loads(content)
            if "items" in raw_data: raw_data["order_lines"] = raw_data.pop("items")
            return raw_data
        except:
            return {'requestor_name': 'Vladimir Keil', 'title': 'Error', 'vendor_name': 'Unknown', 'total_cost': 0.0, 'order_lines': []}

# --- Routes ---

@app.route('/')
def overview():
    conn = get_db_connection()
    requests_list = conn.execute("SELECT * FROM requests ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template('overview.html', requests=requests_list)

@app.route('/new_request', methods=['GET', 'POST'])
def new_request():
    # Using the official 50 groups for the dropdown
    all_groups = sorted(COMMODITY_GROUPS)
    
    data = {
        'requestor_name': 'Vladimir Keil', 'title': '', 'vendor_name': '',
        'vat_id': '', 'total_cost': 0.0, 'department': 'Operations',
        'order_lines': [], 'commodity_group': ''
    }

    if request.method == 'POST':
        if 'offer_file' in request.files and request.files['offer_file'].filename != '':
            file = request.files['offer_file']
            raw_bytes = file.read()
            clean_text = extract_text_from_pdf(raw_bytes)
            
            if clean_text:
                ai_data = extract_data_via_ai(clean_text)
                if ai_data:
                    data.update(ai_data)
            
            return render_template('new_request.html', data=data, all_groups=all_groups)

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
    new_status = request.json.get('status')
    user = request.json.get('user', 'Procurement Manager')
    conn = get_db_connection()
    conn.execute("UPDATE requests SET status = ? WHERE request_id = ?", (new_status, req_id))
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
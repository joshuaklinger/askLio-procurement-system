AI-Powered Procurement Intake System
An intelligent web application designed to streamline the procurement process. This system allows users to manually enter purchase requests or utilize AI-driven PDF scanning to automatically populate request data, classify commodity groups, and maintain a full audit trail.

🚀 Key Features
AI Document Scanning: Automatically extracts vendor names, VAT IDs, total costs, and detailed line items from PDF offers using GPT-4.

Intelligent Classification: Utilizes a Naive Bayes classifier (nb_classifier.joblib) to suggest commodity groups based on request titles.

Interactive Dashboard: A real-time overview of all procurement requests with status tracking (Open, In Progress, Approved, Rejected).

Audit Trail: Every status change is logged with a timestamp and the acting user to ensure compliance and transparency.

Structured Data Validation: Uses Pydantic to ensure all data extracted by AI follows strict procurement schemas.

🛠️ Tech Stack
Backend: Flask (Python)

AI/ML: OpenAI GPT-4 API, Scikit-learn (Naive Bayes)

Database: SQLite (SQLAlchemy-ready)

PDF Processing: PyPDF

Validation: Pydantic V2

📦 Project Structure
Plaintext

├── src/
│   ├── app.py                # Main Flask application logic
│   ├── extraction_schema.py   # Pydantic data models
│   ├── db_setup.py           # Database initialization & schema
│   ├── templates/            # HTML frontend (Jinja2)
│   ├── static/               # CSS & Frontend assets
│   ├── nb_classifier.joblib  # Trained Commodity Group model
│   └── tfidf_vectorizer.joblib # ML Vectorizer for text processing
├── .env.example              # Template for environment variables
├── .gitignore                # Git exclusion rules
├── requirements.txt          # Project dependencies
└── README.md                 # Project documentation
⚙️ Setup & Installation
1. Clone the Repository
Bash

git clone https://github.com/joshuaklinger/askLio-procurement-system.git
cd askLio-procurement-system
2. Set Up Virtual Environment
Bash

python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
3. Install Dependencies
Bash

pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory and add your OpenAI API Key:

Plaintext

OPENAI_API_KEY=your_sk_key_here
5. Initialize Database & Run
Bash

python src/app.py
The application will be available at http://127.0.0.1:5000.

🤖 How the AI Scanner Works
The system uses a multi-step extraction pipeline:

PDF Parsing: Clean text is extracted via pypdf, bypassing binary data to minimize token usage.

Context Management: Content is truncated and cleaned to fit within the GPT-4 8k context window.

Few-Shot Extraction: The AI is prompted with specific JSON examples to ensure it maps vendor "Quantity" to our "amount" field and "Unit Price" to "unit_price" accurately.

Pydantic Validation: The resulting JSON is validated against the ProcurementData schema before being displayed in the UI.

📝 License
This project is for demonstration purposes as part of a technical assessment.

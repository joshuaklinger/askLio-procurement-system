# AI-Powered Procurement Intake System

An intelligent web application designed to streamline the procurement process. This system allows users to manually enter purchase requests or utilize **AI-driven PDF scanning** to automatically populate request data, classify commodity groups, and maintain a full audit trail.



## 🚀 Key Features

* **AI Document Scanning**: Automatically extracts vendor names, VAT IDs, total costs, and detailed line items from PDF offers using GPT-4.
* **Intelligent Classification**: Utilizes a Naive Bayes classifier (`nb_classifier.joblib`) to suggest commodity groups based on request titles.
* **Interactive Dashboard**: A real-time overview of all procurement requests with status tracking (Open, In Progress, Approved, Rejected).
* **Audit Trail**: Every status change is logged with a timestamp and the acting user to ensure compliance and transparency.
* **Structured Data Validation**: Uses Pydantic to ensure all data extracted by AI follows strict procurement schemas.

## 🛠️ Tech Stack

* **Backend**: Flask (Python)
* **AI/ML**: OpenAI GPT-4 API, Scikit-learn (Naive Bayes)
* **Database**: SQLite (SQLAlchemy-ready)
* **PDF Processing**: PyPDF
* **Validation**: Pydantic V2

## 📦 Project Structure

```text
├── src/
│   ├── app.py                  # Main Flask application logic
│   ├── extraction_schema.py    # Pydantic data models
│   ├── db_setup.py             # Database initialization & schema
│   └── templates/              # HTML frontend (Jinja2)
├── .env.example                # Template for environment variables
├── .gitignore                  # Git exclusion rules
├── requirements.txt            # Project dependencies
└── README.md                   # Project documentation

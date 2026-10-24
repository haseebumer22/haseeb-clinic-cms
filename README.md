# 🏥 Doctor Clinic Management System (Haseeb Health Clinic)

A modern, cloud-backed Patient Registration & Appointment Management System built for single-counter clinic reception desks. Features permanent Medical Record (MR) tracking, sequential daily queue tokens, printable OPD slips (A5 & 80mm Thermal Receipt), and real-time medical histories.

- **Live Production URL**: [https://haseeb-clinic-cms.vercel.app](https://haseeb-clinic-cms.vercel.app)
- **Database Engine**: [Supabase PostgreSQL](https://supabase.com) (Mumbai `ap-south-1` Connection Pooler) with SQLite localhost fallback.
- **Hosting & Serverless**: [Vercel](https://vercel.com) (Zero-Config Python/Flask runtime).

---

## 🌟 Key Features

1. **Permanent MR Number Workflow**:
   - New patients are issued a unique, sequential Medical Record number (e.g. `MR-000001`).
   - Returning patients are looked up by Name, Phone, or MR number. Their original MR number is preserved, and a new visit record is appended to their history.
2. **Sequential Daily Token Queue**:
   - Daily queue tokens (`#01`, `#02`, etc.) reset each day to organize walk-in OPD consultations.
3. **High-Resolution Printable Slips**:
   - Dual format toggle: **Standard A5 Paper** and **80mm Thermal Receipt Printer**.
   - Includes simulated barcode, clinic header, patient details, consulting doctor, and consultation fee status.
4. **Patient Directory & Full Medical History**:
   - Real-time search across patients by MR number, phone, or name.
   - Interactive history modal showing past consultation dates, symptoms, consulting doctors, and fees.
5. **Doctor & Fee Management**:
   - Manage clinic roster, room numbers, consultation fees, and doctor availability.
6. **Dual Database Architecture**:
   - Automatically connects to **Supabase PostgreSQL** via `DATABASE_URL` in production or `.env`.
   - Automatically falls back to **SQLite** (`clinic.db`) for offline/standalone local clinic use.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.15, Flask 3.1
- **ORM / Database**: SQLAlchemy 2.1, Supabase PostgreSQL, SQLite
- **Drivers & SDKs**: `psycopg2-binary`, `python-dotenv`, `supabase`
- **Frontend**: HTML5, CSS3, Bootstrap 5.3, Bootstrap Icons, Google Fonts (Plus Jakarta Sans, JetBrains Mono)
- **Deployment**: Vercel Serverless Functions, GitHub

---

## 🚀 Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/haseebumer22/haseeb-clinic-cms.git
cd haseeb-clinic-cms
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Database (.env)
Create or edit `.env` in the root folder:
```env
# Optional: To connect to Supabase PostgreSQL (leave blank to use local SQLite)
DATABASE_URL=postgresql://postgres.yslxkrcmkowvpqaukhtx:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### 4. Run the application
```bash
# Option A: Python command
python app.py

# Option B: Double-click run.bat (Windows)
```

Open your browser at **http://127.0.0.1:5000**.

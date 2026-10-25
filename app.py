import os
import io
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort, send_file
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from models import db, Patient, Visit, Doctor
from dotenv import load_dotenv

# Load local environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "haseeb-clinic-secret-key-2026-very-secure"

# Database Configuration (Supabase PostgreSQL or fallback SQLite)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
elif os.environ.get("VERCEL"):
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////tmp/clinic.db"
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///clinic.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

DEFAULT_DOCTORS = [
    {"name": "Dr. Ahmed Khan", "specialty": "General Physician / Consultant", "fee": 800.0, "room_number": "Room 101"},
    {"name": "Dr. Sara Malik", "specialty": "Pediatrician / Child Specialist", "fee": 1000.0, "room_number": "Room 102"},
    {"name": "Dr. Ali Raza", "specialty": "Cardiologist", "fee": 1500.0, "room_number": "Room 103"},
    {"name": "Dr. Fatima Noor", "specialty": "Gynecologist & Obstetrician", "fee": 1200.0, "room_number": "Room 104"}
]

def init_database():
    """Create database tables and insert initial default doctors if empty."""
    with app.app_context():
        db.create_all()
        if Doctor.query.count() == 0:
            for doc in DEFAULT_DOCTORS:
                db.session.add(Doctor(
                    name=doc["name"],
                    specialty=doc["specialty"],
                    fee=doc["fee"],
                    room_number=doc["room_number"],
                    is_active=True
                ))
            db.session.commit()

init_database()

def calculate_next_token(doctor_name=None):
    """Calculate the sequential OPD token number for a specific doctor today."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    query = Visit.query.filter(Visit.visit_datetime >= today_start)
    if doctor_name:
        query = query.filter(Visit.doctor_name == doctor_name)
    return query.count() + 1

@app.route("/")
def index():
    doctors = Doctor.query.filter_by(is_active=True).all()
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    total_patients = Patient.query.count()
    today_visits = Visit.query.filter(Visit.visit_datetime >= today_start).count()
    active_doctors = len(doctors)
    
    recent_visits = Visit.query.order_by(Visit.id.desc()).limit(6).all()
    doctor_tokens = {doc.name: calculate_next_token(doc.name) for doc in doctors}
    default_next_token = doctor_tokens[doctors[0].name] if doctors else 1

    return render_template(
        "index.html",
        doctors=doctors,
        total_patients=total_patients,
        today_visits=today_visits,
        active_doctors=active_doctors,
        recent_visits=recent_visits,
        doctor_tokens=doctor_tokens,
        next_token=default_next_token
    )

@app.route("/register", methods=["POST"])
def register():
    """Register a new patient and create their first visit record."""
    name = request.form.get("patient_name", "").strip()
    phone = request.form.get("phone_number", "").strip()
    gender = request.form.get("gender", "Male").strip()
    blood_group = request.form.get("blood_group", "N/A").strip()
    address = request.form.get("address", "").strip()
    doctor_name = request.form.get("doctor", "").strip()
    symptoms = request.form.get("symptoms", "General Consultation").strip()
    
    age_text = request.form.get("age", "").strip()
    try:
        age = int(age_text)
    except ValueError:
        flash("Invalid age entered. Please enter a valid number.", "danger")
        return redirect(url_for("index"))

    if not name or not phone or not (1 <= age <= 125):
        flash("Please provide a valid patient name, contact number, and age.", "danger")
        return redirect(url_for("index"))

    doctor = Doctor.query.filter_by(name=doctor_name, is_active=True).first()
    if not doctor:
        flash("Selected doctor is not recognized or is inactive.", "danger")
        return redirect(url_for("index"))

    try:
        # Step 1: Create Patient with placeholder MR number to obtain unique ID
        patient = Patient(
            mr_number="PENDING",
            patient_name=name,
            age=age,
            gender=gender,
            phone_number=phone,
            address=address,
            blood_group=blood_group,
            created_at=datetime.now()
        )
        db.session.add(patient)
        db.session.flush()

        # Step 2: Set permanent unique formatted MR Number
        patient.mr_number = f"MR-{patient.id:06d}"

        # Step 3: Create initial visit with doctor-specific OPD number
        token_num = calculate_next_token(doctor.name)
        visit = Visit(
            patient_id=patient.id,
            token_number=token_num,
            doctor_name=doctor.name,
            department=doctor.specialty,
            symptoms=symptoms if symptoms else "General Consultation",
            fee=doctor.fee,
            status="Waiting",
            visit_datetime=datetime.now()
        )
        db.session.add(visit)
        db.session.commit()

        flash(f"Patient {patient.patient_name} registered successfully with MR: {patient.mr_number} (Dr. {doctor.name} OPD #{token_num})", "success")
        return redirect(url_for("print_slip", visit_id=visit.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error during registration: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/new-visit", methods=["POST"])
def new_visit():
    """Create a new visit for an existing patient (Permanent MR)."""
    patient_id = request.form.get("patient_id")
    doctor_name = request.form.get("doctor", "").strip()
    symptoms = request.form.get("symptoms", "Follow-up / Re-visit").strip()

    patient = db.session.get(Patient, patient_id)
    if not patient:
        flash("Patient not found. Please register as a new patient.", "danger")
        return redirect(url_for("index"))

    doctor = Doctor.query.filter_by(name=doctor_name, is_active=True).first()
    if not doctor:
        flash("Please select a valid doctor.", "danger")
        return redirect(url_for("index"))

    try:
        # Create visit with doctor-specific OPD number
        token_num = calculate_next_token(doctor.name)
        visit = Visit(
            patient_id=patient.id,
            token_number=token_num,
            doctor_name=doctor.name,
            department=doctor.specialty,
            symptoms=symptoms if symptoms else "Follow-up Checkup",
            fee=doctor.fee,
            status="Waiting",
            visit_datetime=datetime.now()
        )
        db.session.add(visit)
        db.session.commit()

        flash(f"New visit booked for {patient.patient_name} (MR: {patient.mr_number}) — {doctor.name} OPD #{token_num}!", "success")
        return redirect(url_for("print_slip", visit_id=visit.id))
    except Exception as e:
        db.session.rollback()
        flash(f"Error booking visit: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/patients")
def patients():
    """Display all registered patients with search filtering."""
    query = request.args.get("q", "").strip()
    if query:
        search_pattern = f"%{query}%"
        patient_list = Patient.query.filter(
            (Patient.patient_name.ilike(search_pattern)) |
            (Patient.mr_number.ilike(search_pattern)) |
            (Patient.phone_number.ilike(search_pattern))
        ).order_by(Patient.id.desc()).all()
    else:
        patient_list = Patient.query.order_by(Patient.id.desc()).all()

    doctors = Doctor.query.filter_by(is_active=True).all()
    doctor_tokens = {doc.name: calculate_next_token(doc.name) for doc in doctors}
    return render_template("patients.html", patients=patient_list, query=query, doctors=doctors, doctor_tokens=doctor_tokens)

@app.route("/patients/export")
def export_patients():
    """Export all registered patients to an Excel (.xlsx) file with professional formatting."""
    patients = Patient.query.order_by(Patient.id.asc()).all()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Patients Directory"
    ws.views.sheetView[0].showGridLines = True

    # Header styling (professional medical blue)
    header_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    data_font = Font(name="Calibri", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0")
    )
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

    headers = [
        "MR Number",
        "Patient Name",
        "Age",
        "Gender",
        "Phone Number",
        "Blood Group",
        "Address",
        "Registration Date",
        "Total Visits",
        "Last Doctor Visited",
        "Last Visit Date"
    ]

    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = thin_border

    for row_idx, p in enumerate(patients, start=2):
        visits_count = len(p.visits)
        last_doc = p.visits[0].doctor_name if p.visits else "None"
        last_visit_date = p.visits[0].visit_datetime.strftime("%Y-%m-%d %I:%M %p") if p.visits else "None"
        reg_date = p.created_at.strftime("%Y-%m-%d %I:%M %p") if p.created_at else ""

        row_data = [
            p.mr_number,
            p.patient_name,
            p.age,
            p.gender,
            p.phone_number,
            p.blood_group or "N/A",
            p.address or "",
            reg_date,
            visits_count,
            last_doc,
            last_visit_date
        ]
        ws.append(row_data)
        ws.row_dimensions[row_idx].height = 20

        is_even = (row_idx % 2 == 0)
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = thin_border
            if is_even:
                cell.fill = zebra_fill

            if col_idx in [1, 3, 4, 5, 6, 8, 9, 11]:
                cell.alignment = center_align
            else:
                cell.alignment = left_align

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"patients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(
        output,
        download_name=filename,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/patients/template")
def download_patient_template():
    """Download a formatted sample Excel (.xlsx) template for bulk patient imports."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Patient Import Template"
    ws.views.sheetView[0].showGridLines = True

    header_fill = PatternFill(start_color="0D9488", end_color="0D9488", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    data_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1")
    )

    headers = ["Patient Name", "Age", "Gender", "Phone Number", "Blood Group", "Address"]
    ws.append(headers)
    ws.row_dimensions[1].height = 26

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_align
        cell.border = thin_border

    sample_data = [
        ["Muhammad Usman", 34, "Male", "03001234567", "B+", "House 12, Street 4, Lahore"],
        ["Ayesha Bibi", 28, "Female", "03219876543", "O+", "Gulberg III, Lahore"],
        ["Tariq Mehmood", 45, "Male", "03335557788", "A+", "DHA Phase 5, Lahore"]
    ]

    for row_idx, row_values in enumerate(sample_data, start=2):
        ws.append(row_values)
        ws.row_dimensions[row_idx].height = 20
        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = data_font
            cell.border = thin_border
            if col_idx in [2, 3, 4, 5]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            else:
                cell.alignment = Alignment(horizontal="left", vertical="center")

    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 15)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        download_name="patient_import_template.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

@app.route("/patients/import", methods=["POST"])
def import_patients():
    """Import patients from an uploaded Excel (.xlsx/.xls) file."""
    if "file" not in request.files:
        flash("No file was selected for upload.", "danger")
        return redirect(url_for("patients"))

    file = request.files["file"]
    if not file or file.filename == "":
        flash("Please select an Excel file (.xlsx) to import.", "danger")
        return redirect(url_for("patients"))

    if not (file.filename.lower().endswith(".xlsx") or file.filename.lower().endswith(".xls")):
        flash("Invalid file format. Please upload an Excel (.xlsx or .xls) file.", "danger")
        return redirect(url_for("patients"))

    try:
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb.active

        # Identify header row and map columns
        header_map = {}
        header_row_idx = None

        for r in range(1, min(10, ws.max_row + 1)):
            row_vals = [str(ws.cell(row=r, column=c).value or "").strip().lower() for c in range(1, ws.max_column + 1)]
            for col_idx, val in enumerate(row_vals, start=1):
                if any(k in val for k in ["patient name", "patient_name", "full name", "name"]):
                    if "name" not in header_map:
                        header_map["name"] = col_idx
                elif "age" in val:
                    header_map["age"] = col_idx
                elif any(k in val for k in ["gender", "sex"]):
                    header_map["gender"] = col_idx
                elif any(k in val for k in ["phone", "mobile", "contact", "cell"]):
                    header_map["phone"] = col_idx
                elif any(k in val for k in ["blood", "blood_group", "blood group"]):
                    header_map["blood_group"] = col_idx
                elif any(k in val for k in ["address", "city", "location"]):
                    header_map["address"] = col_idx

            if "name" in header_map and "phone" in header_map:
                header_row_idx = r
                break

        if not header_row_idx:
            # Fallback to standard columns: 1: Name, 2: Age, 3: Gender, 4: Phone, 5: Blood, 6: Address
            header_row_idx = 1
            header_map = {
                "name": 1,
                "age": 2,
                "gender": 3,
                "phone": 4,
                "blood_group": 5,
                "address": 6
            }

        imported_count = 0
        skipped_count = 0

        for row_idx in range(header_row_idx + 1, ws.max_row + 1):
            name_val = ws.cell(row=row_idx, column=header_map.get("name", 1)).value
            if not name_val:
                continue

            name = str(name_val).strip()
            if not name:
                continue

            phone_col = header_map.get("phone", 4)
            phone_val = ws.cell(row=row_idx, column=phone_col).value
            if phone_val is None:
                skipped_count += 1
                continue

            phone = str(phone_val).strip()
            if phone.endswith(".0"):
                phone = phone[:-2]

            if not phone:
                skipped_count += 1
                continue

            age_col = header_map.get("age", 2)
            age_val = ws.cell(row=row_idx, column=age_col).value
            try:
                age = int(float(age_val)) if age_val is not None else 30
                if age < 1 or age > 125:
                    age = 30
            except (ValueError, TypeError):
                age = 30

            gender_col = header_map.get("gender", 3)
            gender_val = str(ws.cell(row=row_idx, column=gender_col).value or "Male").strip()
            if gender_val.lower().startswith("f"):
                gender = "Female"
            elif gender_val.lower().startswith("o"):
                gender = "Other"
            else:
                gender = "Male"

            bg_col = header_map.get("blood_group", 5)
            blood_val = str(ws.cell(row=row_idx, column=bg_col).value or "N/A").strip()
            blood_group = blood_val if blood_val and blood_val.lower() != "none" else "N/A"

            addr_col = header_map.get("address", 6)
            addr_val = str(ws.cell(row=row_idx, column=addr_col).value or "").strip()
            address = addr_val if addr_val.lower() != "none" else ""

            # Check if patient already exists by phone number
            existing = Patient.query.filter_by(phone_number=phone).first()
            if existing:
                skipped_count += 1
                continue

            patient = Patient(
                mr_number="PENDING",
                patient_name=name,
                age=age,
                gender=gender,
                phone_number=phone,
                address=address,
                blood_group=blood_group,
                created_at=datetime.now()
            )
            db.session.add(patient)
            db.session.flush()
            patient.mr_number = f"MR-{patient.id:06d}"
            imported_count += 1

        db.session.commit()

        if imported_count > 0:
            msg = f"Successfully imported {imported_count} new patient(s)!"
            if skipped_count > 0:
                msg += f" ({skipped_count} row(s) skipped due to duplicate phone or missing fields)."
            flash(msg, "success")
        elif skipped_count > 0:
            flash(f"No new patients imported. {skipped_count} row(s) were skipped (already registered with same phone number).", "warning")
        else:
            flash("No valid patient records found in the uploaded Excel sheet.", "info")

    except Exception as e:
        db.session.rollback()
        flash(f"Error importing Excel file: {str(e)}", "danger")

    return redirect(url_for("patients"))

@app.route("/api/doctor_token")
def doctor_token_api():
    """API endpoint to get real-time next OPD number for any doctor."""
    doc_name = request.args.get("doctor", "").strip()
    return jsonify({
        "doctor": doc_name,
        "next_token": calculate_next_token(doc_name if doc_name else None)
    })

@app.route("/visits")
def visits():
    """Display today's visits queue or filter by date / doctor."""
    selected_doctor = request.args.get("doctor", "").strip()
    date_filter = request.args.get("date", "").strip()

    if date_filter:
        try:
            target_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today()
    else:
        target_date = date.today()

    start_of_day = datetime.combine(target_date, datetime.min.time())
    end_of_day = datetime.combine(target_date, datetime.max.time())

    visits_query = Visit.query.filter(
        Visit.visit_datetime >= start_of_day,
        Visit.visit_datetime <= end_of_day
    )

    if selected_doctor:
        visits_query = visits_query.filter(Visit.doctor_name == selected_doctor)

    visit_list = visits_query.order_by(Visit.token_number.asc()).all()
    doctors = Doctor.query.filter_by(is_active=True).all()

    return render_template(
        "visits.html",
        visits=visit_list,
        doctors=doctors,
        selected_doctor=selected_doctor,
        selected_date=target_date.strftime("%Y-%m-%d")
    )

@app.route("/visits/update-status/<int:visit_id>", methods=["POST"])
def update_visit_status(visit_id):
    """Quick update of visit queue status (Waiting, In Consultation, Completed, Cancelled)."""
    new_status = request.form.get("status")
    visit = db.session.get(Visit, visit_id)
    if visit and new_status in ["Waiting", "In Consultation", "Completed", "Cancelled"]:
        visit.status = new_status
        db.session.commit()
        flash(f"Visit #{visit.token_number} status updated to '{new_status}'", "info")
    return redirect(request.referrer or url_for("visits"))

@app.route("/print/<int:visit_id>")
def print_slip(visit_id):
    """Render high-resolution printable patient registration slip."""
    visit = db.get_or_404(Visit, visit_id)
    patient = db.get_or_404(Patient, visit.patient_id)
    auto_print = request.args.get("auto", "1") == "1"
    return render_template("print_slip.html", visit=visit, patient=patient, auto_print=auto_print)

@app.route("/doctors", methods=["GET", "POST"])
def doctors():
    """View and manage clinic doctors, specialties, and fees."""
    if request.method == "POST":
        doc_name = request.form.get("name", "").strip()
        doc_specialty = request.form.get("specialty", "").strip()
        doc_room = request.form.get("room_number", "").strip()
        try:
            doc_fee = float(request.form.get("fee", 500.0))
        except ValueError:
            doc_fee = 500.0

        if doc_name:
            new_doc = Doctor(
                name=doc_name,
                specialty=doc_specialty or "General Physician",
                room_number=doc_room or "Room 101",
                fee=doc_fee,
                is_active=True
            )
            db.session.add(new_doc)
            db.session.commit()
            flash(f"Doctor '{doc_name}' added successfully!", "success")
            return redirect(url_for("doctors"))

    all_doctors = Doctor.query.order_by(Doctor.id.asc()).all()
    return render_template("doctors.html", doctors=all_doctors)

@app.route("/doctors/toggle/<int:doctor_id>", methods=["POST"])
def toggle_doctor(doctor_id):
    doc = db.session.get(Doctor, doctor_id)
    if doc:
        doc.is_active = not doc.is_active
        db.session.commit()
        state = "activated" if doc.is_active else "deactivated"
        flash(f"{doc.name} {state}.", "info")
    return redirect(url_for("doctors"))

@app.route("/api/search_patient")
def search_patient_api():
    """Live search API for receptionist lookup by MR number, phone, or name."""
    query = request.args.get("q", "").strip()
    if not query or len(query) < 2:
        return jsonify([])

    pattern = f"%{query}%"
    patients = Patient.query.filter(
        (Patient.mr_number.ilike(pattern)) |
        (Patient.phone_number.ilike(pattern)) |
        (Patient.patient_name.ilike(pattern))
    ).limit(8).all()

    results = []
    for p in patients:
        results.append({
            "id": p.id,
            "mr_number": p.mr_number,
            "name": p.patient_name,
            "age": p.age,
            "gender": p.gender,
            "phone": p.phone_number,
            "blood_group": p.blood_group,
            "visits_count": len(p.visits),
            "last_visit": p.visits[0].visit_datetime.strftime("%d-%b-%Y %I:%M %p") if p.visits else "None"
        })
    return jsonify(results)

if __name__ == "__main__":
    init_database()
    app.run(debug=True, port=5000)

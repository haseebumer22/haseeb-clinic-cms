import os
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from models import db, Patient, Visit, Doctor

app = Flask(__name__)
app.config["SECRET_KEY"] = "haseeb-clinic-secret-key-2026-very-secure"
if os.environ.get("VERCEL"):
    db_path = "/tmp/clinic.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", f"sqlite:///{db_path}")
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///clinic.db")
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

def calculate_next_token():
    """Calculate the sequential token number for today's visits."""
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_count = Visit.query.filter(Visit.visit_datetime >= today_start).count()
    return today_count + 1

@app.route("/")
def index():
    doctors = Doctor.query.filter_by(is_active=True).all()
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    total_patients = Patient.query.count()
    today_visits = Visit.query.filter(Visit.visit_datetime >= today_start).count()
    active_doctors = len(doctors)
    
    recent_visits = Visit.query.order_by(Visit.id.desc()).limit(6).all()
    next_token = calculate_next_token()

    return render_template(
        "index.html",
        doctors=doctors,
        total_patients=total_patients,
        today_visits=today_visits,
        active_doctors=active_doctors,
        recent_visits=recent_visits,
        next_token=next_token
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

        # Step 3: Create initial visit
        token_num = calculate_next_token()
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

        flash(f"Patient {patient.patient_name} registered successfully with MR: {patient.mr_number}", "success")
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
        token_num = calculate_next_token()
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

        flash(f"New visit booked for {patient.patient_name} (MR: {patient.mr_number})!", "success")
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
    return render_template("patients.html", patients=patient_list, query=query, doctors=doctors)

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

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)
    mr_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    patient_name = db.Column(db.String(150), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), default="Male", nullable=False)
    phone_number = db.Column(db.String(30), nullable=False, index=True)
    address = db.Column(db.String(255), default="")
    blood_group = db.Column(db.String(10), default="N/A")
    created_at = db.Column(db.DateTime, default=datetime.now, nullable=False)

    # Family member relation tracking for shared phone numbers
    primary_patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=True)
    relation_to_primary = db.Column(db.String(100), default="", nullable=True)

    visits = db.relationship("Visit", backref="patient", cascade="all, delete-orphan", lazy=True, order_by="desc(Visit.visit_datetime)")
    family_members = db.relationship(
        "Patient",
        backref=db.backref("primary_patient", remote_side=[id]),
        lazy=True,
        foreign_keys=[primary_patient_id]
    )

    def __repr__(self):
        return f"<Patient {self.mr_number} - {self.patient_name}>"


class Visit(db.Model):
    __tablename__ = "visits"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    token_number = db.Column(db.Integer, nullable=False, default=1)
    doctor_name = db.Column(db.String(150), nullable=False)
    department = db.Column(db.String(100), default="General Medicine")
    symptoms = db.Column(db.String(255), default="General Checkup")
    fee = db.Column(db.Float, default=500.0)
    status = db.Column(db.String(30), default="Waiting")  # Waiting, In Consultation, Completed, Cancelled
    visit_datetime = db.Column(db.DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<Visit {self.id} - Patient {self.patient_id} - Token {self.token_number}>"


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    specialty = db.Column(db.String(100), default="General Physician")
    fee = db.Column(db.Float, default=500.0)
    room_number = db.Column(db.String(20), default="Room 1")
    is_active = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"<Doctor {self.name} - {self.specialty}>"


class ClinicSetting(db.Model):
    __tablename__ = "clinic_settings"

    id = db.Column(db.Integer, primary_key=True)
    clinic_name = db.Column(db.String(200), default="HASEEB HEALTH CLINIC", nullable=False)
    tagline = db.Column(db.String(255), default="Reception Counter & Patient Registry")
    phone = db.Column(db.String(100), default="(042) 3500-1122")
    address = db.Column(db.String(255), default="Walk-In OPD • Reception Counter")
    slip_footer = db.Column(db.String(255), default="Please take a seat in the waiting area. Your token number will be called shortly.")
    logo_path = db.Column(db.Text, nullable=True, default="")
    master_pin = db.Column(db.String(100), default="1234")
    pin_required = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f"<ClinicSetting {self.clinic_name}>"


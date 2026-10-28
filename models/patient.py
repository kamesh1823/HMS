from extensions import db
from datetime import datetime
import hashlib

class Patient(db.Model):
    __tablename__ = 'patients'
    id            = db.Column(db.Integer, primary_key=True)
    patient_id    = db.Column(db.String(20), unique=True, nullable=False)
    full_name     = db.Column(db.String(120), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender        = db.Column(db.String(10))
    blood_group   = db.Column(db.String(5))
    phone         = db.Column(db.String(20))
    email         = db.Column(db.String(120))
    address       = db.Column(db.Text)
    emergency_contact_name  = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    allergies          = db.Column(db.Text)
    chronic_conditions = db.Column(db.Text)
    hospital_id   = db.Column(db.String(20), default='HOSP_001')
    registered_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    visits        = db.relationship('Visit', backref='patient', lazy=True)
    scans         = db.relationship('Scan', backref='patient', lazy=True)

    def generate_encryption_key_seed(self):
        raw = f"{self.patient_id}{self.date_of_birth}{self.hospital_id}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def __repr__(self):
        return f'<Patient {self.patient_id} - {self.full_name}>'


class Visit(db.Model):
    __tablename__ = 'visits'
    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    doctor_id  = db.Column(db.Integer, db.ForeignKey('users.id'))
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    reason     = db.Column(db.Text)
    diagnosis  = db.Column(db.Text)
    notes      = db.Column(db.Text)
    status     = db.Column(db.String(20), default='active')
    prescriptions = db.relationship('Prescription', backref='visit', lazy=True)
    lab_reports   = db.relationship('LabReport', backref='visit', lazy=True)


class Prescription(db.Model):
    __tablename__ = 'prescriptions'
    id         = db.Column(db.Integer, primary_key=True)
    visit_id   = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=False)
    medicine   = db.Column(db.String(200), nullable=False)
    dosage     = db.Column(db.String(100))
    frequency  = db.Column(db.String(100))
    duration   = db.Column(db.String(100))
    notes      = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class LabReport(db.Model):
    __tablename__ = 'lab_reports'
    id          = db.Column(db.Integer, primary_key=True)
    patient_id  = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    visit_id    = db.Column(db.Integer, db.ForeignKey('visits.id'), nullable=True)
    report_name = db.Column(db.String(200))
    report_type = db.Column(db.String(100), default='General')  # Blood, Urine, X-Ray, etc.
    file_path   = db.Column(db.String(300))
    notes       = db.Column(db.Text)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class Scan(db.Model):
    __tablename__ = 'scans'
    id             = db.Column(db.Integer, primary_key=True)
    patient_id     = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    visit_id       = db.Column(db.Integer, db.ForeignKey('visits.id'))
    scan_type      = db.Column(db.String(50))
    body_part      = db.Column(db.String(100))
    original_path  = db.Column(db.String(300))
    encrypted_path = db.Column(db.String(300))
    uploaded_by    = db.Column(db.Integer, db.ForeignKey('users.id'))
    uploaded_at    = db.Column(db.DateTime, default=datetime.utcnow)
    notes          = db.Column(db.Text)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id               = db.Column(db.Integer, primary_key=True)
    patient_type     = db.Column(db.String(10))
    patient_name     = db.Column(db.String(120))
    phone            = db.Column(db.String(20))
    email            = db.Column(db.String(120))
    date_of_birth    = db.Column(db.String(20))
    patient_id_ref   = db.Column(db.String(20))
    preferred_doctor = db.Column(db.String(120))
    assigned_doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    appointment_date = db.Column(db.String(30))
    reason           = db.Column(db.Text)
    status           = db.Column(db.String(20), default='pending')
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'))
    action     = db.Column(db.String(200))
    target     = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow)

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.patient import Patient, Visit, Prescription, LabReport, Scan, AuditLog, Appointment
from models.user import User
from extensions import db
from datetime import datetime, date as date_type
from functools import wraps
import re

patients_bp = Blueprint('patients', __name__)

# ── Access control decorators ──────────────────────────────────────
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator

def log_action(action, target):
    try:
        entry = AuditLog(
            user_id   = current_user.id,
            action    = action,
            target    = target,
            ip_address= request.remote_addr,
        )
        db.session.add(entry)
        db.session.commit()
    except Exception:
        pass

def generate_patient_id():
    """Generate unique patient ID: MV-YYYY-XXXX"""
    year  = datetime.now().year
    count = Patient.query.count() + 1
    return f"MV-{year}-{count:04d}"

# ── PATIENT LIST ────────────────────────────────────────────────────
@patients_bp.route('/patients')
@login_required
def list_patients():
    # Patients can only see their own portal
    if current_user.role == 'patient':
        return redirect(url_for('patients.my_records'))
    search = request.args.get('q', '').strip()
    page   = request.args.get('page', 1, type=int)
    query  = Patient.query

    if search:
        query = query.filter(
            db.or_(
                Patient.full_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%'),
                Patient.phone.ilike(f'%{search}%'),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    new_today = Patient.query.filter(
        db.func.date(Patient.created_at) == date_type.today()
    ).count()
    return render_template('patients/list.html', patients=patients, search=search, new_today=new_today)

# ── NEW PATIENT REGISTRATION ────────────────────────────────────────
@patients_bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def new_patient():
    if request.method == 'POST':
        dob_str = request.form.get('date_of_birth')
        try:
            dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            flash('Invalid date of birth format.', 'danger')
            return render_template('patients/new.html',
                now=datetime.now(), total_patients=Patient.query.count())

        patient = Patient(
            patient_id             = generate_patient_id(),
            full_name              = request.form.get('full_name').strip(),
            date_of_birth          = dob,
            gender                 = request.form.get('gender'),
            blood_group            = request.form.get('blood_group'),
            phone                  = request.form.get('phone').strip(),
            email                  = request.form.get('email', '').strip(),
            address                = request.form.get('address', '').strip(),
            emergency_contact_name = request.form.get('emergency_contact_name', '').strip(),
            emergency_contact_phone= request.form.get('emergency_contact_phone', '').strip(),
            allergies              = request.form.get('allergies', '').strip(),
            chronic_conditions     = request.form.get('chronic_conditions', '').strip(),
            registered_by          = current_user.id,
        )
        db.session.add(patient)
        db.session.commit()

        log_action(f'Registered new patient', f'{patient.patient_id} — {patient.full_name}')
        flash(f'Patient {patient.full_name} registered successfully! ID: {patient.patient_id}', 'success')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    return render_template('patients/new.html',
        now=datetime.now(), total_patients=Patient.query.count())

# ── VIEW PATIENT PROFILE + FULL HISTORY ────────────────────────────
@patients_bp.route('/patients/<int:patient_id>')
@login_required
def view_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    # Block receptionist from seeing medical details
    if current_user.role == 'receptionist':
        return render_template('patients/profile_reception.html', patient=patient)

    visits = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.visit_date.desc()).all()
    scans  = Scan.query.filter_by(patient_id=patient.id).order_by(Scan.uploaded_at.desc()).all()

    log_action('Viewed patient profile', f'{patient.patient_id} — {patient.full_name}')
    lab_reports = LabReport.query.filter_by(patient_id=patient.id).order_by(LabReport.uploaded_at.desc()).all()
    return render_template(
        'patients/profile.html',
        patient     = patient,
        visits      = visits,
        scans       = scans,
        doctors     = User.query.filter_by(role='doctor', is_active=True).all(),
        lab_reports = lab_reports,
    )

# ── EDIT PATIENT ───────────────────────────────────────────────────
@patients_bp.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        patient.full_name               = request.form.get('full_name', patient.full_name).strip()
        patient.phone                   = request.form.get('phone', patient.phone).strip()
        patient.email                   = request.form.get('email', patient.email).strip()
        patient.address                 = request.form.get('address', patient.address).strip()
        patient.blood_group             = request.form.get('blood_group', patient.blood_group)
        patient.gender                  = request.form.get('gender', patient.gender)
        patient.emergency_contact_name  = request.form.get('emergency_contact_name', '').strip()
        patient.emergency_contact_phone = request.form.get('emergency_contact_phone', '').strip()
        patient.allergies               = request.form.get('allergies', '').strip()
        patient.chronic_conditions      = request.form.get('chronic_conditions', '').strip()

        db.session.commit()
        log_action('Edited patient profile', f'{patient.patient_id} — {patient.full_name}')
        flash('Patient information updated successfully.', 'success')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    return render_template('patients/edit.html', patient=patient)

# ── NEW VISIT ──────────────────────────────────────────────────────
@patients_bp.route('/patients/<int:patient_id>/visit/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'doctor')
def new_visit(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == 'POST':
        visit = Visit(
            patient_id = patient.id,
            doctor_id  = current_user.id,
            reason     = request.form.get('reason', '').strip(),
            diagnosis  = request.form.get('diagnosis', '').strip(),
            notes      = request.form.get('notes', '').strip(),
            status     = request.form.get('status', 'active'),
        )
        db.session.add(visit)
        db.session.commit()
        log_action('Created visit record', f'Patient: {patient.patient_id}')
        flash('Visit record created successfully.', 'success')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    return render_template('patients/new_visit.html', patient=patient)

# ── ADD PRESCRIPTION ───────────────────────────────────────────────
@patients_bp.route('/visits/<int:visit_id>/prescription/new', methods=['POST'])
@login_required
@roles_required('admin', 'doctor')
def add_prescription(visit_id):
    visit = Visit.query.get_or_404(visit_id)
    rx = Prescription(
        visit_id  = visit.id,
        medicine  = request.form.get('medicine', '').strip(),
        dosage    = request.form.get('dosage', '').strip(),
        frequency = request.form.get('frequency', '').strip(),
        duration  = request.form.get('duration', '').strip(),
        notes     = request.form.get('rx_notes', '').strip(),
    )
    db.session.add(rx)
    db.session.commit()
    flash('Prescription added.', 'success')
    return redirect(url_for('patients.view_patient', patient_id=visit.patient_id))

# ── SEARCH API (for AJAX) ──────────────────────────────────────────
@patients_bp.route('/patients/search')
@login_required
def search_patients():
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify([])
    results = Patient.query.filter(
        db.or_(
            Patient.full_name.ilike(f'%{q}%'),
            Patient.patient_id.ilike(f'%{q}%'),
        )
    ).limit(8).all()
    return jsonify([{
        'id': p.id, 'patient_id': p.patient_id,
        'full_name': p.full_name, 'dob': str(p.date_of_birth),
        'phone': p.phone,
    } for p in results])

# ── PATIENT PORTAL (read-only self-view) ────────────────────────────
@patients_bp.route('/my-records')
@login_required
def my_records():
    """Patient self-service portal — read-only view of own data."""
    if current_user.role != 'patient':
        flash('This portal is for patients only.', 'danger')
        return redirect(url_for('dashboard.index'))

    # Find linked patient record by email match
    patient = Patient.query.filter_by(email=current_user.email).first()
    if not patient:
        return render_template('patients/portal_no_record.html')

    visits      = Visit.query.filter_by(patient_id=patient.id).order_by(Visit.visit_date.desc()).all()
    lab_reports = LabReport.query.filter_by(patient_id=patient.id).order_by(LabReport.uploaded_at.desc()).all()
    # Match appointments by phone or patient_id_ref
    appointments = Appointment.query.filter(
        db.or_(
            Appointment.phone == patient.phone,
            Appointment.patient_id_ref == patient.patient_id,
            Appointment.email == patient.email,
        )
    ).order_by(Appointment.appointment_date.desc()).all()

    return render_template(
        'patients/portal.html',
        patient      = patient,
        visits       = visits,
        lab_reports  = lab_reports,
        appointments = appointments,
    )

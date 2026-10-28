"""
routes/reception.py
Receptionist & Admin: Patient Check-in, Billing, Book Appointment
"""
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, jsonify)
from flask_login import login_required, current_user
from models.patient import Patient, Visit, Appointment, AuditLog
from models.user import User
from extensions import db
from datetime import datetime, date
from functools import wraps

reception_bp = Blueprint('reception', __name__)


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def log_action(action, target):
    try:
        entry = AuditLog(user_id=current_user.id, action=action,
                         target=target, ip_address=request.remote_addr)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        pass


# ── Patient Check-in ───────────────────────────────────────────────
@reception_bp.route('/checkin', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def checkin():
    patients = Patient.query.order_by(Patient.full_name).all()
    doctors  = User.query.filter_by(role='doctor', is_active=True).all()
    today_visits = (Visit.query
                    .filter(db.func.date(Visit.visit_date) == date.today())
                    .order_by(Visit.visit_date.desc())
                    .all())

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        doctor_id  = request.form.get('doctor_id') or None
        reason     = request.form.get('reason', '').strip()

        if not patient_id:
            flash('Please select a patient.', 'danger')
            return render_template('reception/checkin.html',
                                   patients=patients, doctors=doctors,
                                   today_visits=today_visits)

        patient = Patient.query.get_or_404(int(patient_id))

        visit = Visit(
            patient_id = patient.id,
            doctor_id  = int(doctor_id) if doctor_id else None,
            reason     = reason or 'Walk-in / Check-in',
            status     = 'active',
        )
        db.session.add(visit)
        db.session.commit()

        log_action('Patient checked in', f'{patient.patient_id} — {patient.full_name}')
        flash(f'{patient.full_name} checked in successfully! Visit #{visit.id} created.', 'success')
        return redirect(url_for('reception.checkin'))

    return render_template('reception/checkin.html',
                           patients=patients, doctors=doctors,
                           today_visits=today_visits)


# ── Billing ────────────────────────────────────────────────────────
@reception_bp.route('/billing', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def billing():
    patients     = Patient.query.order_by(Patient.full_name).all()
    recent_bills = []  # placeholder — extend with a Bill model later if needed

    if request.method == 'POST':
        patient_id   = request.form.get('patient_id')
        amount       = request.form.get('amount', '').strip()
        description  = request.form.get('description', '').strip()
        payment_mode = request.form.get('payment_mode', 'cash')

        if not patient_id or not amount:
            flash('Please fill in all required fields.', 'danger')
            return render_template('reception/billing.html',
                                   patients=patients, recent_bills=recent_bills)

        patient = Patient.query.get_or_404(int(patient_id))

        log_action(
            f'Billing entry — {payment_mode.upper()} ₹{amount}',
            f'{patient.patient_id} — {description or "General"}'
        )
        flash(f'Payment of ₹{amount} recorded for {patient.full_name} ({payment_mode.title()}).', 'success')
        return redirect(url_for('reception.billing'))

    return render_template('reception/billing.html',
                           patients=patients, recent_bills=recent_bills)


# ── Book Appointment (internal — staff side) ───────────────────────
@reception_bp.route('/staff/book-appointment', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def book_appointment_staff():
    doctors = User.query.filter_by(role='doctor', is_active=True).all()

    if request.method == 'POST':
        # Resolve doctor name from select value
        doc_val = request.form.get('preferred_doctor', '').strip()
        doc_name = doc_val
        if doc_val and doc_val.isdigit():
            doc_obj = User.query.get(int(doc_val))
            doc_name = f"Dr. {doc_obj.full_name}" if doc_obj else doc_val
        appt = Appointment(
            patient_type     = request.form.get('patient_type', 'existing'),
            patient_name     = request.form.get('patient_name', '').strip(),
            phone            = request.form.get('phone', '').strip(),
            email            = request.form.get('email', '').strip(),
            date_of_birth    = request.form.get('date_of_birth', ''),
            patient_id_ref   = request.form.get('patient_id_ref', '').strip(),
            preferred_doctor = doc_name,
            appointment_date = request.form.get('appointment_date', ''),
            reason           = request.form.get('reason', '').strip(),
            status           = 'confirmed',   # staff-booked = auto confirmed
        )
        db.session.add(appt)
        db.session.commit()

        log_action('Booked appointment (staff)',
                   f'{appt.patient_name} — {appt.appointment_date}')
        flash(f'Appointment booked for {appt.patient_name} on {appt.appointment_date}.', 'success')
        return redirect(url_for('appointments.list_appointments'))

    return render_template('reception/book_appointment.html', doctors=doctors,
                           today=date.today().strftime('%Y-%m-%d'))

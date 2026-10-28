"""routes/appointments.py — Appointment management with doctor assignment"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.patient import Appointment, Patient, Visit, AuditLog
from models.user import User
from extensions import db
from datetime import datetime
from functools import wraps

appts_bp = Blueprint('appointments', __name__)

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
        db.session.add(entry); db.session.commit()
    except Exception:
        pass

@appts_bp.route('/appointments')
@login_required
@roles_required('admin', 'receptionist', 'doctor')
def list_appointments():
    status_filter = request.args.get('status', '')
    date_filter   = request.args.get('date', '')
    page          = request.args.get('page', 1, type=int)
    query = Appointment.query
    if status_filter:
        query = query.filter_by(status=status_filter)
    if date_filter:
        query = query.filter(Appointment.appointment_date == date_filter)
    appointments = query.order_by(Appointment.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    counts = {
        'pending'  : Appointment.query.filter_by(status='pending').count(),
        'confirmed': Appointment.query.filter_by(status='confirmed').count(),
        'completed': Appointment.query.filter_by(status='completed').count(),
        'cancelled': Appointment.query.filter_by(status='cancelled').count(),
    }
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    return render_template('appointments/list.html',
        appointments  = appointments,
        counts        = counts,
        status_filter = status_filter,
        date_filter   = date_filter,
        doctors       = doctors,
    )

@appts_bp.route('/appointments/<int:appt_id>')
@login_required
@roles_required('admin', 'receptionist', 'doctor')
def view_appointment(appt_id):
    appt    = Appointment.query.get_or_404(appt_id)
    patient = None
    if appt.patient_id_ref:
        patient = Patient.query.filter_by(patient_id=appt.patient_id_ref).first()
    doctors = User.query.filter_by(role='doctor', is_active=True).all()
    return render_template('appointments/view.html', appt=appt, patient=patient, doctors=doctors)

@appts_bp.route('/appointments/<int:appt_id>/confirm')
@login_required
@roles_required('admin', 'receptionist')
def confirm_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'confirmed'
    db.session.commit()
    log_action('Confirmed appointment', f'{appt.patient_name} — {appt.appointment_date}')
    flash(f'Appointment for {appt.patient_name} confirmed.', 'success')
    return redirect(url_for('appointments.list_appointments'))

@appts_bp.route('/appointments/<int:appt_id>/cancel')
@login_required
@roles_required('admin', 'receptionist')
def cancel_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'cancelled'
    db.session.commit()
    log_action('Cancelled appointment', appt.patient_name)
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('appointments.list_appointments'))

@appts_bp.route('/appointments/<int:appt_id>/complete')
@login_required
@roles_required('admin', 'receptionist', 'doctor')
def complete_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    appt.status = 'completed'
    db.session.commit()
    log_action('Completed appointment', appt.patient_name)
    flash('Appointment marked as completed.', 'success')
    return redirect(url_for('appointments.list_appointments'))

@appts_bp.route('/appointments/<int:appt_id>/assign-doctor', methods=['POST'])
@login_required
@roles_required('admin', 'receptionist')
def assign_doctor(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    doctor_id = request.form.get('doctor_id')
    if doctor_id:
        doctor = User.query.get(int(doctor_id))
        if doctor:
            appt.assigned_doctor_id  = doctor.id
            appt.preferred_doctor    = doctor.full_name
            if appt.status == 'pending':
                appt.status = 'confirmed'
            db.session.commit()
            log_action('Assigned doctor to appointment',
                       f'{appt.patient_name} → Dr. {doctor.full_name}')
            flash(f'Dr. {doctor.full_name} assigned to {appt.patient_name}.', 'success')
    return redirect(url_for('appointments.view_appointment', appt_id=appt_id))

@appts_bp.route('/appointments/<int:appt_id>/attend', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'doctor', 'receptionist')
def attend_patient(appt_id):
    """Create a visit record from an appointment — attends the patient."""
    appt    = Appointment.query.get_or_404(appt_id)
    patient = None
    if appt.patient_id_ref:
        patient = Patient.query.filter_by(patient_id=appt.patient_id_ref).first()

    if request.method == 'POST':
        patient_db_id = request.form.get('patient_db_id')
        if not patient_db_id:
            flash('Please link this appointment to a registered patient first.', 'danger')
            return redirect(url_for('appointments.view_appointment', appt_id=appt_id))

        visit = Visit(
            patient_id = int(patient_db_id),
            doctor_id  = appt.assigned_doctor_id or current_user.id,
            reason     = appt.reason or 'Appointment visit',
            status     = 'active',
        )
        db.session.add(visit)
        appt.status = 'completed'
        db.session.commit()
        log_action('Attended appointment — visit created',
                   f'{appt.patient_name} → Visit #{visit.id}')
        flash(f'Visit #{visit.id} created for {appt.patient_name}.', 'success')
        return redirect(url_for('patients.view_patient', patient_id=int(patient_db_id)))

    patients = Patient.query.order_by(Patient.full_name).all()
    return render_template('appointments/attend.html', appt=appt, patient=patient, patients=patients)

@appts_bp.route('/appointments/<int:appt_id>/register-patient', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'receptionist')
def register_from_appointment(appt_id):
    appt = Appointment.query.get_or_404(appt_id)
    if request.method == 'POST':
        return redirect(url_for('patients.new_patient'))
    return render_template('appointments/register_from_appt.html', appt=appt)

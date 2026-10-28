from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models.patient import Patient, Scan, Appointment, Visit, AuditLog, LabReport
from models.user import User
from extensions import db
from datetime import datetime, date

dashboard_bp = Blueprint('dashboard', __name__)

def get_admin_stats():
    today = date.today()
    return {
        'total_patients'    : Patient.query.count(),
        'new_today'         : Patient.query.filter(db.func.date(Patient.created_at) == today).count(),
        'appointments_today': Appointment.query.filter(Appointment.appointment_date == str(today)).count(),
        'total_scans'       : Scan.query.count(),
        'total_staff'       : User.query.filter_by(is_active=True).count(),
    }

def get_doctor_stats(doctor_id):
    today = date.today()
    return {
        'my_patients'       : Patient.query.count(),
        'visits_today'      : Visit.query.filter(
                                db.func.date(Visit.visit_date) == today,
                                Visit.doctor_id == doctor_id).count(),
        'pending_scans'     : Scan.query.count(),
        'appointments_today': Appointment.query.filter(
                                Appointment.appointment_date == str(today),
                                Appointment.assigned_doctor_id == doctor_id).count(),
    }

def get_receptionist_stats():
    today = date.today()
    checked_in = Visit.query.filter(db.func.date(Visit.visit_date) == today).count()
    return {
        'registered_today'  : Patient.query.filter(db.func.date(Patient.created_at) == today).count(),
        'appointments_today': Appointment.query.filter(Appointment.appointment_date == str(today)).count(),
        'checked_in'        : checked_in,
        'total_patients'    : Patient.query.count(),
    }

def get_radiologist_stats():
    today = date.today()
    return {
        'total_encrypted': Scan.query.count(),
        'uploaded_today' : Scan.query.filter(db.func.date(Scan.uploaded_at) == today).count(),
        'avg_psnr'       : '38.4',
        'scan_types'     : 3,
    }

def get_lab_stats():
    today = date.today()
    return {
        'total_reports'  : LabReport.query.count(),
        'uploaded_today' : LabReport.query.filter(db.func.date(LabReport.uploaded_at) == today).count(),
        'total_patients' : Patient.query.count(),
        'pending'        : 0,
    }

@dashboard_bp.route('/dashboard')
@login_required
def index():
    role = current_user.role
    pending_appts = Appointment.query.filter_by(status='pending').count()

    if role == 'admin':
        role_count = db.session.query(User.role).filter_by(is_active=True).distinct().count()
        return render_template(
            'dashboard/admin.html',
            stats           = get_admin_stats(),
            pending_appts   = pending_appts,
            recent_patients = Patient.query.order_by(Patient.created_at.desc()).limit(6).all(),
            recent_logs     = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(6).all(),
            role_count      = role_count,
        )

    elif role == 'doctor':
        today = date.today()
        today_visits = (Visit.query
            .filter(db.func.date(Visit.visit_date) == today)
            .filter_by(doctor_id=current_user.id)
            .all())
        today_appts = (Appointment.query
            .filter(Appointment.appointment_date == str(today))
            .filter(db.or_(
                Appointment.assigned_doctor_id == current_user.id,
                Appointment.preferred_doctor == current_user.full_name
            )).all())
        return render_template(
            'dashboard/doctor.html',
            stats        = get_doctor_stats(current_user.id),
            today_visits = today_visits,
            today_appts  = today_appts,
            recent_scans = Scan.query.order_by(Scan.uploaded_at.desc()).limit(5).all(),
        )

    elif role == 'radiologist':
        recent_scans = Scan.query.order_by(Scan.uploaded_at.desc()).limit(8).all()
        return render_template(
            'dashboard/radiologist.html',
            stats        = get_radiologist_stats(),
            recent_scans = recent_scans,
        )

    elif role == 'receptionist':
        return render_template(
            'dashboard/receptionist.html',
            stats                = get_receptionist_stats(),
            pending_appts        = pending_appts,
            pending_appointments = Appointment.query.filter_by(status='pending').order_by(Appointment.created_at.desc()).limit(8).all(),
            todays_checkins      = (Visit.query
                                   .filter(db.func.date(Visit.visit_date) == date.today())
                                   .order_by(Visit.visit_date.desc()).limit(8).all()),
            doctors              = User.query.filter_by(role='doctor', is_active=True).all(),
        )

    elif role == 'lab':
        today = date.today()
        recent_reports = LabReport.query.order_by(LabReport.uploaded_at.desc()).limit(10).all()
        return render_template(
            'dashboard/lab.html',
            stats          = get_lab_stats(),
            recent_reports = recent_reports,
        )

    elif role == 'patient':
        return redirect(url_for('patients.my_records'))
    else:
        return redirect(url_for('main.index'))

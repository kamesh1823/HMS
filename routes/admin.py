"""routes/admin.py — Admin-only: user management + audit log"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from models.user import User
from models.patient import AuditLog, Patient
from extensions import db
from functools import wraps

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Administrator access required.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return wrapper

@admin_bp.route('/admin/users')
@login_required
@admin_required
def list_users():
    role_filter = request.args.get('role', '')
    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)
    users = query.order_by(User.role, User.full_name).all()
    return render_template('admin/users.html', users=users, role_filter=role_filter)

@admin_bp.route('/admin/users/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists.', 'danger')
            return render_template('admin/new_user.html')
        user = User(
            full_name  = request.form.get('full_name', '').strip(),
            email      = email,
            role       = request.form.get('role', 'receptionist'),
            department = request.form.get('department', '').strip(),
            phone      = request.form.get('phone', '').strip(),
        )
        user.set_password(request.form.get('password', 'MediVault@123'))
        db.session.add(user)
        db.session.commit()
        entry = AuditLog(user_id=current_user.id, action='Created new user',
                         target=f'{user.email} ({user.role})', ip_address=request.remote_addr)
        db.session.add(entry); db.session.commit()
        flash(f'User {user.full_name} created successfully.', 'success')
        return redirect(url_for('admin.list_users'))
    return render_template('admin/new_user.html')

@admin_bp.route('/admin/users/<int:user_id>/toggle')
@login_required
@admin_required
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.list_users'))
    user.is_active = not user.is_active
    db.session.commit()
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.full_name} {status}.', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/admin/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """Reset any user's password from the admin panel."""
    user     = User.query.get_or_404(user_id)
    new_pass = request.form.get('new_password', '').strip()
    if len(new_pass) < 6:
        flash('Password must be at least 6 characters.', 'danger')
        return redirect(url_for('admin.list_users'))
    user.set_password(new_pass)
    db.session.commit()
    entry = AuditLog(user_id=current_user.id, action='Reset user password',
                     target=f'{user.email} ({user.role})', ip_address=request.remote_addr)
    db.session.add(entry); db.session.commit()
    flash(f'Password reset for {user.full_name}.', 'success')
    return redirect(url_for('admin.list_users'))

@admin_bp.route('/admin/patient-portal/enable', methods=['POST'])
@login_required
@admin_required
def enable_patient_portal():
    """
    Create or update a Patient-role user account linked to a patient record.
    The patient logs in with their registered email + a password set here.
    """
    patient_db_id = request.form.get('patient_id')
    password      = request.form.get('portal_password', '').strip()

    if not patient_db_id or len(password) < 6:
        flash('Please select a patient and set a password (min 6 chars).', 'danger')
        return redirect(url_for('patients.list_patients'))

    patient = Patient.query.get_or_404(int(patient_db_id))

    if not patient.email:
        flash(f'{patient.full_name} has no email on file. Add an email to their profile first.', 'danger')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    # Check if a patient-role user already exists for this email
    existing = User.query.filter_by(email=patient.email).first()
    if existing:
        if existing.role != 'patient':
            flash(f'Email {patient.email} is already used by a staff account ({existing.role}). Cannot create patient portal.', 'danger')
            return redirect(url_for('patients.view_patient', patient_id=patient.id))
        # Update password if already exists
        existing.set_password(password)
        existing.is_active = True
        existing.full_name = patient.full_name
        db.session.commit()
        flash(f'Patient portal updated for {patient.full_name}. They can log in at /auth/login?portal=patient', 'success')
    else:
        # Create new patient-role user
        user = User(
            full_name = patient.full_name,
            email     = patient.email,
            role      = 'patient',
            phone     = patient.phone or '',
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash(f'Patient portal created for {patient.full_name}. Email: {patient.email} | Password set.', 'success')

    entry = AuditLog(user_id=current_user.id, action='Enabled patient portal',
                     target=f'{patient.patient_id} — {patient.full_name}', ip_address=request.remote_addr)
    db.session.add(entry); db.session.commit()
    return redirect(url_for('patients.view_patient', patient_id=patient.id))

@admin_bp.route('/audit-log')
@login_required
@admin_required
def audit_log():
    page  = request.args.get('page', 1, type=int)
    logs  = AuditLog.query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=30, error_out=False)
    users = {u.id: u.full_name for u in User.query.all()}
    return render_template('admin/audit_log.html', logs=logs, users=users)

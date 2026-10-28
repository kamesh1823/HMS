"""
routes/scans.py
Handles medical scan upload → encrypt → view → decrypt → download
"""
import os
import uuid
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, send_file, jsonify, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from models.patient import Patient, Scan, AuditLog
from extensions import db
from datetime import datetime

scans_bp = Blueprint('scans', __name__)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def log_action(action, target):
    try:
        entry = AuditLog(user_id=current_user.id, action=action,
                          target=target, ip_address=request.remote_addr)
        db.session.add(entry); db.session.commit()
    except Exception:
        pass


def roles_required(*roles):
    from functools import wraps
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Upload & Encrypt ───────────────────────────────────────────────
@scans_bp.route('/scans/upload', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'doctor', 'radiologist')
def upload_scan():
    patients = Patient.query.order_by(Patient.full_name).all()
    preselect = request.args.get('patient')

    if request.method == 'POST':
        patient_id_form = request.form.get('patient_id')
        patient = Patient.query.get_or_404(int(patient_id_form))

        if 'scan_file' not in request.files:
            flash('No file selected.', 'danger')
            return render_template('scans/upload.html', patients=patients)

        file = request.files['scan_file']
        if file.filename == '' or not allowed_file(file.filename):
            flash('Invalid file. Please upload PNG, JPG, or BMP.', 'danger')
            return render_template('scans/upload.html', patients=patients)

        # Save original
        ext         = file.filename.rsplit('.', 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        upload_dir  = os.path.join(current_app.root_path, 'uploads')
        enc_dir     = os.path.join(current_app.root_path, 'encrypted')
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(enc_dir, exist_ok=True)

        orig_path = os.path.join(upload_dir, unique_name)
        enc_name  = f"enc_{unique_name.rsplit('.',1)[0]}.png"
        enc_path  = os.path.join(enc_dir, enc_name)

        file.save(orig_path)

        # ── Encrypt ────────────────────────────────────────────────
        from encryption.pipeline import encrypt_image
        dob_str  = str(patient.date_of_birth)
        result   = encrypt_image(
            image_path    = orig_path,
            output_path   = enc_path,
            patient_id    = patient.patient_id,
            date_of_birth = dob_str,
            hospital_id   = patient.hospital_id,
        )

        if result.get('status') == 'error':
            # Model not trained yet — store paths but mark as pending
            flash(f"⚠ Encryption note: {result['message']} — Scan stored, encryption pending.", 'info')
            enc_path = orig_path   # fallback: store original path

        # Save scan record to DB
        scan = Scan(
            patient_id    = patient.id,
            scan_type     = request.form.get('scan_type', 'MRI'),
            body_part     = request.form.get('body_part', ''),
            original_path = orig_path,
            encrypted_path= enc_path,
            uploaded_by   = current_user.id,
            notes         = request.form.get('notes', ''),
        )
        db.session.add(scan)
        db.session.commit()

        log_action('Uploaded & encrypted scan',
                   f'{scan.scan_type} — Patient: {patient.patient_id}')
        flash(f'Scan uploaded and encrypted successfully!', 'success')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    return render_template('scans/upload.html', patients=patients, preselect=preselect)


# ── View / Decrypt ─────────────────────────────────────────────────
@scans_bp.route('/scans/<int:scan_id>/view')
@login_required
@roles_required('admin', 'doctor', 'radiologist')
def view_scan(scan_id):
    scan    = Scan.query.get_or_404(scan_id)
    patient = Patient.query.get_or_404(scan.patient_id)

    from encryption.pipeline import decrypt_image
    from encryption.chaotic_key import get_key_preview

    dec_dir  = os.path.join(current_app.root_path, 'decrypted')
    dec_name = f"dec_{scan_id}_{uuid.uuid4().hex[:8]}.png"
    dec_path = os.path.join(dec_dir, dec_name)
    os.makedirs(dec_dir, exist_ok=True)

    metrics       = {}
    dec_available = False

    result = decrypt_image(
        encrypted_path= scan.encrypted_path,
        output_path   = dec_path,
        patient_id    = patient.patient_id,
        date_of_birth = str(patient.date_of_birth),
        hospital_id   = patient.hospital_id,
    )
    if result.get('status') == 'success':
        metrics       = result
        dec_available = True
    
    log_action('Viewed / decrypted scan',
               f'Scan {scan_id} — Patient: {patient.patient_id}')

    key_preview = get_key_preview(
        patient.patient_id,
        str(patient.date_of_birth),
        patient.hospital_id
    )

    return render_template(
        'scans/view.html',
        scan          = scan,
        patient       = patient,
        metrics       = metrics,
        dec_available = dec_available,
        dec_filename  = dec_name if dec_available else None,
        key_preview   = key_preview,
    )


# ── Download Decrypted ─────────────────────────────────────────────
@scans_bp.route('/scans/<int:scan_id>/download')
@login_required
@roles_required('admin', 'doctor', 'radiologist')
def download_scan(scan_id):
    scan    = Scan.query.get_or_404(scan_id)
    patient = Patient.query.get_or_404(scan.patient_id)

    from encryption.pipeline import decrypt_image
    dec_dir  = os.path.join(current_app.root_path, 'decrypted')
    dec_name = f"dl_{patient.patient_id}_{scan.scan_type}.png"
    dec_path = os.path.join(dec_dir, dec_name)
    os.makedirs(dec_dir, exist_ok=True)

    result = decrypt_image(
        encrypted_path= scan.encrypted_path,
        output_path   = dec_path,
        patient_id    = patient.patient_id,
        date_of_birth = str(patient.date_of_birth),
        hospital_id   = patient.hospital_id,
    )
    if result.get('status') == 'success' and os.path.exists(dec_path):
        log_action('Downloaded decrypted scan',
                   f'Scan {scan_id} — Patient: {patient.patient_id}')
        return send_file(dec_path, as_attachment=True,
                         download_name=f"{patient.patient_id}_{scan.scan_type}.png")

    flash('Decryption failed. Please try again.', 'danger')
    return redirect(url_for('scans.view_scan', scan_id=scan_id))


# ── Serve encrypted image for display ─────────────────────────────
@scans_bp.route('/scans/<int:scan_id>/encrypted-image')
@login_required
def serve_encrypted(scan_id):
    scan = Scan.query.get_or_404(scan_id)
    if os.path.exists(scan.encrypted_path):
        return send_file(scan.encrypted_path, mimetype='image/png')
    return '', 404


# ── Serve decrypted image for display ─────────────────────────────
@scans_bp.route('/decrypted/<filename>')
@login_required
def serve_decrypted(filename):
    safe_name = secure_filename(filename)
    path = os.path.join(current_app.root_path, 'decrypted', safe_name)
    if os.path.exists(path):
        return send_file(path, mimetype='image/png')
    return '', 404


# ── List All Scans ─────────────────────────────────────────────────
@scans_bp.route('/scans')
@login_required
@roles_required('admin', 'doctor', 'radiologist')
def list_scans():
    page   = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    query  = Scan.query

    if search:
        # join Patient to filter by name or patient_id
        query = query.join(Patient, Scan.patient_id == Patient.id).filter(
            db.or_(
                Patient.full_name.ilike(f'%{search}%'),
                Patient.patient_id.ilike(f'%{search}%'),
            )
        )

    scans = query.order_by(Scan.uploaded_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template('scans/list.html', scans=scans, search=search)

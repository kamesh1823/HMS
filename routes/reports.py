"""routes/reports.py — Lab report management"""
import os, uuid
from flask import (Blueprint, render_template, redirect, url_for,
                   flash, request, send_file, current_app, jsonify)
from flask_login import login_required, current_user
from models.patient import Patient, Visit, LabReport, AuditLog
from extensions import db
from functools import wraps

reports_bp  = Blueprint('reports', __name__)
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}

def allowed_file(f):
    return '.' in f and f.rsplit('.', 1)[1].lower() in ALLOWED_EXT

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
        e = AuditLog(user_id=current_user.id, action=action,
                      target=target, ip_address=request.remote_addr)
        db.session.add(e); db.session.commit()
    except Exception:
        pass

def _safe_path(stored_path):
    """
    Returns an absolute path that works even if the project root moved.
    stored_path may be absolute (old) or relative (new).
    Always tries current_app.root_path / uploads/reports / basename first.
    """
    if stored_path and os.path.exists(stored_path):
        return stored_path
    # Fallback: reconstruct from basename
    if stored_path:
        basename = os.path.basename(stored_path)
        rebuilt  = os.path.join(current_app.root_path, 'uploads', 'reports', basename)
        if os.path.exists(rebuilt):
            return rebuilt
    return None

@reports_bp.route('/reports/upload', methods=['GET', 'POST'])
@login_required
@roles_required('admin', 'doctor', 'radiologist', 'receptionist', 'lab')
def upload_report():
    patients = Patient.query.order_by(Patient.full_name).all()

    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        visit_id   = request.form.get('visit_id') or None
        if visit_id and str(visit_id).strip() in ('', '0', 'None'):
            visit_id = None
        if visit_id:
            try:
                visit_id = int(visit_id)
            except (ValueError, TypeError):
                visit_id = None

        if not patient_id:
            flash('Please select a patient.', 'danger')
            return render_template('reports/upload.html', patients=patients)

        patient = Patient.query.get_or_404(int(patient_id))

        if 'report_file' not in request.files:
            flash('No file selected.', 'danger')
            return render_template('reports/upload.html', patients=patients)

        file = request.files['report_file']
        if not file or file.filename == '' or not allowed_file(file.filename):
            flash('Invalid or missing file. Use PNG, JPG, or PDF.', 'danger')
            return render_template('reports/upload.html', patients=patients)

        ext     = file.filename.rsplit('.', 1)[1].lower()
        # Store a RELATIVE path: uploads/reports/<fname>
        # This way download works even if project folder is moved
        fname   = f"report_{uuid.uuid4().hex}.{ext}"
        rep_dir = os.path.join(current_app.root_path, 'uploads', 'reports')
        os.makedirs(rep_dir, exist_ok=True)
        abs_path = os.path.join(rep_dir, fname)
        file.save(abs_path)

        # Save the ORIGINAL filename for download — user sees their file's name
        original_filename = file.filename

        report = LabReport(
            patient_id  = patient.id,
            visit_id    = visit_id,
            # report_name = what user typed, fallback to original filename
            report_name = request.form.get('report_name', '').strip() or original_filename,
            report_type = request.form.get('report_type', 'General'),
            notes       = request.form.get('notes', '').strip(),
            # Store relative path so it works after folder moves
            file_path   = os.path.join('uploads', 'reports', fname),
            uploaded_by = current_user.id,
        )
        db.session.add(report)
        db.session.commit()

        log_action('Uploaded lab report', f'{report.report_name} — {patient.patient_id}')
        flash('Lab report uploaded successfully.', 'success')
        return redirect(url_for('patients.view_patient', patient_id=patient.id))

    return render_template('reports/upload.html', patients=patients)


@reports_bp.route('/reports')
@login_required
def list_reports():
    page           = request.args.get('page', 1, type=int)
    patient_filter = request.args.get('patient_id', '', type=str)
    query          = LabReport.query
    if patient_filter:
        try:
            query = query.filter_by(patient_id=int(patient_filter))
        except ValueError:
            pass
    reports  = query.order_by(LabReport.uploaded_at.desc()).paginate(page=page, per_page=20, error_out=False)
    patients = Patient.query.order_by(Patient.full_name).all()
    return render_template('reports/list.html',
                            reports=reports, patients=patients,
                            patient_filter=patient_filter)


@reports_bp.route('/reports/<int:report_id>/download')
@login_required
def download_report(report_id):
    report = LabReport.query.get_or_404(report_id)

    # Try absolute path, then relative from root_path
    abs_path = _safe_path(
        report.file_path if os.path.isabs(report.file_path)
        else os.path.join(current_app.root_path, report.file_path)
    )

    if abs_path and os.path.exists(abs_path):
        # Use the stored report_name as the download filename
        # Preserve extension from the actual file
        ext           = abs_path.rsplit('.', 1)[-1].lower()
        download_name = report.report_name
        # Make sure download name has the correct extension
        if not download_name.lower().endswith(f'.{ext}'):
            download_name = f"{download_name}.{ext}"

        log_action('Downloaded lab report', report.report_name)
        return send_file(
            abs_path,
            as_attachment = True,
            download_name = download_name
        )

    flash(f'Report file not found on server. It may have been deleted.', 'danger')
    return redirect(url_for('reports.list_reports'))


@reports_bp.route('/reports/<int:report_id>/view')
@login_required
def view_report(report_id):
    report   = LabReport.query.get_or_404(report_id)
    abs_path = _safe_path(
        report.file_path if os.path.isabs(report.file_path)
        else os.path.join(current_app.root_path, report.file_path)
    )
    if abs_path and os.path.exists(abs_path):
        ext = abs_path.rsplit('.', 1)[-1].lower()
        if ext == 'pdf':
            return send_file(abs_path, mimetype='application/pdf')
        return send_file(abs_path, mimetype=f'image/{ext}')
    flash('Report file not found.', 'danger')
    return redirect(url_for('reports.list_reports'))


@reports_bp.route('/reports/<int:report_id>/delete')
@login_required
@roles_required('admin', 'lab', 'doctor')
def delete_report(report_id):
    report   = LabReport.query.get_or_404(report_id)
    abs_path = _safe_path(
        report.file_path if os.path.isabs(report.file_path)
        else os.path.join(current_app.root_path, report.file_path)
    )
    if abs_path and os.path.exists(abs_path):
        os.remove(abs_path)
    db.session.delete(report)
    db.session.commit()
    flash('Report deleted.', 'success')
    return redirect(url_for('reports.list_reports'))


@reports_bp.route('/patients/<int:patient_id>/visits-json')
@login_required
def patient_visits_json(patient_id):
    visits = Visit.query.filter_by(patient_id=patient_id).all()
    return jsonify([{
        'id'    : v.id,
        'date'  : v.visit_date.strftime('%d %b %Y'),
        'reason': v.reason or 'General Visit'
    } for v in visits])

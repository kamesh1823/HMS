from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from models.patient import Appointment
from extensions import db
from datetime import datetime
import requests
import json

main_bp = Blueprint('main', __name__)

WHATSAPP_NUMBER = '6374307624'
GOOGLE_SHEET_EMAIL = 'bmoni1104@gmail.com'

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/book-appointment', methods=['POST'])
def book_appointment():
    # Accept both JSON and form-encoded data
    if request.is_json:
        data = request.get_json()
    else:
        data = request.form.to_dict()
    if not data:
        return jsonify({'success': False, 'message': 'No data received'}), 400

    # Save to DB
    appt = Appointment(
        patient_type     = data.get('patient_type'),
        patient_name     = data.get('patient_name'),
        phone            = data.get('phone'),
        email            = data.get('email'),
        date_of_birth    = data.get('date_of_birth', ''),
        patient_id_ref   = data.get('patient_id_ref', ''),
        preferred_doctor = data.get('preferred_doctor'),
        appointment_date = data.get('appointment_date'),
        reason           = data.get('reason'),
    )
    db.session.add(appt)
    db.session.commit()

    # Build WhatsApp message
    if data.get('patient_type') == 'new':
        msg = (
            f"🏥 *MediVault - New Appointment Request*\n\n"
            f"👤 *Patient Type:* New Patient\n"
            f"📛 *Name:* {data.get('patient_name')}\n"
            f"📞 *Phone:* {data.get('phone')}\n"
            f"📧 *Email:* {data.get('email', 'N/A')}\n"
            f"🎂 *DOB:* {data.get('date_of_birth')}\n"
            f"👨‍⚕️ *Preferred Doctor:* {data.get('preferred_doctor', 'Any')}\n"
            f"📅 *Appointment Date:* {data.get('appointment_date')}\n"
            f"💬 *Reason:* {data.get('reason')}\n"
            f"🕐 *Submitted:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        )
    else:
        msg = (
            f"🏥 *MediVault - Existing Patient Appointment*\n\n"
            f"👤 *Patient Type:* Existing Patient\n"
            f"🪪 *Patient ID:* {data.get('patient_id_ref')}\n"
            f"📛 *Name:* {data.get('patient_name')}\n"
            f"📞 *Phone:* {data.get('phone')}\n"
            f"👨‍⚕️ *Preferred Doctor:* {data.get('preferred_doctor', 'Any')}\n"
            f"📅 *Appointment Date:* {data.get('appointment_date')}\n"
            f"💬 *Reason:* {data.get('reason')}\n"
            f"🕐 *Submitted:* {datetime.now().strftime('%d %b %Y, %I:%M %p')}"
        )

    # WhatsApp link (opens WhatsApp with pre-filled message)
    import urllib.parse
    wa_link = f"https://wa.me/{WHATSAPP_NUMBER}?text={urllib.parse.quote(msg)}"

    return jsonify({
        'success': True,
        'whatsapp_link': wa_link,
        'message': 'Appointment booked successfully!'
    })

@main_bp.route('/presentation')
def presentation():
    return render_template('presentation.html')

@main_bp.route('/verify-patient', methods=['POST'])
def verify_patient():
    """Verify existing patient by ID + name + phone match."""
    data = request.get_json() or {}
    patient_id = data.get('patient_id', '').strip().upper()
    name       = data.get('name', '').strip().lower()
    phone      = data.get('phone', '').strip()

    if not patient_id:
        return jsonify({'valid': False, 'message': 'Please enter your Patient ID.'})

    from models.patient import Patient
    p = Patient.query.filter_by(patient_id=patient_id).first()
    if not p:
        return jsonify({'valid': False, 'message': 'Patient ID not found in our records.'})

    # Verify name AND phone match
    name_ok  = name  in p.full_name.lower() if name else True
    phone_ok = phone in (p.phone or '')   if phone else True

    if name_ok and phone_ok:
        return jsonify({'valid': True,  'patient_name': p.full_name, 'patient_id': p.patient_id})
    else:
        return jsonify({'valid': False, 'message': 'Name or phone does not match our records. Please contact reception.'})

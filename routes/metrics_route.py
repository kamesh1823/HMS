import os, numpy as np
from flask import Blueprint, render_template, jsonify
from flask_login import login_required, current_user
from models.patient import Scan, Patient
from extensions import db

metrics_bp = Blueprint('metrics', __name__)

def _models_exist():
    try:
        from encryption.autoencoder import models_exist
        return models_exist()
    except Exception:
        return False

@metrics_bp.route('/metrics')
@login_required
def metrics_dashboard():
    return render_template('metrics/dashboard.html',
        total_scans    = Scan.query.count(),
        total_patients = Patient.query.count(),
        model_trained  = _models_exist(),
    )

@metrics_bp.route('/metrics/compute-demo')
@login_required
def compute_demo_metrics():
    try:
        from encryption.metrics import compute_psnr, compute_ssim, compute_mse, compute_entropy
        from encryption.chaotic_key import generate_key_array
    except ImportError as e:
        return jsonify({'error': str(e)}), 500
    IMG = 224
    results = []
    np.random.seed(42)
    for i in range(10):
        orig = np.clip(np.random.rand(IMG,IMG).astype(np.float32)*0.7+0.1,0,1)
        pid  = f"MV-2024-{i+1:04d}"
        dob  = f"199{i%10}-0{(i%9)+1}-14"
        key  = generate_key_array(pid,dob,"HOSP_001",IMG*IMG)
        k2d  = (key.reshape(IMG,IMG)/255.0).astype(np.float32)
        enc  = np.mod(orig+k2d,1.0)
        dec  = np.mod(enc-k2d,1.0)
        results.append({'scan_id':i+1,'label':f'Scan {i+1}',
            'enc_psnr':compute_psnr(orig,enc),'dec_psnr':compute_psnr(orig,dec),
            'enc_ssim':compute_ssim(orig,enc),'dec_ssim':compute_ssim(orig,dec),
            'enc_entropy':compute_entropy(enc),'ori_entropy':compute_entropy(orig),
            'enc_mse':compute_mse(orig,enc),'dec_mse':compute_mse(orig,dec)})
    return jsonify({
        'results':results,
        'avg_enc_psnr':round(np.mean([r['enc_psnr'] for r in results]),3),
        'avg_dec_psnr':round(np.mean([r['dec_psnr'] for r in results]),3),
        'avg_enc_ssim':round(np.mean([r['enc_ssim'] for r in results]),4),
        'avg_dec_ssim':round(np.mean([r['dec_ssim'] for r in results]),4),
        'avg_entropy' :round(np.mean([r['enc_entropy'] for r in results]),4),
        'total_scans' :len(results),
    })

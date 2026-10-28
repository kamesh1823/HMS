"""
app.py — MediVault HMS Application Factory
"""
from flask import Flask
from extensions import db, login_manager
import os

def create_app():
    app = Flask(__name__)

    # ── Config ─────────────────────────────────────────────────────
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'medivault-secret-2024-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medivault.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['ENCRYPTED_FOLDER'] = 'encrypted'
    app.config['DECRYPTED_FOLDER'] = 'decrypted'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

    # ── Init extensions ────────────────────────────────────────────
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'warning'

    # ── Register blueprints ────────────────────────────────────────
    from routes.main          import main_bp
    from routes.auth          import auth_bp
    from routes.dashboard     import dashboard_bp
    from routes.patients      import patients_bp
    from routes.scans         import scans_bp
    from routes.appointments  import appts_bp
    from routes.reports       import reports_bp
    from routes.metrics_route import metrics_bp
    from routes.admin         import admin_bp
    from routes.reception     import reception_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp,      url_prefix='/auth')
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(scans_bp)
    app.register_blueprint(appts_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(reception_bp)

    # ── Create DB tables & seed admin ─────────────────────────────
    with app.app_context():
        import models.user
        import models.patient
        db.create_all()
        from models.user import seed_admin
        seed_admin()

    # ── Ensure upload folders exist ────────────────────────────────
    for folder in [
        app.config['UPLOAD_FOLDER'],
        app.config['ENCRYPTED_FOLDER'],
        app.config['DECRYPTED_FOLDER'],
    ]:
        os.makedirs(folder, exist_ok=True)

    return app

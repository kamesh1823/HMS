from extensions import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id         = db.Column(db.Integer, primary_key=True)
    full_name  = db.Column(db.String(120), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)
    # Roles: admin, doctor, radiologist, receptionist, lab, patient
    role       = db.Column(db.String(20), nullable=False, default='receptionist')
    department = db.Column(db.String(100))
    phone      = db.Column(db.String(20))
    is_active  = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def seed_admin():
    if not User.query.filter_by(email='admin@medivault.com').first():
        admin = User(full_name='System Admin', email='admin@medivault.com', role='admin')
        admin.set_password('Admin@1234')
        db.session.add(admin)
        db.session.commit()
        print('[✓] Default admin created: admin@medivault.com / Admin@1234')

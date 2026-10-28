from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')
        user     = User.query.filter_by(email=email, is_active=True).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome, {user.full_name}!', 'success')
            # Patient role → always go to patient portal
            if user.role == 'patient':
                return redirect(url_for('patients.my_records'))
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard.index'))
        else:
            flash('Invalid email or password. Please try again.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('main.index'))

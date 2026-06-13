from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import database_manager

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        initial_balance = request.form.get('initial_balance', 0, type=float)

        if not full_name or not nickname or not password:
            flash('All fields are required.')
            return redirect(url_for('auth.register'))

        hashed_password = generate_password_hash(password)

        if database_manager.add_user(full_name, nickname, hashed_password):
            # Save initial balance for current month
            from datetime import date
            current_month = date.today().strftime('%Y-%m')
            database_manager.set_user_balance(nickname, current_month, initial_balance)

            flash('Registration successful! Please login.')
            return redirect(url_for('auth.login'))
        else:
            flash('Nickname already exists.')
            return redirect(url_for('auth.register'))

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identifier = request.form.get('identifier') # Can be nickname or full name
        password = request.form.get('password')

        user = database_manager.get_user_by_nickname(identifier)
        if not user:
            user = database_manager.get_user_by_full_name(identifier)

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['nickname'] = user['nickname']
            database_manager.update_last_access(user['id'])

            # Check if balance is set
            from datetime import date
            current_month = date.today().strftime('%Y-%m')
            if database_manager.get_user_balance(user['nickname'], current_month) is None:
                # If no balance for current month, check if ANY balance exists
                if not database_manager.get_user_first_balance_month(user['nickname']):
                    return redirect(url_for('set_initial_balance'))

            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials.')

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

from flask import Flask, render_template, session, redirect, url_for
from auth import auth_bp
import database_manager
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Register Blueprints
app.register_blueprint(auth_bp)

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    users = database_manager.get_all_users()
    return render_template('index.html', users=users)

if __name__ == '__main__':
    database_manager.init_db()
    # Host 0.0.0.0 makes it accessible on the local network
    app.run(host='0.0.0.0', port=5000, debug=True)

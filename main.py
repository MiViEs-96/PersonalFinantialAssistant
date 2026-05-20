from flask import Flask, render_template, session, redirect, url_for, request
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

    from datetime import date
    nickname = session['nickname']
    transactions = database_manager.get_transactions_by_user(nickname)
    return render_template('index.html', transactions=transactions, today=date.today().isoformat())

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    date = request.form.get('date')
    amount = float(request.form.get('amount'))
    currency = request.form.get('currency')
    direction = request.form.get('direction')
    category = request.form.get('category')
    comment = request.form.get('comment')
    nickname = session['nickname']

    database_manager.add_transaction(date, amount, currency, direction, category, nickname, comment)
    return redirect(url_for('index'))

@app.route('/stats')
def stats():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    nickname = session['nickname']
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    transactions = database_manager.get_stats_data(nickname, start_date, end_date)

    import analytics
    chart_data = analytics.process_data_for_charts(transactions)

    return render_template('stats.html', chart_data=chart_data, start_date=start_date, end_date=end_date)

if __name__ == '__main__':
    # Verifico le tabelle all'avvio
    from database_manager import init_db
    init_db() # Per semplicità nel server lo facciamo in automatico,
              # lo script db_check.py può essere usato manualmente per controllo interattivo.

    # Host 0.0.0.0 makes it accessible on the local network
    app.run(host='0.0.0.0', port=5000, debug=True)

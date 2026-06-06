from flask import Flask, render_template, session, redirect, url_for, request, g
from auth import auth_bp
import database_manager
import os
import translations
import json
import difflib
import csv
import io
from flask import jsonify, make_response
from mdns_broadcaster import start_mdns_broadcast

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Register Blueprints
app.register_blueprint(auth_bp)

@app.before_request
def before_request():
    g.lang = session.get('lang', 'it')

@app.context_processor
def inject_translations():
    lang = g.lang
    def translate(key):
        return translations.TRANSLATIONS.get(lang, translations.TRANSLATIONS['it']).get(key, key)
    return dict(_=translate)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in translations.TRANSLATIONS:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('dashboard.html')

@app.route('/finance')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    from datetime import date
    nickname = session['nickname']

    # Get monthly stats
    today = date.today()
    start_of_month = date(today.year, today.month, 1).isoformat()
    monthly_data = database_manager.get_stats_data(nickname, start_date=start_of_month)

    monthly_income = sum(t['amount'] for t in monthly_data if t['direction'] == 'entrata')
    monthly_expense = sum(t['amount'] for t in monthly_data if t['direction'] == 'uscita')

    all_transactions = database_manager.get_transactions_by_user(nickname)
    latest_transactions = all_transactions[:5] # Last 5

    # Calculate balance
    monthly_balance = monthly_income - monthly_expense

    # Previous Month Stats
    from datetime import timedelta
    first_of_current = date(today.year, today.month, 1)
    last_of_prev = first_of_current - timedelta(days=1)
    first_of_prev = date(last_of_prev.year, last_of_prev.month, 1)

    prev_month_data = database_manager.get_stats_data(nickname,
                                                     start_date=first_of_prev.isoformat(),
                                                     end_date=last_of_prev.isoformat())

    prev_income = sum(t['amount'] for t in prev_month_data if t['direction'] == 'entrata')
    prev_expense = sum(t['amount'] for t in prev_month_data if t['direction'] == 'uscita')
    prev_balance = prev_income - prev_expense

    # Calculate variation %
    variation = 0
    if prev_balance != 0:
        variation = ((monthly_balance - prev_balance) / abs(prev_balance)) * 100
    elif monthly_balance != 0:
        variation = 100 # From 0 to something is 100% gain

    # Build category translations map for JS
    cat_translations = {}
    lang_dict = translations.TRANSLATIONS.get(g.lang, translations.TRANSLATIONS['it'])
    with open('categories.json', 'r') as f:
        all_cats = json.load(f)
        for cat_list in all_cats.values():
            for c in cat_list:
                cat_translations[c] = lang_dict.get(c.lower(), c)

    return render_template('index.html',
                           transactions=latest_transactions,
                           today=today.isoformat(),
                           monthly_income=monthly_income,
                           monthly_expense=monthly_expense,
                           monthly_balance=monthly_balance,
                           prev_balance=prev_balance,
                           variation=variation,
                           cat_translations=cat_translations)

@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    nickname = session['nickname']
    dates = request.form.getlist('date[]')
    amounts = request.form.getlist('amount[]')
    currencies = request.form.getlist('currency[]')
    directions = request.form.getlist('direction[]')
    categories = request.form.getlist('category[]')
    comments = request.form.getlist('comment[]')

    for i in range(len(dates)):
        if dates[i] and amounts[i]:
            database_manager.add_transaction(
                dates[i],
                float(amounts[i]),
                currencies[i],
                directions[i],
                categories[i],
                nickname,
                comments[i]
            )

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

@app.route('/api/categories')
def get_categories():
    if not os.path.exists('categories.json'):
        return jsonify({"income": [], "expense": []})
    with open('categories.json', 'r') as f:
        return jsonify(json.load(f))

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    nickname = session['nickname']
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    direction = request.args.get('direction')
    category = request.args.get('category')

    transactions, total_count = database_manager.get_paginated_transactions(
        nickname, page, per_page, start_date, end_date, direction, category
    )

    import math
    total_pages = math.ceil(total_count / per_page)

    # Load all categories for the filter
    with open('categories.json', 'r') as f:
        all_cats_data = json.load(f)

    all_cats = sorted(list(set(all_cats_data['income'] + all_cats_data['expense'])))

    # Category translations for display
    lang_dict = translations.TRANSLATIONS.get(g.lang, translations.TRANSLATIONS['it'])
    cat_translations = {c: lang_dict.get(c.lower(), c) for c in all_cats}

    return render_template('history.html',
                           transactions=transactions,
                           page=page,
                           per_page=per_page,
                           total_pages=total_pages,
                           total_count=total_count,
                           all_cats=all_cats,
                           cat_translations=cat_translations,
                           filters={
                               'start_date': start_date,
                               'end_date': end_date,
                               'direction': direction,
                               'category': category
                           })

@app.route('/download_csv')
def download_csv():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    nickname = session['nickname']
    transactions = database_manager.get_transactions_by_user(nickname)

    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow(['ID', 'Date', 'Amount', 'Currency', 'Type', 'Category', 'Comment'])

    for t in transactions:
        writer.writerow([t['id'], t['date'], t['amount'], t['currency'], t['direction'], t['category'], t['comment']])

    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=transactions_{nickname}.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@app.route('/api/add_category', methods=['POST'])
def add_category():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    new_name_raw = data.get('name', '').strip()
    category_type = data.get('type', 'expense').lower()
    force = data.get('force', False)

    if not new_name_raw:
        return jsonify({"error": "Empty name"}), 400

    # Load existing categories
    with open('categories.json', 'r') as f:
        categories = json.load(f)

    target_list = categories.get(category_type, [])

    # 1. Check for translations (Case-insensitive)
    # We want to save the English version if it matches a known translation in ANY language
    eng_name = new_name_raw
    found_in_translations = False

    for lang in translations.TRANSLATIONS:
        for key, val in translations.TRANSLATIONS[lang].items():
            if val.lower() == new_name_raw.lower():
                # We found a match, use the key (which is our English/DB name)
                # But only if it's one of our core categories or keys
                # We need to be careful not to map "Enter" to "enter" as a category.
                # Only map if it's in our initial set or common.
                if key in ['payment', 'sales', 'gift', 'groceries', 'clothes']:
                    eng_name = key.capitalize()
                    found_in_translations = True
                    break
        if found_in_translations: break

    # 2. Duplicate Check
    if any(c.lower() == eng_name.lower() for c in target_list):
        return jsonify({
            "error": "duplicate",
            "message": translations.TRANSLATIONS[g.lang]['category_exists'].format(name=eng_name)
        }), 409

    # 3. Misspelling check (against localized names in current language)
    current_lang_categories = []
    # Map current English categories to current language names for comparison
    for c in target_list:
        loc_val = translations.TRANSLATIONS[g.lang].get(c.lower(), c)
        current_lang_categories.append(loc_val)

    if not force:
        matches = difflib.get_close_matches(new_name_raw, current_lang_categories, n=1, cutoff=0.7)
        if matches:
            return jsonify({
                "error": "mispelling",
                "suggestion": matches[0],
                "message": translations.TRANSLATIONS[g.lang]['did_you_mean'].format(suggestion=matches[0])
            }), 400

    # 4. Add and Save
    target_list.append(eng_name)
    categories[category_type] = target_list
    with open('categories.json', 'w') as f:
        json.dump(categories, f, indent=4)

    return jsonify({"success": True, "name": eng_name, "type": category_type})

if __name__ == '__main__':
    # Verifico le tabelle all'avvio
    from database_manager import init_db
    init_db()

    # Avvio il broadcast mDNS per tumitumi.local
    # In modalità debug=True Flask avvia due processi, quindi controlliamo se è il processo principale
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        zc, info = start_mdns_broadcast("tumitumi", 5000)

    # Host 0.0.0.0 makes it accessible on the local network
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    finally:
        if 'zc' in locals():
            zc.unregister_service(info)
            zc.close()

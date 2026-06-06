from flask import Flask, render_template, session, redirect, url_for, request, g
from auth import auth_bp
import database_manager
import os
import translations
import json
import difflib
from flask import jsonify
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

    return render_template('index.html',
                           transactions=latest_transactions,
                           today=today.isoformat(),
                           monthly_income=monthly_income,
                           monthly_expense=monthly_expense)

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

from flask import Flask, render_template, session, redirect, url_for, request, g
from auth import auth_bp
import database_manager
import os
import translations
import json
import difflib
import csv
import io
import threading
from flask import jsonify, make_response
from mdns_broadcaster import start_mdns_broadcast
from googletrans import Translator

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
        # 1. Check in custom_translations.json
        if os.path.exists('custom_translations.json'):
            try:
                with open('custom_translations.json', 'r') as f:
                    custom = json.load(f)
                    if key in custom and lang in custom[key]:
                        return custom[key][lang]
            except:
                pass

        # 2. Check in standard translations
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

    # Load custom translations
    custom_cats_trans = {}
    if os.path.exists('custom_translations.json'):
        with open('custom_translations.json', 'r') as f:
            custom_cats_trans = json.load(f)

    with open('categories.json', 'r') as f:
        all_cats = json.load(f)
        for cat_list in all_cats.values():
            for c in cat_list:
                # 1. Custom translations first
                if c in custom_cats_trans and g.lang in custom_cats_trans[c]:
                    cat_translations[c] = custom_cats_trans[c][g.lang]
                    continue

                # 2. Standard translations
                translated = lang_dict.get(c.lower())
                if translated:
                    cat_translations[c] = translated
                else:
                    cat_translations[c] = c

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

@app.route('/api/translate_category', methods=['POST'])
def translate_category_api():
    data = request.get_json()
    name = data.get('name')
    source_lang = data.get('source_lang', 'it')
    if not name:
        return jsonify({"error": "No name"}), 400

    translator = Translator()
    try:
        # Translate from the source language used in the primary input
        trans_it = translator.translate(name, src=source_lang, dest='it').text
        trans_en = translator.translate(name, src=source_lang, dest='en').text
        trans_zh = translator.translate(name, src=source_lang, dest='zh-cn').text

        return jsonify({
            "it": trans_it,
            "en": trans_en,
            "zh": trans_zh
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

    custom_trans = {}
    if os.path.exists('custom_translations.json'):
        with open('custom_translations.json', 'r') as f:
            try: custom_trans = json.load(f)
            except: pass

    cat_translations = {}
    for c in all_cats:
        # 1. Custom
        if c in custom_trans and g.lang in custom_trans[c]:
            cat_translations[c] = custom_trans[c][g.lang]
        else:
            # 2. Standard
            translated = lang_dict.get(c.lower())
            cat_translations[c] = translated if translated else c

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

@app.route('/more_info')
def more_info():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    users = database_manager.get_all_users()

    # Get category usage
    usage_counts = database_manager.get_category_usage_counts()

    with open('categories.json', 'r') as f:
        categories_data = json.load(f)

    # Load custom translations for display
    custom_trans = {}
    if os.path.exists('custom_translations.json'):
        with open('custom_translations.json', 'r') as f:
            try: custom_trans = json.load(f)
            except: pass

    # Prepare detailed category info
    cat_details = {"income": [], "expense": []}
    for ctype in ["income", "expense"]:
        for cat in categories_data[ctype]:
            db_dir = 'entrata' if ctype == 'income' else 'uscita'
            count = usage_counts.get((cat, db_dir), 0)

            # Translation logic with multiple fallbacks to avoid empty strings
            display_name = ""

            # 1. Check custom translations first
            if cat in custom_trans:
                display_name = custom_trans[cat].get(g.lang, "")

            # 2. Check standard translations if not found or empty
            if not display_name:
                display_name = translations.TRANSLATIONS[g.lang].get(cat.lower(), "")

            # 3. Final fallback to the database name itself
            if not display_name:
                display_name = cat

            cat_details[ctype].append({
                "name": cat,
                "display": display_name,
                "count": count
            })

    return render_template('more_info.html',
                           users=users,
                           cat_details=cat_details)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user_id = session['user_id']
    old_nickname = session['nickname']
    new_full_name = request.form.get('full_name')
    new_nickname = request.form.get('nickname')

    if database_manager.update_user_profile(user_id, old_nickname, new_full_name, new_nickname):
        session['nickname'] = new_nickname
        return redirect(url_for('more_info'))
    else:
        # Handle error (e.g. nickname taken)
        return "Errore: Nickname già in uso", 400

@app.route('/api/delete_category', methods=['POST'])
def delete_category():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    cat_name = data.get('name')
    cat_type = data.get('type') # 'income' or 'expense'

    if not cat_name or not cat_type:
        return jsonify({"error": "Missing data"}), 400

    # Safety check: count transactions again
    usage_counts = database_manager.get_category_usage_counts()
    db_dir = 'entrata' if cat_type == 'income' else 'uscita'
    if usage_counts.get((cat_name, db_dir), 0) > 0:
        return jsonify({"error": "Category in use"}), 400

    # Delete from categories.json
    with open('categories.json', 'r') as f:
        categories = json.load(f)

    if cat_name in categories[cat_type]:
        categories[cat_type].remove(cat_name)
        with open('categories.json', 'w') as f:
            json.dump(categories, f, indent=4)

        # Optional: delete from custom_translations.json too?
        if os.path.exists('custom_translations.json'):
            with open('custom_translations.json', 'r') as f:
                custom = json.load(f)
            if cat_name in custom:
                del custom[cat_name]
                with open('custom_translations.json', 'w') as f:
                    json.dump(custom, f, indent=4)

        return jsonify({"success": True})

    return jsonify({"error": "Category not found"}), 404

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
    # 'name' here is now the English translation from the JS
    new_name_raw = data.get('name', '').strip().capitalize()
    category_type = data.get('type', 'expense').lower()
    force = data.get('force', False)
    manual_trans = data.get('translations') # {it, en, zh}

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
                possible_keys = ['payment', 'sales', 'gift', 'groceries', 'clothes', 'taxes', 'transport', 'salary', 'entertainment', 'rent', 'utilities', 'bonus']
                if key in possible_keys:
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

    # 3. Misspelling check
    current_lang_categories = []
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

    # 4. Add and Save Category
    target_list.append(eng_name)
    categories[category_type] = target_list
    with open('categories.json', 'w') as f:
        json.dump(categories, f, indent=4)

    # 5. Save Custom Translations
    if manual_trans:
        custom_trans = {}
        if os.path.exists('custom_translations.json'):
            with open('custom_translations.json', 'r') as f:
                try:
                    custom_trans = json.load(f)
                except: pass

        custom_trans[eng_name] = {
            "it": manual_trans.get("it", eng_name),
            "en": manual_trans.get("en", eng_name),
            "zh": manual_trans.get("zh", eng_name)
        }

        with open('custom_translations.json', 'w') as f:
            json.dump(custom_trans, f, indent=4)

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

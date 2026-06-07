def process_data_for_charts(transactions):
    """
    Process transactions list into data formats suitable for Chart.js
    """
    income_total = 0
    expense_total = 0

    income_by_category = {}
    expense_by_category = {}

    for t in transactions:
        amount = t['amount']
        category = t['category']
        direction = t['direction']

        if direction == 'entrata':
            income_total += amount
            income_by_category[category] = income_by_category.get(category, 0) + amount
        else:
            expense_total += amount
            expense_by_category[category] = expense_by_category.get(category, 0) + amount

    return {
        'pie_data': [income_total, expense_total],
        'pie_labels': ['income', 'expense'], # Use keys for translation
        'income_bar_labels': list(income_by_category.keys()),
        'income_bar_values': list(income_by_category.values()),
        'expense_bar_labels': list(expense_by_category.keys()),
        'expense_bar_values': list(expense_by_category.values())
    }

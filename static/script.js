let categories = { income: [], expense: [] };
let translations = {};
let currentActiveSelect = null;
let forceSubmit = false;

// Fetch categories and translations on load
async function init() {
    try {
        const catRes = await fetch('/api/categories');
        categories = await catRes.json();

        // Populate initial row
        updateCategoryOptions(document.querySelector('.category-select'), 'uscita');

        // Set up event listeners for initial row
        document.querySelector('.direction-select').addEventListener('change', (e) => {
            updateCategoryOptions(e.target.closest('tr').querySelector('.category-select'), e.target.value);
        });

        document.querySelector('.category-select').addEventListener('change', handleCategoryChange);

    } catch (e) {
        console.error("Init failed", e);
    }
}

function updateCategoryOptions(selectElement, direction, selectedValue = null) {
    const type = direction === 'entrata' ? 'income' : 'expense';
    const list = categories[type];

    // Clear
    selectElement.innerHTML = '';

    // Add categories
    list.forEach(cat => {
        const opt = document.createElement('option');
        opt.value = cat;
        // Use translated name if available
        opt.textContent = (typeof CAT_TRANSLATIONS !== 'undefined' && CAT_TRANSLATIONS[cat])
                            ? CAT_TRANSLATIONS[cat]
                            : cat;
        if(cat === selectedValue) opt.selected = true;
        selectElement.appendChild(opt);
    });

    // Add "Other"
    const otherOpt = document.createElement('option');
    otherOpt.value = '__other__';
    otherOpt.textContent = typeof TXT_OTHER !== 'undefined' ? TXT_OTHER : 'Altro...';
    if('__other__' === selectedValue) otherOpt.selected = true;
    selectElement.appendChild(otherOpt);
}

function handleCategoryChange(e) {
    if (e.target.value === '__other__') {
        openModal(e.target);
    }
}

function addRow() {
    const tbody = document.querySelector('#transaction-table tbody');

    // Get the first set of 3 rows (Main, Comment Label, Comment Input)
    const mainRow = tbody.rows[0].cloneNode(true);
    const commentLabel = tbody.rows[1].cloneNode(true);
    const commentRow = tbody.rows[2].cloneNode(true);

    // Reset values
    mainRow.querySelectorAll('input').forEach(i => {
        if(i.type !== 'date') i.value = '';
    });
    commentRow.querySelector('input').value = '';

    // Re-setup listeners for the new row
    const dirSelect = mainRow.querySelector('.direction-select');
    const catSelect = mainRow.querySelector('.category-select');

    dirSelect.addEventListener('change', (e) => {
        updateCategoryOptions(catSelect, e.target.value);
    });
    catSelect.addEventListener('change', handleCategoryChange);

    // Initial category population for new row
    updateCategoryOptions(catSelect, dirSelect.value);

    tbody.appendChild(mainRow);
    tbody.appendChild(commentLabel);
    tbody.appendChild(commentRow);
}

function openModal(selectElement) {
    currentActiveSelect = selectElement;
    const direction = selectElement.closest('tr').querySelector('.direction-select').value;
    document.getElementById('modal-type').value = direction === 'entrata' ? 'income' : 'expense';
    document.getElementById('modal-name').value = '';
    document.getElementById('modal-error').style.display = 'none';
    document.getElementById('categoryModal').style.display = 'flex';
    document.getElementById('modal-confirm-btn').textContent = typeof TXT_ADD !== 'undefined' ? TXT_ADD : 'Aggiungi';
    forceSubmit = false;
}

function closeModal() {
    document.getElementById('categoryModal').style.display = 'none';
    if (currentActiveSelect && currentActiveSelect.value === '__other__') {
        currentActiveSelect.selectedIndex = 0; // Reset to first option if canceled
    }
}

async function submitCategory() {
    const name = document.getElementById('modal-name').value.trim();
    const type = document.getElementById('modal-type').value;
    const errorEl = document.getElementById('modal-error');
    const confirmBtn = document.getElementById('modal-confirm-btn');

    if (!name) return;

    try {
        const response = await fetch('/api/add_category', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, type, force: forceSubmit })
        });

        const result = await response.json();

        if (response.ok) {
            // Success! Update categories cache
            categories[type].push(result.name);

            // Update the row that triggered the modal
            if (currentActiveSelect) {
                const tr = currentActiveSelect.closest('tr');
                const dirSelect = tr.querySelector('.direction-select');
                dirSelect.value = type === 'income' ? 'entrata' : 'uscita';
                updateCategoryOptions(currentActiveSelect, dirSelect.value, result.name);
            }

            closeModal();
            // Optional: update all other category selects on the page?
            // For simplicity, they will have the new option when their direction changes
        } else {
            errorEl.textContent = result.message || "Errore";
            errorEl.style.display = 'block';

            if (result.error === 'mispelling' || result.error === 'duplicate') {
                confirmBtn.textContent = typeof TXT_CONFIRM_ANYWAY !== 'undefined' ? TXT_CONFIRM_ANYWAY : 'Conferma Comunque';
                forceSubmit = true;
            }
        }
    } catch (e) {
        errorEl.textContent = "Errore di connessione";
        errorEl.style.display = 'block';
    }
}

document.addEventListener('DOMContentLoaded', init);

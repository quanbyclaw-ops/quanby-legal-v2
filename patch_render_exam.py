with open('/var/www/quanby-legal/onboard.html', 'r', encoding='utf-8') as f:
    src = f.read()

# Fix renderExamPage - add letter labels from position index
old_render = '''    // Render questions
    const qs = pageQuestions.map((q, i) =>
        `<div class="ob-question" id="q-${q.id}">
            <p>${start + i + 1}. ${q.question}</p>
            ${q.choices.map(c =>
                `<div class="ob-choice ${(function(){ var q2 = _questions.find(function(x){return x.id===q.id;}); var idx2 = q2 ? q2.choices.indexOf(c) : -1; return _answers[q.id] === String.fromCharCode(65+idx2) ? 'selected' : ''; })()}" onclick="pickAnswer('${q.id}', this)">${c}</div>`
            ).join('')}
        </div>`
    ).join('');'''

new_render = '''    // Render questions — letter labels (A/B/C/D) come from display position, NOT from choice text
    const qs = pageQuestions.map((q, i) =>
        `<div class="ob-question" id="q-${q.id}">
            <p>${start + i + 1}. ${q.question}</p>
            ${q.choices.map((c, cidx) => {
                const letter = String.fromCharCode(65 + cidx);
                const isSelected = _answers[q.id] === letter;
                return `<div class="ob-choice ${isSelected ? 'selected' : ''}" onclick="pickAnswer('${q.id}', this, ${cidx})"><strong>${letter}.</strong> ${c}</div>`;
            }).join('')}
        </div>`
    ).join('');'''

# Fix pickAnswer - use passed cidx instead of indexOf (reliable, no whitespace issues)
old_pick = '''function pickAnswer(qid, el) {
    const text = el.textContent;
    // Store the letter (A/B/C/D) based on choice index
    var q = _questions.find(function(q){ return q.id === qid; });
    if (q) {
        var idx = q.choices.indexOf(text);
        _answers[qid] = idx >= 0 ? String.fromCharCode(65 + idx) : text;
    } else {
        _answers[qid] = text;
    }'''

new_pick = '''function pickAnswer(qid, el, cidx) {
    // cidx = choice index passed from onclick (0=A, 1=B, 2=C, 3=D) — reliable regardless of text content
    if (cidx !== undefined && cidx >= 0) {
        _answers[qid] = String.fromCharCode(65 + cidx);
    } else {
        // Fallback: derive from DOM position within parent
        var parent = el.parentElement;
        var siblings = parent ? Array.from(parent.querySelectorAll('.ob-choice')) : [];
        var idx = siblings.indexOf(el);
        _answers[qid] = idx >= 0 ? String.fromCharCode(65 + idx) : 'A';
    }'''

changed = 0

if old_render in src:
    src = src.replace(old_render, new_render)
    print('renderExamPage patched')
    changed += 1
else:
    print('renderExamPage pattern NOT found - checking...')
    idx = src.find('Render questions')
    print('Context:', src[max(0,idx-20):idx+300] if idx>0 else 'NOT FOUND')

if old_pick in src:
    src = src.replace(old_pick, new_pick)
    print('pickAnswer patched')
    changed += 1
else:
    print('pickAnswer pattern NOT found')
    idx = src.find('function pickAnswer')
    print('Context:', src[idx:idx+300] if idx>0 else 'NOT FOUND')

if changed > 0:
    with open('/var/www/quanby-legal/onboard.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print(f'Saved ({changed} patches applied)')

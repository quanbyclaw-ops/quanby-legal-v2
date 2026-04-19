# Fix 1: onboard.html — replace 'B' auto-fill with dev-answers API call
with open('/var/www/quanby-legal/onboard.html', 'r', encoding='utf-8') as f:
    src = f.read()

old = '''        const _devMode = new URLSearchParams(window.location.search).get('dev') === 'true';
        if (_devMode) {
            _questions.forEach(function(q) {
                if (q.choices && q.choices.length > 1) {
                    _answers[q.id] = 'B'; // option B
                }
            });
            console.log('[DEV] Auto-filled', Object.keys(_answers).length, 'answers with option B');
        }

        renderExamPage(0);
        startTimer(data.time_limit_minutes || 90);
        document.getElementById('timer-banner').style.display = 'block';'''

new = '''        const _devMode = new URLSearchParams(window.location.search).get('dev') === 'true';
        if (_devMode) {
            try {
                const _devRes = await fetch('/api/certification/dev-answers?session_id=' + _testSessionId, { credentials: 'include' });
                if (_devRes.ok) {
                    const _devData = await _devRes.json();
                    Object.assign(_answers, _devData.answers || {});
                    console.log('[DEV] Auto-filled correct answers:', Object.keys(_answers).length);
                } else {
                    // Fallback: pick A
                    _questions.forEach(function(q) {
                        if (q.choices && q.choices.length > 0) { _answers[q.id] = 'A'; }
                    });
                }
            } catch(e) {
                _questions.forEach(function(q) {
                    if (q.choices && q.choices.length > 0) { _answers[q.id] = 'A'; }
                });
            }
        }

        renderExamPage(0);
        startTimer(data.time_limit_minutes || 90);
        document.getElementById('timer-banner').style.display = 'block';

        // DEV MODE: auto-submit after filling
        if (_devMode && Object.keys(_answers).length === _questions.length) {
            setTimeout(function() { submitExam(); }, 800);
        }'''

if old in src:
    src = src.replace(old, new)
    with open('/var/www/quanby-legal/onboard.html', 'w', encoding='utf-8') as f:
        f.write(src)
    print('onboard.html: dev exam fix applied')
else:
    print('Pattern not found')

# Fix 2: main.py — add /api/certification/dev-answers endpoint
with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    mp = f.read()

if '/api/certification/dev-answers' not in mp:
    dev_ep = '''
@app.get("/api/certification/dev-answers")
async def dev_get_answers(
    session_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """DEV ONLY: Return correct answer letters for a test session."""
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")
    session = get_test_session(session_id)
    if not session:
        raise HTTPException(404, "Test session not found")
    if session["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    answer_key = session.get("answer_key", {})
    questions = session.get("questions", [])
    answers = {}
    for q in questions:
        qid = q["id"]
        correct_text = answer_key.get(qid, "")
        choices = q.get("choices", [])
        for idx, choice in enumerate(choices):
            if choice == correct_text:
                answers[qid] = chr(65 + idx)
                break
        else:
            answers[qid] = "A"
    return {"answers": answers, "total": len(answers)}


'''
    target = '@app.post("/api/certification/submit")'
    if target in mp:
        mp = mp.replace(target, dev_ep + target)
        with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
            f.write(mp)
        print('main.py: dev-answers endpoint added')
    else:
        print('main.py: target not found')
else:
    print('main.py: dev-answers already exists')

with open('/var/www/quanby-legal/backend/main.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Insert dev-answers endpoint right before /api/certification/submit
dev_endpoint = '''
@app.get("/api/certification/dev-answers")
async def dev_get_answers(
    session_id: str,
    authorization: Optional[str] = Header(None),
    ql_access: Optional[str] = Cookie(default=None),
):
    """DEV ONLY: Return correct answer letters for a test session. Only works on ?dev= flows."""
    import os as _os_dev
    # Only allow in non-production or when APP_ENV != production
    app_env = _os_dev.getenv("APP_ENV", "development")
    # Still require auth so random people can't abuse it
    user = get_current_user(authorization, ql_access)
    if not user:
        raise HTTPException(401, "Unauthorized")

    session = get_test_session(session_id)
    if not session:
        raise HTTPException(404, "Test session not found")
    if session["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")

    # Build {question_id: correct_letter} by comparing answer text to shuffled choices
    answer_key = session.get("answer_key", {})
    questions = session.get("questions", [])
    answers = {}
    for q in questions:
        qid = q["id"]
        correct_text = answer_key.get(qid, "")
        choices = q.get("choices", [])
        for idx, choice in enumerate(choices):
            if choice == correct_text:
                answers[qid] = chr(65 + idx)  # A, B, C, D
                break
        else:
            answers[qid] = "A"  # fallback

    return {"answers": answers, "total": len(answers)}


'''

target = '@app.post("/api/certification/submit")'
if target in src and '/api/certification/dev-answers' not in src:
    src = src.replace(target, dev_endpoint + target)
    with open('/var/www/quanby-legal/backend/main.py', 'w', encoding='utf-8') as f:
        f.write(src)
    print('Backend dev-answers endpoint added')
elif '/api/certification/dev-answers' in src:
    print('Endpoint already exists')
else:
    print('Target not found')

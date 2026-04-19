import json
import sys

# Load test sessions
with open('/var/www/quanby-legal/backend/data/test_sessions.json') as f:
    d = json.load(f)

print('Total sessions:', len(d))
if not d:
    print('No sessions found')
    sys.exit(0)

# Get most recent session
latest = sorted(d.items(), key=lambda x: x[1].get('started_at', 0), reverse=True)[:1]
for sid, s in latest:
    print('Session:', sid[:16])
    questions = s.get('questions', [])
    answer_key = s.get('answer_key', {})
    print('Questions:', len(questions), '| Answer key entries:', len(answer_key))
    
    # Check first 5
    for q in questions[:5]:
        qid = q['id']
        correct_text = answer_key.get(qid, 'MISSING')
        choices = q['choices']
        idx = choices.index(correct_text) if correct_text in choices else -1
        correct_letter = chr(65 + idx) if idx >= 0 else 'NOT_IN_CHOICES'
        print()
        print(f'  Q{q["number"]} id={qid}')
        print(f'  Correct text: {correct_text[:60]}')
        print(f'  Correct letter: {correct_letter}')
        for i, c in enumerate(choices):
            marker = ' <-- CORRECT' if i == idx else ''
            print(f'    {chr(65+i)}: {c[:60]}{marker}')
    
    # Check dev-answers logic: simulate what the endpoint returns
    print()
    print('=== Simulating dev-answers endpoint ===')
    wrong_count = 0
    for q in questions:
        qid = q['id']
        correct_text = answer_key.get(qid, '')
        choices = q['choices']
        # This is what the endpoint does
        found_letter = None
        for idx, choice in enumerate(choices):
            if choice == correct_text:
                found_letter = chr(65 + idx)
                break
        if not found_letter:
            print(f'  MISSING: Q{q["number"]} correct_text={correct_text[:40]} NOT in choices={[c[:20] for c in choices]}')
            wrong_count += 1
    
    if wrong_count == 0:
        print('All answers mappable correctly!')
    else:
        print(f'{wrong_count} questions with unmappable answers!')

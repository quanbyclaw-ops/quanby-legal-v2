import sys, json, os
sys.path.insert(0, '/var/www/quanby-legal/backend')
import question_bank

# Simulate exactly what happens end-to-end in dev mode
print('=== Simulating full dev mode exam flow ===')
questions, answer_key = question_bank.get_randomized_test(role='attorney', count=50)

# Simulate dev-answers endpoint
dev_answers = {}
for q in questions:
    qid = q['id']
    correct_text = answer_key.get(qid, '')
    choices = q['choices']
    for idx, choice in enumerate(choices):
        if choice == correct_text:
            dev_answers[qid] = chr(65 + idx)
            break
    else:
        dev_answers[qid] = 'A'
        print(f'FALLBACK A for {qid}: correct_text={correct_text[:40]} not in {[c[:20] for c in choices]}')

print(f'dev_answers has {len(dev_answers)} entries')

# Simulate grade_test exactly
from question_bank import grade_test
result = grade_test(
    questions_without_answers=questions,
    answer_key=answer_key,
    user_answers=dev_answers
)

print(f'Score: {result["correct"]}/{result["total"]} ({result["score_pct"]}%)')
print(f'Passed: {result["passed"]}')

# Show wrong answers
wrong = [r for r in result['results'] if not r['is_correct']]
if wrong:
    print(f'\n{len(wrong)} WRONG answers:')
    for w in wrong[:10]:
        print(f'  Q={w["id"]} user_letter={w["user_answer"]} user_text={w["user_answer_text"][:40]}')
        print(f'    correct={w["correct_answer_text"][:40]}')
else:
    print('All correct!')

# Check the grade_test letter->text resolution
print('\n=== Checking grade_test resolution for first 3 ===')
for q in questions[:3]:
    qid = q['id']
    letter = dev_answers.get(qid, '?')
    choices = q['choices']
    idx = ord(letter) - ord('A') if letter else -1
    resolved_text = choices[idx] if 0 <= idx < len(choices) else 'OUT_OF_RANGE'
    correct_text = answer_key.get(qid, '')
    match = resolved_text == correct_text
    print(f'  {qid}: letter={letter} resolved={resolved_text[:40]} correct={correct_text[:40]} MATCH={match}')

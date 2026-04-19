import sys
sys.path.insert(0, '/var/www/quanby-legal/backend')
import question_bank
import ast

# Syntax check
with open('/var/www/quanby-legal/backend/question_bank.py') as f:
    src = f.read()
ast.parse(src)
print('Syntax OK')

print('Attorney questions:', len(question_bank.ATTORNEY_QUESTIONS))
q = question_bank.ATTORNEY_QUESTIONS[0]
print('Sample question:', q['question'][:60])
print('Choices (no prefix expected):')
for i, c in enumerate(q['choices']):
    print(f'  {chr(65+i)}: {c[:60]}')
print('Correct letter:', q['answer'])
print('Correct text:', q['choices'][ord(q['answer'])-ord('A')][:60])

# Test get_randomized_test
questions, answer_key = question_bank.get_randomized_test(role='attorney', count=50)
print()
print('Randomized test: questions=%d, answer_key=%d' % (len(questions), len(answer_key)))

# Verify all answers resolve correctly
errors = 0
for q2 in questions:
    qid = q2['id']
    correct_text = answer_key.get(qid, '')
    choices = q2['choices']
    if correct_text not in choices:
        print('ERROR: correct_text not in choices for', qid)
        print('  correct_text:', correct_text[:60])
        print('  choices:', [c[:30] for c in choices])
        errors += 1

if errors == 0:
    print('All 50 answers correctly map to choices!')
else:
    print(f'{errors} errors found!')

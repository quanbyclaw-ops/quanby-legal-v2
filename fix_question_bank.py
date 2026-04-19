import re

with open('/var/www/quanby-legal/backend/question_bank.py', 'r', encoding='utf-8') as f:
    src = f.read()

# Strip the "A. ", "B. ", "C. ", "D. " prefixes from all choice strings
# Pattern: "A. text", "B. text", "C. text", "D. text" inside string literals
# Only strip the leading letter+dot+space when it's at the start of a quoted string

def strip_choice_prefix(match):
    full = match.group(0)
    # Extract the content
    quote = match.group(1)  # " or '
    prefix = match.group(2)  # A. or B. etc
    text = match.group(3)    # rest of content
    return f'{quote}{text}{quote}'

# Replace "A. text", "B. text" etc. at start of string literals
pattern = r'("|\')([A-D]\. )([^"\']+)\1'

# Count before
before = len(re.findall(pattern, src))
print(f'Found {before} choice strings with letter prefixes')

# Also need to update answer_key logic — currently stores full text including prefix
# After stripping, the answer key stores text WITHOUT prefix, matching the stripped choices
new_src = re.sub(pattern, strip_choice_prefix, src)

# Verify the answer references are still valid
# The "answer": "B" fields are letter references to original order — those stay the same
# The get_randomized_test function does:
#   correct_answer_text = choices[ord(q["answer"]) - ord("A")]
# This still works because choices is the list BEFORE shuffle,
# and we still strip prefix from the text, so key = clean text

after = len(re.findall(pattern, new_src))
print(f'After: {after} remaining (should be 0)')

# Sanity check — make sure question structure looks right
sample_idx = new_src.find('"atty_001"')
print('Sample after fix:')
print(new_src[sample_idx:sample_idx+400])

with open('/var/www/quanby-legal/backend/question_bank.py', 'w', encoding='utf-8') as f:
    f.write(new_src)
print('Written successfully')

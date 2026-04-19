import ast
for f in ['main.py', 'ai_engine.py']:
    try:
        ast.parse(open(f'/var/www/quanby-legal/backend/{f}').read())
        print(f'{f}: OK')
    except SyntaxError as e:
        print(f'{f}: SYNTAX ERROR {e}')

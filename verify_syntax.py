import ast
src = open('/var/www/quanby-legal/backend/main.py').read()
ast.parse(src)
print('Syntax OK')

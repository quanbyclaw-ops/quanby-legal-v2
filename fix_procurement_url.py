import sqlite3
conn = sqlite3.connect('/var/www/quanby-builder/database/database.sqlite')
conn.execute("UPDATE builds SET product_url='https://bcs.quanbyai.com' WHERE id=14")
conn.commit()
for row in conn.execute('SELECT id, title, product_url FROM builds WHERE id=14'):
    print(f'[{row[0]}] {row[1]} -> {row[2]}')
conn.close()

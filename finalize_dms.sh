#!/bin/bash
# Update builder DB for Quanby DMS
sqlite3 /var/www/quanby-builder/database/database.sqlite "UPDATE builds SET product_url='https://dms.quanbyai.com' WHERE id=15;"
echo "Builder DB:"
sqlite3 /var/www/quanby-builder/database/database.sqlite "SELECT id,title,product_url FROM builds WHERE id=15;"

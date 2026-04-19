#!/bin/bash

# Update builder DB
sqlite3 /var/www/quanby-builder/database/database.sqlite "UPDATE builds SET product_url='https://proc.quanbyai.com' WHERE id=14;"
echo "Builder DB updated:"
sqlite3 /var/www/quanby-builder/database/database.sqlite "SELECT id,title,product_url FROM builds WHERE id=14;"

# Update APP_URL in bcs-ims .env
sed -i 's|APP_URL=.*|APP_URL=https://proc.quanbyai.com|' /var/www/bcs-ims/.env
echo "APP_URL: $(grep APP_URL /var/www/bcs-ims/.env)"

# Clear laravel config cache
cd /var/www/bcs-ims && php artisan config:clear 2>&1 | tail -1

echo "All done"

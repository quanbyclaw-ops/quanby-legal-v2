#!/bin/bash
set -e

# Create nginx config for dms.quanbyai.com
cat > /etc/nginx/sites-available/dms-quanby << 'NGINX'
server {
    server_name dms.quanbyai.com;
    root /var/www/opapru-edms/public;
    index index.php index.html;
    client_max_body_size 50M;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }
    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.2-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_read_timeout 120s;
    }
    location ~ /\.ht { deny all; }

    listen 80;
}
NGINX

ln -sf /etc/nginx/sites-available/dms-quanby /etc/nginx/sites-enabled/dms-quanby

nginx -t && nginx -s reload
echo "nginx ready for dms.quanbyai.com"

# Update APP_URL in .env
sed -i 's|APP_URL=.*|APP_URL=https://dms.quanbyai.com|' /var/www/opapru-edms/.env
echo "APP_URL: $(grep APP_URL /var/www/opapru-edms/.env)"
cd /var/www/opapru-edms && php artisan config:clear 2>&1 | tail -1

# Try SSL cert (needs DNS first)
certbot --nginx -d dms.quanbyai.com --non-interactive --agree-tos --email admin@quanbyai.com 2>&1 | tail -5 || echo "SSL: add DNS record first — certbot will run when DNS propagates"

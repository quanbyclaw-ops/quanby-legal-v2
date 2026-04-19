#!/bin/bash
set -e

# 1. Create nginx config for proc.quanbyai.com (same app as bcs.quanbyai.com)
cat > /etc/nginx/sites-available/proc-ims << 'NGINX'
server {
    server_name proc.quanbyai.com;
    root /var/www/bcs-ims/public;
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

# 2. Enable the site
ln -sf /etc/nginx/sites-available/proc-ims /etc/nginx/sites-enabled/proc-ims

# 3. Test nginx
nginx -t && nginx -s reload
echo "nginx reloaded with proc.quanbyai.com"

# 4. Issue SSL cert for proc.quanbyai.com
# Note: DNS must point proc.quanbyai.com to this server first
# certbot will run if DNS is already set
certbot --nginx -d proc.quanbyai.com --non-interactive --agree-tos --email admin@quanbyai.com 2>&1 | tail -10 || echo "Certbot: may need DNS to propagate first — run manually if needed"

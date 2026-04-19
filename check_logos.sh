#!/bin/bash
for f in sc-logo.png doc-logo-white.png hyperledger-logo.png dict-logo.png pnpki-logo.jpg linux-foundation-logo.png qlegal-logo-sm.png; do
    printf "%-40s " "$f"
    curl -s -o /dev/null -w '%{http_code} %{content_type} size=%{size_download}b' "https://legal.quanbyai.com/assets/partners/$f" 2>/dev/null || \
    curl -s -o /dev/null -w '%{http_code} %{content_type} size=%{size_download}b' "https://legal.quanbyai.com/$f" 2>/dev/null
    echo
done

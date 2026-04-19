#!/bin/bash
# Download actual partner logos from Google Drive
# File IDs found from the folder: 142hrwV7iQMNivhn26VxevyeZKMAr0k2o

DEST="/var/www/quanby-legal/assets/partners"
mkdir -p "$DEST"

download_gdrive() {
    local id="$1"
    local out="$2"
    echo "Downloading: $out"
    curl -sL "https://drive.google.com/uc?export=download&id=${id}&confirm=t" \
        -H "User-Agent: Mozilla/5.0" \
        -o "$out" -w "  -> HTTP %{http_code} size=%{size_download}b\n" --max-time 30
    # Check if it's actually an image
    file "$out" | grep -qE 'image|PNG|JPEG|SVG' && echo "  OK: image" || echo "  WARN: not an image - $(file $out | head -c 100)"
}

# We'll try to enumerate the folder via Google Drive's export
# Fetch raw folder data
curl -sL "https://drive.google.com/drive/folders/142hrwV7iQMNivhn26VxevyeZKMAr0k2o" \
    -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36" \
    -o /tmp/gdrive_folder.html 2>/dev/null

# Extract file IDs from the HTML (pattern: "id":"FILEID")
echo "=== File IDs found in folder page ==="
grep -oP '"id":"\K[a-zA-Z0-9_-]{25,}' /tmp/gdrive_folder.html | sort -u | head -30

echo ""
echo "=== File names found ==="
grep -oP 'DICT Commercial|Hyperledger Fabric|Linux Foundation|PNPKI|SC-Logo|DOC - Horizontal|Proptech' /tmp/gdrive_folder.html | sort -u

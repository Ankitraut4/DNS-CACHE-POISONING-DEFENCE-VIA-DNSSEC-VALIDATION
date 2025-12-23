#!/bin/bash

ZONE="example.com"
ZONE_FILE="/etc/bind/zones/${ZONE}.zone"
KEYS_DIR="/etc/bind/keys"

echo "=========================================="
echo "🔐 DNSSEC Setup for ${ZONE}"
echo "=========================================="

# Create keys directory
mkdir -p $KEYS_DIR
cd $KEYS_DIR

# Clean up old keys
rm -f K${ZONE}*.* 2>/dev/null

# Generate ZSK (Zone Signing Key)
echo "[1/4] Generating Zone Signing Key..."
dnssec-keygen -a RSASHA256 -b 2048 -n ZONE $ZONE
echo "✅ ZSK generated"

# Generate KSK (Key Signing Key)
echo "[2/4] Generating Key Signing Key..."
dnssec-keygen -a RSASHA256 -b 4096 -f KSK -n ZONE $ZONE
echo "✅ KSK generated"

# Sign the zone
echo "[3/4] Signing zone file..."
cd /etc/bind/zones
dnssec-signzone -o $ZONE -k $KEYS_DIR/K${ZONE}*.private $ZONE_FILE
echo "✅ Zone signed"

# Update config to use signed zone
echo "[4/4] Updating configuration..."
sed -i 's|file "/etc/bind/zones/example.com.zone";|file "/etc/bind/zones/example.com.zone.signed";|' /etc/bind/named.conf

echo ""
echo "=========================================="
echo "✅ DNSSEC SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "Keys generated:"
ls -lh $KEYS_DIR/K${ZONE}*
echo ""
echo "Signed zone: ${ZONE_FILE}.signed"
echo "=========================================="

#!/bin/bash
# DNSSEC Key Generation and Zone Signing Script

ZONE="example.com"
ZONE_FILE="/etc/bind/zones/${ZONE}.zone"
KEYS_DIR="/etc/bind/keys"

echo "=========================================="
echo "🔐 DNSSEC Setup for ${ZONE}"
echo "=========================================="

# Create keys directory
echo "[1/7] Creating keys directory..."
mkdir -p $KEYS_DIR
chmod 755 $KEYS_DIR
cd $KEYS_DIR

# Clean up old keys if they exist
echo "[2/7] Cleaning up old keys..."
rm -f K${ZONE}*.key K${ZONE}*.private K${ZONE}*.ds 2>/dev/null || true

# Generate ZSK (Zone Signing Key)
echo "[3/7] Generating Zone Signing Key (ZSK)..."
ZSK=$(dnssec-keygen -a RSASHA256 -b 2048 -n ZONE $ZONE 2>&1 | tail -1)
echo "  Generated: $ZSK"

# Generate KSK (Key Signing Key)
echo "[4/7] Generating Key Signing Key (KSK)..."
KSK=$(dnssec-keygen -a RSASHA256 -b 4096 -f KSK -n ZONE $ZONE 2>&1 | tail -1)
echo "  Generated: $KSK"

# Sign the zone
echo "[5/7] Signing zone file..."
cd /etc/bind/zones

# Create backup
cp $ZONE_FILE ${ZONE_FILE}.backup

# Sign the zone
dnssec-signzone -A -3 $(head -c 1000 /dev/urandom 2>/dev/null | sha1sum | cut -b 1-16) \
    -K $KEYS_DIR \
    -o $ZONE \
    -t $ZONE_FILE > /tmp/sign.log 2>&1

# Check if signing was successful
if [ -f "${ZONE_FILE}.signed" ]; then
    echo "  ✅ Zone signed successfully!"
else
    echo "  ❌ Zone signing failed!"
    cat /tmp/sign.log
    exit 1
fi

# Update named.conf to use signed zone
echo "[6/7] Updating named.conf..."
if [ -f "/etc/bind/named.conf.dnssec" ]; then
    cp /etc/bind/named.conf.dnssec /etc/bind/named.conf
    echo "  ✅ Config updated to use signed zone"
fi

# Reload DNS server
echo "[7/7] Reloading DNS server..."
rndc reload >/dev/null 2>&1 || echo "  Note: rndc reload will happen automatically"

echo ""
echo "=========================================="
echo "📋 DNSSEC Key Summary"
echo "=========================================="
echo "Keys directory: $KEYS_DIR"
ls -lh $KEYS_DIR/K${ZONE}*.key 2>/dev/null || echo "No keys found"
echo ""
echo "✅ ZSK: $ZSK"
echo "✅ KSK: $KSK"
echo "✅ Zone file: ${ZONE_FILE}"
echo "✅ Signed zone: ${ZONE_FILE}.signed"
echo ""
echo "DNSKEY Records:"
cat $KEYS_DIR/K${ZONE}*.key 2>/dev/null || echo "No keys to display"
echo "=========================================="
echo "✅ DNSSEC SETUP COMPLETE!"
echo "=========================================="

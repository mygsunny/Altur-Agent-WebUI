#!/bin/sh
# Create (once) a private Altru LAN certificate authority and issue a server
# certificate for this machine, for HERMES_WEBUI_TLS_CERT / HERMES_WEBUI_TLS_KEY.
#
# Usage: make-lan-cert.sh <LAN IP or hostname> [more names...]
#
# Writes <first name>.pem / <first name>.key next to the CA, so one machine can
# issue certificates for every server and the CA key never has to be copied.
# Browsers trust the certificate only after ca.pem is trusted on each device
# (macOS: Keychain Access > System > Always Trust; iOS: install profile, then
# Settings > General > About > Certificate Trust Settings).
set -eu
[ $# -ge 1 ] || { echo "usage: $0 <LAN IP or hostname> [more names...]" >&2; exit 1; }
DIR="${ALTRU_TLS_DIR:-$HOME/.local/share/altru-tls}"
mkdir -p "$DIR"; chmod 700 "$DIR"; cd "$DIR"
umask 077
if [ ! -f ca.key ]; then
  openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes \
    -keyout ca.key -out ca.pem -days 3650 -subj "/CN=Altru LAN CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" 2>/dev/null
  echo "Created CA: $DIR/ca.pem (trust this on each device)"
fi
SAN=""
for name in "$@"; do
  case "$name" in
    *[!0-9.]*) SAN="${SAN:+$SAN,}DNS:$name" ;;
    *) SAN="${SAN:+$SAN,}IP:$name" ;;
  esac
done
OUT="$1"
openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout "$OUT.key" -out "$OUT.csr" \
  -subj "/CN=$1" 2>/dev/null
printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature\n' "$SAN" > "$OUT.ext"
# 825 days is the longest validity Apple platforms accept for TLS server certs.
openssl x509 -req -in "$OUT.csr" -CA ca.pem -CAkey ca.key -CAcreateserial -out "$OUT.pem" \
  -days 825 -extfile "$OUT.ext" 2>/dev/null
rm -f "$OUT.csr" "$OUT.ext"
chmod 600 "$OUT.key" "$OUT.pem" ca.key
echo "Server certificate for $SAN:"
echo "  ALTRU_LAN_HTTPS_CERT=$DIR/$OUT.pem"
echo "  ALTRU_LAN_HTTPS_KEY=$DIR/$OUT.key"

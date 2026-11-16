#!/bin/sh
# Create (once) a private Altru LAN certificate authority and issue a server
# certificate for this machine, for HERMES_WEBUI_TLS_CERT / HERMES_WEBUI_TLS_KEY.
#
# Usage: make-lan-cert.sh <LAN IP or hostname> [more names...]
#
# Browsers trust the certificate only after ca.pem is trusted on each device
# (macOS: Keychain Access > System > Always Trust; iOS: install profile, then
# Settings > General > About > Certificate Trust Settings). Copy the CA to other
# servers instead of creating a second one, so devices trust one CA for all.
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
openssl req -newkey ec -pkeyopt ec_paramgen_curve:P-256 -nodes -keyout server.key -out server.csr \
  -subj "/CN=$1" 2>/dev/null
printf 'subjectAltName=%s\nextendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature\n' "$SAN" > server.ext
# 825 days is the longest validity Apple platforms accept for TLS server certs.
openssl x509 -req -in server.csr -CA ca.pem -CAkey ca.key -CAcreateserial -out server.pem \
  -days 825 -extfile server.ext 2>/dev/null
rm -f server.csr server.ext
chmod 600 server.key server.pem ca.key
echo "Server certificate for $SAN:"
echo "  HERMES_WEBUI_TLS_CERT=$DIR/server.pem"
echo "  HERMES_WEBUI_TLS_KEY=$DIR/server.key"

#!/usr/bin/env bash
# Lancia glisweb-cli. Il venv sta in ~/.cache ( fuori da Dropbox ) e si crea al primo giro.
# Senza argomenti: da remoto ( login col codice deploy ). Con --demo: deploy finto ( password 'demo' ).
# Con argomenti: passati tali e quali, p.es. -c /var/www/glisweb --stato DEV ( sul server )
# o -k glisdev: login col codice deploy via configserver, poi diretto al deploy
set -e
DEV="$(cd "$(dirname "$0")" && pwd)"
C="$HOME/.cache/glisweb-cli"
if [ ! -x "$C/venv/bin/glisweb-cli" ]; then
  python3 -m venv "$C/venv"
  "$C/venv/bin/pip" install -q -e "$DEV"
fi
mkdir -p "$C/demo-deploy/_src" "$C/demo-deploy/src"
touch "$C/demo-deploy/_src/_config.php"
# senza argomenti: da remoto ( codice, utente, password ); la demo vuole --demo
[ "$*" = "--demo" ] && set -- -c "$C/demo-deploy" --demo
exec "$C/venv/bin/glisweb-cli" "$@"

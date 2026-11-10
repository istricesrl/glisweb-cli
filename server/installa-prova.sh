#!/bin/bash
# installa _cli.php su glisdev ( web03 ) e prova una pagina: bash installa-prova.sh [pagina [tabella id]]
# p.es. bash installa-prova.sh anagrafica.form anagrafica 1
D=$(dirname "$0"); P=${1:-anagrafica.view}; TB=${2:-}; ID=${3:-}
R=root@web03.istricesrl.it; A=/var/www/glisdev.istricesrl.com/dev/_src/_api
U=https://glisdev.istricesrl.com/
# la password di root di glisdev: GLISDEV_PASW o il file server/.pasw ( fuori dal repo, vedi .gitignore )
PASW=${GLISDEV_PASW:-$(cat "$D/.pasw" 2>/dev/null)}
[ -z "$PASW" ] && { echo "KO: manca la password ( GLISDEV_PASW o $D/.pasw )"; exit 1; }
# in locale php non c'e': il controllo di sintassi si fa sul server, prima di sostituire il file
scp -q "$D/_cli.php" $R:/tmp/_cli.nuovo.php || exit 1
ssh $R "php -l /tmp/_cli.nuovo.php && cp -p $A/_cli.php $A/_cli.php.prima && cp /tmp/_cli.nuovo.php $A/_cli.php && chown --reference=$A/_cli.php.prima $A/_cli.php" || exit 1
echo "installato ( copia del precedente: _cli.php.prima )"
T=$(curl -s -A glisweb-cli -H 'Content-Type: application/json' \
  -d "{\"__login__\":{\"user\":\"root\",\"pasw\":\"$PASW\"}}" ${U}api/login \
  | python3 -c 'import json,sys;print(json.load(sys.stdin).get("token",""))')
[ -z "$T" ] && { echo "KO: login fallito"; exit 1; }
REC=""; [ -n "$TB" ] && REC=",\"record\":{\"tabella\":\"$TB\",\"id\":\"$ID\"}"
curl -s -A glisweb-cli -H 'Content-Type: application/json' -H "gliswebAuthKey: $T" \
  -d "{\"pagina\":\"$P\"$REC}" ${U}api/cli | python3 -c '
import json,sys; r=sys.stdin.read()
try: d=json.loads(r)
except Exception: print(r[:2500]); sys.exit()
print(d.get("status"),d.get("err"),"schema",d.get("schema"),"tabs",d.get("tabs"))
f=d.get("form")
if f:
    rec=f.get("record") or {}
    print("table",f.get("table"),"method",f.get("method"),"activity",f.get("activity"),"err",f.get("err"))
    print("record",{k:v for k,v in rec.items() if not isinstance(v,(list,dict))})
    print("figli",{k:(len(v) if isinstance(v,(list,dict)) else v) for k,v in rec.items() if isinstance(v,(list,dict))})
    for k,v in rec.items():
        if isinstance(v,(list,dict)) and v: print(" ",k,json.dumps(v,ensure_ascii=False)[:300])
    print("select",{k:(len(v) if isinstance(v,(list,dict)) else v) for k,v in (f.get("select") or {}).items()})
    s=(f.get("select") or {}).get("sesso"); print("  sesso",json.dumps(s,ensure_ascii=False)[:300])
else:
    v=d.get("view") or {}
    print("id",v.get("id"),"table",v.get("table"),"open",v.get("open"),"pager",v.get("pager"))
    print("cols",v.get("cols")); print("class",v.get("class"))
    print("righe",len(v.get("data") or []), (v.get("data") or [None])[0])
print("rumore",d.get("rumore"))'

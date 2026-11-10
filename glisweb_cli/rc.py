"""I preset di accesso in ~/.glisweb-cli.rc: codice deploy, utente e password, per non rifare il login a mano.

Il file ha righe `chiave = valore`. Le righe prima di ogni sezione formano il preset di default,
e ogni `[nome]` apre un preset con quel nome:

    codice   = 30039081
    utente   = root
    password = segreta

    [gimbe]
    codice   = 12345678
    utente   = fabio
    password = altra

Le chiavi valide sono codice, utente e password; `#` e `;` aprono un commento.
"""
import sys
from pathlib import Path

RC = Path.home() / ".glisweb-cli.rc"
CHIAVI = ("codice", "utente", "password")
DEFAULT = ""  # nome del preset fatto dalle righe prima della prima sezione


def leggi(percorso: Path = RC) -> dict[str, dict]:
    """Restituisce {nome: {codice, utente, password}}, nell'ordine del file. Se il file manca: {}."""
    try:
        righe = percorso.read_text().splitlines()
    except OSError:
        return {}
    preset, nome = {}, DEFAULT
    for r in righe:
        r = r.strip()
        if not r or r[0] in "#;":
            continue
        if r.startswith("[") and r.endswith("]"):
            nome = r[1:-1].strip()
            preset.setdefault(nome, {})
            continue
        k, sep, v = r.partition("=")
        k = k.strip().lower()
        if sep and k in CHIAVI:
            preset.setdefault(nome, {})[k] = v.strip()
    return {n: p for n, p in preset.items() if p}


def scegli(chiave: str | None = None, percorso: Path = RC) -> dict:
    """Il preset da usare: con `chiave` quello che ha quel nome o quel codice, senza il default
    ( o il primo del file ). Se non ce n'e' nessuno: {}."""
    preset = leggi(percorso)
    if not preset:
        return {}
    if chiave:
        if chiave in preset:
            return preset[chiave]
        for p in preset.values():
            if p.get("codice") == chiave:
                return p
        return {}
    return preset.get(DEFAULT) or next(iter(preset.values()))


def avvisa_permessi(percorso: Path = RC):
    """Il file contiene password: se lo leggono anche gli altri utenti, lo si dice ( non si blocca )."""
    try:
        if percorso.stat().st_mode & 0o077:
            print(f"attenzione: {percorso} e' leggibile da altri utenti, conviene chmod 600", file=sys.stderr)
    except OSError:
        pass

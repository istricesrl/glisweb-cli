"""Le chiamate al sito glisweb: login ( api/login ) e struttura ( api/cli ). Il resto va sul database."""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

CACHE = Path.home() / ".cache" / "glisweb-cli"
PROFILI = Path.home() / ".config" / "glisweb-cli" / "profili.json"
CONFIGSERVER = "https://configserver.istricesrl.com/"
DURATA_TOKEN = 3600  # il token vale un'ora dall'ultima chiamata ( _cli.php riscrive la chiave a ogni uso )


class ErroreApi(Exception):
    pass


class SessioneScaduta(ErroreApi):
    """Il sito ha risposto 401: il token non vale piu'. La TUI torna subito al login."""


def url_del_deploy(cx: dict, stato: str = "DEV", sito: str | None = None) -> str:
    """Come _025.site.php: protocollo://host.dominio/ del sito, per lo stato scelto."""
    siti = cx.get("sites") or {}
    if not siti:
        raise ErroreApi("nessun sito nella configurazione: usa --url")
    s = siti[sito] if sito else next(iter(siti.values()))
    try:
        host = s["hosts"].get(stato)
        dominio = s["domains"][stato]
        proto = s.get("protocols", {}).get(stato, "https")
    except KeyError:
        raise ErroreApi(f"il sito non ha lo stato {stato}: usa --stato o --url")
    return f"{proto}://{host + '.' if host else ''}{dominio}/"


class Sito:
    def __init__(self, url: str):
        self.url = url.rstrip("/") + "/"
        self.token: str | None = None
        self.account: dict = {}
        # quando scade il token: un'ora dall'ultima chiamata andata a buon fine; None se non si sa ( demo )
        self.scade: float | None = None
        self.ultima_chiamata = 0.0
        # chiamato a ogni 401, anche da un thread: la TUI lo usa per tornare subito al login
        self.su_scaduta = None
        self._file = CACHE / (hashlib.sha1(self.url.encode()).hexdigest()[:12] + ".json")

    # --- sessione in cache, cosi' non si rifa' il login a ogni avvio

    def riprendi(self) -> bool:
        try:
            d = json.loads(self._file.read_text())
        except (OSError, ValueError):
            return False
        if d.get("scade", 0) < time.time():
            return False
        self.token, self.account = d["token"], d["account"]
        return True

    def _salva(self, **extra):
        CACHE.mkdir(parents=True, exist_ok=True)
        try:
            d = json.loads(self._file.read_text())
        except (OSError, ValueError):
            d = {}
        d.update(extra)
        self._file.write_text(json.dumps(d))
        self._file.chmod(0o600)

    def esci(self):
        self._file.unlink(missing_ok=True)
        self.token = None

    # --- chiamate

    def _post(self, percorso: str, dati: dict | None = None) -> dict:
        h = {"gliswebAuthKey": self.token} if self.token else {}
        try:
            r = requests.post(self.url + percorso, json=dati or {}, headers=h, timeout=20)
        except requests.RequestException as e:
            raise ErroreApi(f"il sito non risponde: {e}")
        try:
            d = r.json()
        except ValueError:
            if r.status_code == 403:
                # la pagina "accesso negato" di ModSecurity sul server: un testo gli e' sembrato un attacco
                raise ErroreApi("il firewall del sito ha rifiutato i dati ( ModSecurity ): di solito e' un testo "
                                "che somiglia a un attacco, prova a cambiarlo")
            raise ErroreApi(f"{percorso}: risposta non JSON ( HTTP {r.status_code} )")
        if r.status_code == 401 and percorso != "api/login":
            self.token, self.scade = None, 0.0
            if self.su_scaduta:
                self.su_scaduta()
            raise SessioneScaduta(d.get("err") or "sessione scaduta")
        if r.status_code >= 400 or d.get("status") == "KO":
            raise ErroreApi(d.get("err") or f"HTTP {r.status_code}")
        if self.token:
            # ogni chiamata autenticata riporta il token a un'ora ( _cli.php riscrive la chiave su Redis )
            self.ultima_chiamata = time.time()
            self.scade = self.ultima_chiamata + DURATA_TOKEN
        return d

    def carica_file(self, locale: str | Path, cartella: str = "var/contenuti/", pezzo: int = 1 << 20) -> str:
        """Carica un file su api/upload, a pezzi come l'uploader del framework, e ritorna il
        percorso sul sito ( p.es. var/contenuti/x.png ). Se il nome c'e' gia' il server lo
        rinomina in nome.<timestamp>.ext: vale il percorso ritornato, non il nome locale."""
        p = Path(locale).expanduser()
        try:
            dati = p.read_bytes()
        except OSError as e:
            raise ErroreApi(f"file non leggibile: {e}")
        if not dati:
            raise ErroreApi("file vuoto")
        pezzi = [dati[i:i + pezzo] for i in range(0, len(dati), pezzo)]
        d: dict = {}
        for n, blocco in enumerate(pezzi):
            # i pezzi vanno da 0 a n-1 e X-Chunk-Total e' l'indice dell'ultimo: il server unisce quando coincidono
            h = {"gliswebAuthKey": self.token or "", "Content-Type": "application/octet-stream",
                 "X-File-Name": p.name, "X-File-Size": str(len(dati)), "X-Target-Folder": cartella,
                 "X-Chunk-Number": str(n), "X-Chunk-Total": str(len(pezzi) - 1)}
            try:
                r = requests.post(self.url + "api/upload", data=blocco, headers=h, timeout=60)
                d = r.json()
            except requests.RequestException as e:
                raise ErroreApi(f"il sito non risponde: {e}")
            except ValueError:
                raise ErroreApi(f"api/upload: risposta non JSON ( HTTP {r.status_code} )")
            if r.status_code == 401:
                self.token, self.scade = None, 0.0
                if self.su_scaduta:
                    self.su_scaduta()
                raise SessioneScaduta("sessione scaduta")
            if r.status_code >= 400 or d.get("error"):
                raise ErroreApi("; ".join(d.get("error") or []) or f"HTTP {r.status_code}")
        if not d.get("filePath"):
            raise ErroreApi("api/upload: nessun percorso nella risposta")
        return d["filePath"]

    def login(self, utente: str, password: str) -> dict:
        d = self._post("api/login", {"__login__": {"user": utente, "pasw": password}})
        self.token = d.pop("token", None)
        if not self.token:
            raise ErroreApi("login riuscito ma senza token")
        self.account = d
        self.ultima_chiamata = time.time()
        self.scade = self.ultima_chiamata + DURATA_TOKEN
        self._salva(token=self.token, account=d, scade=time.time() + DURATA_TOKEN)
        return d

    def rinnova(self) -> None:
        """Solo per tenere vivo il token mentre si lavora: api/cli con "rinnova", niente menu."""
        self._post("api/cli", {"rinnova": True})

    def struttura(self) -> dict:
        """Account e menu di amministrazione dell'utente ( api/cli, vedi dev/server/_cli.php )."""
        d = self._post("api/cli")
        self._salva(struttura=d)
        return d

    def pagina(self, id: str, view: dict | None = None, record: dict | None = None,
               salva: dict | None = None, elimina: bool = False) -> dict:
        """Una pagina ( api/cli con "pagina" ): per una vista colonne, righe e pager, e view e' il __view__ di
        glisweb; per un form record e' {"tabella": ..., "id": ...} e torna record, tendine e schede; con salva
        ( {campo: valore} ) il record si scrive prima, e torna gia' riletto, con l'esito in form.salvato; con
        elimina si cancella, l'esito in form.eliminato. Senza id in record il form e' vuoto, e salva inserisce."""
        dati = {"pagina": id, "__view__": view or {}}
        if record:
            dati["record"] = record
        if salva is not None:
            dati["salva"] = salva
        if elimina:
            dati["elimina"] = True
        return self._post("api/cli", dati)


# --- configserver: dal codice deploy al sito, poi i profili locali per andare diretti


def profili() -> dict:
    """{"ultimo": codice, "deploy": {codice: {"url", "utente"}}}"""
    try:
        d = json.loads(PROFILI.read_text())
    except (OSError, ValueError):
        d = {}
    d.setdefault("deploy", {})
    return d


def salva_profilo(codice: str, url: str, utente: str):
    d = profili()
    d["deploy"][codice] = {"url": url, "utente": utente}
    d["ultimo"] = codice
    PROFILI.parent.mkdir(parents=True, exist_ok=True)
    PROFILI.write_text(json.dumps(d, indent=2))
    PROFILI.chmod(0o600)


def sito_del_profilo(codice: str | None = None) -> Sito | None:
    """Il sito dell'ultimo profilo usato ( o di quello col codice dato ), se c'e'."""
    d = profili()
    p = d["deploy"].get(codice or d.get("ultimo") or "")
    return Sito(p["url"]) if p else None


def accedi(codice: str, utente: str, password: str) -> Sito:
    """Login a tre campi. Un codice gia' noto va diretto al deploy; se il deploy non risponde,
    o il codice e' nuovo, si chiede al configserver, che da' solo OK o KO."""
    codice = codice.strip().lower()
    p = profili()["deploy"].get(codice)
    if p:
        sito = Sito(p["url"])
        try:
            sito.login(utente, password)
            salva_profilo(codice, sito.url, utente)
            return sito
        except ErroreApi as e:
            if not str(e).startswith("il sito non risponde"):
                raise
    try:
        r = requests.post(CONFIGSERVER, json={"codice": codice, "user": utente, "pasw": password}, timeout=30)
        d = r.json()
    except requests.RequestException as e:
        raise ErroreApi(f"il configserver non risponde: {e}")
    except ValueError:
        raise ErroreApi(f"configserver: risposta non JSON ( HTTP {r.status_code} )")
    if d.get("status") != "OK" or not d.get("token") or not d.get("url"):
        raise ErroreApi("codice, utente o password errati")
    sito = Sito(d["url"])
    sito.token, sito.account = d["token"], d.get("account") or {}
    sito.ultima_chiamata = time.time()
    sito.scade = sito.ultima_chiamata + DURATA_TOKEN
    sito._salva(token=sito.token, account=sito.account, scade=time.time() + DURATA_TOKEN)
    salva_profilo(codice, sito.url, utente)
    return sito

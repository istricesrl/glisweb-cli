"""L'interfaccia a schermate, in stile applicazione MS-DOS: login, poi dashboard con la barra dei menu in alto."""
from __future__ import annotations
from datetime import datetime
import html
import json
import re
import threading
import time

from textual import events, on, work
from textual.app import App, ComposeResult
from textual.actions import SkipAction
from textual.binding import Binding
from textual.containers import Center, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widget import Widget
from textual.suggester import Suggester
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

from . import api
from .api import ErroreApi, Sito

CSS = """
/* stile minimale: solo bianco, nero, grigio e grassetto; i campi sono righe di underscore */
* { scrollbar-background: #000000; scrollbar-background-hover: #000000; scrollbar-background-active: #000000;
    scrollbar-color: #aaaaaa; scrollbar-color-hover: #ffffff; scrollbar-color-active: #ffffff;
    scrollbar-corner-color: #000000; }
Screen { background: #000000; color: #ffffff; }
Static, Label { background: #000000; color: #ffffff; }

/* login */
#login { width: 46; height: auto; margin-top: 4; padding: 0; background: #000000; }
.riga { height: 1; margin-top: 1; }
.riga Label { width: 12; }
/* regola: le etichette dei campi sono sempre bianche e in grassetto */
Label.campo, .riga Label { color: #ffffff; text-style: bold; }
Input { width: 1fr; height: 1; padding: 0; border: none; background: #000000; color: #ffffff;
        text-style: none; }
Input:focus { border: none; background: #000000; text-style: none; }
Input > .input--cursor { background: #ffffff; color: #000000; text-style: none; }
Input > .input--placeholder { color: #ffffff; }
#login #errore { margin-top: 1; color: #ffffff; text-style: bold; }
#login Button { margin-top: 1; width: auto; min-width: 0; height: 1; padding: 0; border: none;
                background: #000000; color: #ffffff; text-style: none; }
#login Button:focus, #login Button:hover { background: #ffffff; color: #000000; text-style: none; }
#titolo-login { width: 100%; text-style: bold; }

/* barra dei menu */
#testa { dock: top; height: 4; }
#briciole { height: 1; padding: 0 1; margin: 1 0; background: #000000; color: #ffffff; }
#barra { height: 1; background: #ffffff; color: #000000; }
.voce-barra { width: auto; padding: 0 1; background: #ffffff; color: #000000; }
.voce-barra.attiva { background: #aaaaaa; color: #000000; }
#stato { dock: bottom; height: 1; background: #ffffff; color: #000000; padding: 0 1; }
#stato Static { background: #ffffff; color: #000000; }
#info { width: auto; }
#stato .spazio { width: 1fr; }
#orologio { width: auto; }
#stato Input#comando { width: 36; margin: 0 2; background: #aaaaaa; color: #000000; }
#stato Input#comando:focus { background: #aaaaaa; color: #000000; }
#stato Input#comando > .input--placeholder { color: #000000; }
#stato Input#comando > .input--suggestion { color: #555555; }
#corpo { padding: 1 2; }
Dashboard { layers: base sopra; }
#suggerimenti { layer: sopra; position: absolute; display: none; width: 36; height: auto;
                background: #aaaaaa; color: #000000; }

/* tendine */
Tendina { background: transparent; }
Scatola, Ombra { position: absolute; }
Ombra { background: #555555; }

/* vista: tabella delle righe */
Vista { height: 1fr; }
#vista-titolo { height: 1; padding: 0 1; text-style: bold; }
#vista-cerca { height: 1; padding: 0 1; margin-bottom: 1; }
#vista-cerca Label { width: auto; }
#vista-piede { height: 1; padding: 0 1; margin: 1 0; color: #aaaaaa; }
#vista-piede:focus { background: #ffffff; color: #000000; }
DataTable { height: 1fr; background: #000000; color: #ffffff; scrollbar-size: 1 1; }
DataTable > .datatable--header { background: #000000; color: #ffffff; text-style: bold underline; }
DataTable > .datatable--cursor { background: #ffffff; color: #000000; }
DataTable > .datatable--hover { background: #ffffff; color: #000000; text-style: none; }
DataTable > .datatable--header-hover { background: #000000; }
DataTable > .datatable--even-row { background: #000000; }
DataTable > .datatable--odd-row { background: #1a1a1a; }

/* form: righe di campi, l'etichetta sopra il campo */
Form { height: 1fr; padding: 1 2; }
#form-schede { height: 2; margin-bottom: 1; color: #aaaaaa; border-bottom: solid #ffffff; }
#form-schede:focus { text-style: bold; }
/* campi e figli scorrono fra le schede e il piede, che restano fermi; il campo col fuoco si porta in vista da se' */
#form-corpo { height: 1fr; scrollbar-size-vertical: 1; padding-right: 1; }
#form-campi { height: auto; }
.form-riga { height: auto; margin-bottom: 1; }
.form-campo { width: 1fr; height: auto; margin-right: 2; }
.form-campo Label { height: 1; }
Scelta { height: 1; background: #000000; color: #ffffff; }
Scelta:focus { background: #ffffff; color: #000000; }
TextArea { height: 3; border: none; padding: 0; background: #1a1a1a; color: #ffffff; }
TextArea:focus { border: none; }
TextArea > .text-area--cursor-line { background: #1a1a1a; }
/* sottotabelle ( mail, telefoni ): una riga per record, senza etichette sopra ogni campo */
.sub-titolo { height: 1; text-style: bold; }
.form-sub, .form-sub-testa { height: 1; }
.form-sub > *, .form-sub-testa > Label { width: 1fr; margin-right: 2; }
.form-sub-testa > Label { color: #aaaaaa; }
.sub-fine { height: 1; }
.form-sub > .sub-piu, .form-sub-testa > .sub-piu { width: 3; margin-right: 0; }
Piu:focus { background: #ffffff; color: #000000; }
#form-figli { height: auto; color: #aaaaaa; margin-top: 1; }
#form-fondo { dock: bottom; height: auto; }
#form-stato { height: 1; color: #ffffff; }
/* l'etichetta di un campo rifiutato dal server: in negativo, col motivo */
Label.errore { background: #ffffff; color: #000000; text-style: bold; }
/* se il terminale e' stretto l'aiuto va a capo invece di tagliarsi */
#form-piede { height: auto; color: #aaaaaa; }
"""


def _etichetta(v: dict) -> str:
    for k in ("label", "title"):
        e = v.get(k)
        if isinstance(e, dict):  # sui deploy veri le etichette sono per lingua: {"it-IT": "..."}
            e = e.get("it-IT") or next(iter(e.values()), None)
        if e:
            return str(e)
    return v.get("id") or "?"


def percorso(menu: list[dict], id: str) -> list[dict]:
    """Le voci del menu dalla radice fino alla pagina id, per le briciole di pane; vuoto se non c'e'."""
    for v in menu or []:
        if v.get("id") == id:
            return [v]
        sotto = percorso(v.get("content") or [], id)
        if sotto:
            return [v, *sotto]
    return []


TIPI = {".view.twig": "V", ".form.twig": "F", ".tools.twig": "T"}


# i comandi del campo Ctrl+K che non aprono una pagina
SPECIALI = {"ESCI": "esce da glisweb-cli", "QUIT": "esce da glisweb-cli"}


def comandi_rapidi(menu: list[dict]) -> dict[str, dict]:
    """I comandi rapidi del campo Ctrl+K: una lettera per il tipo di pagina ( V vista, F form, T tools,
    P il resto, N la vista aperta sul form vuoto d'inserimento ) e le prime quattro lettere dell'etichetta che si vede nel menu, p.es. anagrafica -> VANAG.
    Se il codice e' gia' preso, tre lettere dell'etichetta e l'iniziale dell'id ( listini di acquisti e
    di catalogo: VLISA, VLISC ), e se e' preso anche quello un numero in fondo."""
    out: dict[str, dict] = {}

    def lettere(x: str) -> str:
        return re.sub(r"[^A-Z0-9]", "", x.upper())

    def giro(voci):
        for v in voci or []:
            sch = v.get("schema") or ""
            if v.get("id") and sch and v["id"] not in {x["id"] for x in out.values()}:
                t = next((c for suf, c in TIPI.items() if sch.endswith(suf)), "P")
                et = lettere(_etichetta(v)) or lettere(v["id"]) or "X"
                c = t + et[:4]
                if c in out:
                    c = t + et[:3] + lettere(v["id"])[:1]
                n, base = 2, c
                while c in out:
                    c, n = f"{base}{n}", n + 1
                out[c] = v
                # ogni vista ha anche il suo N: la stessa pagina, che si apre sul form vuoto ( NANAG )
                if t == "V" and "N" + c[1:] not in out:
                    out["N" + c[1:]] = {**v, "__nuovo__": True}
            giro(v.get("content"))
    giro(menu)
    return out


class SuggerisciComando(Suggester):
    """Autocompletamento del campo comandi: il primo codice che comincia con quello scritto."""

    def __init__(self, comandi: dict[str, dict]):
        super().__init__(use_cache=False, case_sensitive=False)
        self.comandi = comandi

    async def get_suggestion(self, value: str) -> str | None:
        for c in sorted(self.comandi):
            if value and c.startswith(value.upper()):
                return value + c[len(value):]
        return None


class Comando(Input):
    """Il campo grigio del piede ( Ctrl+K ): Invio esegue, Esc torna dove si era, destra completa."""
    BINDINGS = [Binding("escape", "esci", show=False), Binding("up", "scorri(-1)", show=False),
                Binding("down", "scorri(1)", show=False)]
    # si raggiunge solo con Ctrl+K: se fosse focalizzabile, all'avvio prenderebbe il fuoco ( cursore
    # nel piede ) e si mangerebbe gli alt+lettera del menu
    can_focus = False

    def on_key(self, ev):
        # alt+lettera anche da qui: si lascia il campo e il tasto sale alla Dashboard, che apre il menu
        if ev.key.startswith("alt+") and len(ev.key) == 5:
            self.value = ""
            self.screen.lascia_comando()

    def action_esci(self):
        self.value = ""
        self.screen.lascia_comando()

    def action_scorri(self, d: int):
        self.screen.scorri_suggerimenti(d)


def voci_barra(menu: list[dict]) -> list[dict]:
    """Il primo livello del menu admin va nella barra. Se c'e' una sola radice ( p.es. la dashboard ),
    nella barra vanno lei e i suoi figli. Da verificare sulla struttura vera del deploy."""
    if len(menu) == 1 and menu[0].get("content"):
        radice = dict(menu[0], content=[])
        return [radice, *menu[0]["content"]]
    return menu


def scegli_hotkey(etichette: list[str]) -> list[str | None]:
    """Una lettera per voce, la prima libera dell'etichetta ( come i menu DOS )."""
    usate: list[str | None] = []
    for e in etichette:
        usate.append(next((c for c in e.lower() if c.isalnum() and c not in usate), None))
    return usate


def _con_hotkey(etichetta: str, lettera: str | None) -> Text:
    t = Text(etichetta)
    if lettera:
        i = etichetta.lower().find(lettera)
        t.stylize("underline", i, i + 1)
    return t


def _nel_form(w: Widget) -> bool:
    return any(isinstance(a, Form) for a in w.ancestors)


def _alle_schede(w: Widget) -> bool:
    """Freccia su da un campo del form: il fuoco va alla riga delle schede, se il form ne ha."""
    f = next((a for a in w.ancestors if isinstance(a, Form)), None)
    if f is None or not f.schede:
        return False
    f.query_one("#form-schede").focus()
    return True


def _in_verticale(w: Widget, d: int) -> bool:
    """Frecce su e giu' nel form: il fuoco va al campo della riga sopra ( d=-1 ) o sotto ( d=1 ), quello piu'
    vicino in orizzontale. Torna False se in quella direzione non ci sono campi."""
    f = next((a for a in w.ancestors if isinstance(a, Form)), None)
    if f is None:
        return False
    box = f.query_one("#form-campi")

    def pos(c):
        # la posizione dentro #form-campi, anche fuori schermo: virtual_region e' relativa al genitore
        x = y = 0
        while c is not box and c is not None:
            x, y = x + c.virtual_region.x, y + c.virtual_region.y
            c = c.parent
        return y, x
    campi = {c: pos(c) for c in f.query("#form-campi Campo, #form-campi Scelta, #form-campi Testo") if c.display}
    y0, x0 = pos(w)
    righe = [y for y, _ in campi.values() if (y - y0) * d > 0]
    if not righe:
        return False
    y = min(righe) if d > 0 else max(righe)
    c = min((c for c, p in campi.items() if p[0] == y), key=lambda c: abs(campi[c][1] - x0))
    c.focus()
    if isinstance(c, Campo):
        c.call_after_refresh(setattr, c, "cursor_position", min(w.cursor_position, len(c.value))
                             if isinstance(w, Campo) else len(c.value))
    return True


def _valore(w) -> str:
    """Il valore di un campo del form come lo manda il form web: stringa, vuoto per nessun valore."""
    if isinstance(w, (Scelta, Ricerca)):
        return "" if w.valore in (None, "-", "None") else w.valore
    if isinstance(w, TextArea):
        return w.text
    return w.value


class Campo(Input):
    """Un Input il cui spazio vuoto si disegna con underscore, come un modulo su carta. Nei form le frecce
    destra e sinistra, arrivate in fondo o in cima al testo, passano al campo dopo o a quello prima; su e giu'
    vanno al campo della riga sopra o sotto, e dalla prima riga su porta alle schede."""
    BINDINGS = [Binding("up", "su", show=False), Binding("down", "giu", show=False)]

    def __init__(self, *a, **kw):
        # il contenuto non si seleziona entrando: un tasto battuto per sbaglio lo cancellerebbe tutto
        kw.setdefault("select_on_focus", False)
        super().__init__(*a, **kw)

    def _vai(self, avanti: bool):
        """Al campo dopo col cursore in testa, o a quello prima col cursore in fondo."""
        w = self.screen.focus_next() if avanti else self.screen.focus_previous()
        if isinstance(w, Campo):
            w.call_after_refresh(setattr, w, "cursor_position", 0 if avanti else len(w.value))

    def action_su(self):
        if not _nel_form(self):
            raise SkipAction()  # fuori dal form ( login ) la freccia su resta a chi sta sopra
        _in_verticale(self, -1) or _alle_schede(self)

    def action_giu(self):
        # nel form si scende al campo sotto; in fondo ci si ferma, non si torna alla dashboard
        if not _nel_form(self):
            raise SkipAction()
        _in_verticale(self, 1)

    def action_cursor_left(self, select: bool = False):
        if not select and self.cursor_position == 0 and _nel_form(self):
            self._vai(False)
        else:
            super().action_cursor_left(select)

    def action_cursor_right(self, select: bool = False):
        if not select and self.cursor_position >= len(self.value) and not self._suggestion and _nel_form(self):
            self._vai(True)
        else:
            super().action_cursor_right(select)

    def render_line(self, y: int) -> Strip:
        riga = super().render_line(y)
        pieno = len(self.value) - int(self.scroll_offset.x) + (1 if self.has_focus else 0)
        pieno = max(0, min(pieno, riga.cell_length))
        resto = Strip([Segment(seg.text.replace(" ", "_"), seg.style, seg.control) for seg in riga.crop(pieno)])
        return Strip.join([riga.crop(0, pieno), resto])


# colori delle tendine: (testo, sfondo)
# tavolozza dell'intera app: bianco, nero, grigio ( #aaaaaa, e #555555 per le ombre ) e grassetto
NORMALE = Style(color="#000000", bgcolor="#aaaaaa")
SCELTA = Style(color="#ffffff", bgcolor="#000000")
CHIARA = Style(color="#000000", bgcolor="#ffffff")  # la tendina di un campo del form: bianca come il campo evidenziato
LETTERA = Style(bold=True, underline=True)


class Scatola(Widget):
    """La tendina alla Turbo Vision: cornice a linea singola, uno spazio ai lati, lettera rapida, ► per i sottomenu."""

    def __init__(self, voci: list[dict], hotkey: list[str | None], chiara: bool = False):
        super().__init__()
        self.voci, self.hotkey = voci, hotkey
        # righe: le voci che si vedono, se lo schermo non le contiene tutte; cima: la prima di quelle
        self.righe, self.cima, self._scelta = len(voci), 0, 0
        self.fondo = CHIARA if chiara else NORMALE
        self.interna = max([10] + [cell_len(_etichetta(v)) + (2 if v.get("content") else 0) + 2 for v in voci])

    @property
    def larghezza(self) -> int:
        return self.interna + 2

    @property
    def scelta(self) -> int:
        return self._scelta

    @scelta.setter
    def scelta(self, i: int):
        # la voce scelta resta sempre fra quelle visibili
        self._scelta = i
        self.cima = min(max(self.cima, i - self.righe + 1), i)

    def render_line(self, y: int) -> Strip:
        n = self.righe
        if y == 0:
            return Strip([Segment("┌" + "─" * self.interna + "┐", self.fondo)])
        if y == n + 1:
            return Strip([Segment("└" + "─" * self.interna + "┘", self.fondo)])
        if y > n + 1:
            return Strip.blank(self.larghezza)
        i = self.cima + y - 1
        v, stile = self.voci[i], (SCELTA if i == self.scelta else self.fondo)
        testo = _etichetta(v)
        freccia = "►" if v.get("content") else ""
        riga = Text(" " + testo, style=stile)
        lettera = self.hotkey[i]
        if lettera:
            k = testo.lower().find(lettera) + 1
            riga.stylize(LETTERA, k, k + 1)
        riga.append(" " * (self.interna - 1 - cell_len(testo) - len(freccia) - 1) + freccia + " ", stile)
        segs = [Segment("│", self.fondo), *riga.render(self.app.console), Segment("│", self.fondo)]
        return Strip([sg for sg in segs if sg.text != "\n"])

    def on_click(self, ev):
        i = self.cima + ev.y - 1
        if 0 < ev.y <= self.righe and i < len(self.voci):
            self.scelta = i
            self.refresh()
            self.screen.action_invio()


class Ombra(Widget):
    def render(self) -> str:
        return ""


def voci_tendina(v: dict) -> list[dict]:
    """Le voci della tendina di v: se v e' anche una pagina ( in glisweb anagrafica e' anagrafica.view, con
    figli account e archivio ), la pagina stessa va per prima, se no dal menu non la si apre."""
    figli = list(v.get("content") or [])
    if v.get("schema"):
        figli.insert(0, {**v, "content": []})
    return figli


class Tendina(ModalScreen):
    """Un menu a tendina; le voci con figli aprono una tendina a fianco."""

    BINDINGS = [
        Binding("escape", "chiudi", "chiudi"),
        Binding("left", "sinistra", show=False),
        Binding("right", "destra", show=False),
        Binding("up", "muovi(-1)", show=False),
        Binding("down", "muovi(1)", show=False),
        Binding("enter", "invio", show=False),
    ]

    def __init__(self, voci: list[dict], x: int, y: int, primo_livello: bool = True, chiara: bool = False):
        super().__init__()
        self.voci, self.x, self.y, self.primo_livello, self.chiara = voci, x, y, primo_livello, chiara
        self.hotkey = scegli_hotkey([_etichetta(v) for v in voci])

    def compose(self) -> ComposeResult:
        sc = Scatola(self.voci, self.hotkey, self.chiara)
        # self.y e' la riga sotto il campo: se la tendina li' non ci sta, si apre sopra il campo; se non ci
        # sta da nessuna parte, va dove c'e' piu' posto e le voci scorrono
        alto = self.app.size.height
        h = len(self.voci) + 2
        sotto_libero, sopra_libero = alto - self.y - 1, self.y - 1
        self.su = h > sotto_libero and sopra_libero > sotto_libero
        if h > max(sotto_libero, sopra_libero):
            h = max(3, max(sotto_libero, sopra_libero))
            sc.righe = h - 2
        if self.su:
            self.y = max(0, self.y - 1 - h)
        w = sc.larghezza
        sc.styles.width, sc.styles.height, sc.styles.offset = w, h, (self.x, self.y)
        destra, sotto = Ombra(), Ombra()
        destra.styles.width, destra.styles.height, destra.styles.offset = 2, h, (self.x + w, self.y + 1)
        sotto.styles.width, sotto.styles.height, sotto.styles.offset = w, 1, (self.x + 2, self.y + h)
        yield destra
        yield sotto
        yield sc

    @property
    def scatola(self) -> Scatola:
        return self.query_one(Scatola)

    def _corrente(self) -> dict:
        return self.voci[self.scatola.scelta]

    def _apri_figlia(self, v: dict):
        sc = self.scatola
        self.app.push_screen(Tendina(voci_tendina(v), self.x + sc.larghezza - 1, self.y + sc.scelta - sc.cima + 1, False, self.chiara),
                             lambda r: r is not None and self.dismiss(r))

    def action_muovi(self, d: int):
        sc = self.scatola
        # nelle tendine dei form la freccia verso il campo dalla voce piu' vicina chiude, come Esc ( nei menu della
        # barra gira in fondo ): su dalla prima se la tendina e' sotto il campo, giu' dall'ultima se e' sopra
        if self.chiara and (d > 0 and sc.scelta == len(self.voci) - 1 if self.su else d < 0 and sc.scelta == 0):
            self.dismiss(None)
            return
        sc.scelta = (sc.scelta + d) % len(self.voci)
        sc.refresh()

    def action_invio(self):
        v = self._corrente()
        if v.get("content"):
            self._apri_figlia(v)
        else:
            self.dismiss(v)

    def action_destra(self):
        v = self._corrente()
        if v.get("content"):
            self._apri_figlia(v)
        elif self.primo_livello:
            self.dismiss(">")

    def action_sinistra(self):
        self.dismiss("<" if self.primo_livello else None)

    def action_chiudi(self):
        self.dismiss(None)

    def on_key(self, ev):
        # alt+lettera con una tendina aperta: si passa a quel menu della barra
        if ev.key.startswith("alt+") and len(ev.key) == 5:
            ev.stop()
            self.dismiss(ev.key)
        # lettera semplice: la voce con quella lettera rapida
        elif ev.character and len(ev.key) == 1 and ev.key.lower() in self.hotkey:
            ev.stop()
            self.scatola.scelta = self.hotkey.index(ev.key.lower())
            self.scatola.refresh()
            self.action_invio()

    def on_click(self, ev):
        # click fuori dalla tendina: si chiude
        if ev.widget is self:
            self.dismiss(None)


class Login(Screen):
    BINDINGS = [Binding("escape", "app.quit", "esci")]

    def __init__(self, avviso: str = ""):
        super().__init__()
        # dopo una scadenza: il motivo, e la password non si ripropone ( chi passa non deve poter rientrare )
        self.avviso = avviso

    def compose(self) -> ComposeResult:
        with Center():
            with Vertical(id="login"):
                yield Static("glisweb-cli", id="titolo-login")
                prof = api.profili() if self.app.remoto else {}
                ultimo = self.app.codice or prof.get("ultimo") or ""
                utente = self.app.preset.get("utente") or (prof.get("deploy", {}).get(ultimo) or {}).get("utente", "")
                if self.app.remoto:
                    with Horizontal(classes="riga"):
                        yield Label("codice")
                        yield Campo(ultimo, id="codice")
                else:
                    yield Static(self.app.sito.url)
                with Horizontal(classes="riga"):
                    yield Label("utente")
                    yield Campo(utente, id="utente")
                with Horizontal(classes="riga"):
                    yield Label("password")
                    yield Campo("" if self.avviso else self.app.preset.get("password", ""), id="password", password=True)
                yield Label(self.avviso, id="errore")
                yield Button(r"\[ Entra ]", id="entra")

    def on_mount(self):
        # col profilo gia' compilato si parte dalla password
        if (self.app.remoto or self.avviso) and self.query_one("#utente", Input).value:
            self.query_one("#password").focus()
        # niente autologin: il preset compila soltanto, cosi' si puo' cambiare codice o utente

    @on(Input.Submitted, "#codice")
    def _vai_utente(self):
        self.query_one("#utente").focus()

    @on(Input.Submitted, "#utente")
    def _vai_password(self):
        self.query_one("#password").focus()

    @on(Input.Submitted, "#password")
    @on(Button.Pressed, "#entra")
    def _entra(self):
        c = self.query_one("#codice", Input).value.strip() if self.app.remoto else ""
        u = self.query_one("#utente", Input).value.strip()
        p = self.query_one("#password", Input).value
        if u and p and (c or not self.app.remoto):
            self.query_one("#errore", Label).update("accesso in corso...")
            self._login(c, u, p)

    @work(thread=True, exclusive=True)
    def _login(self, codice: str, utente: str, password: str):
        try:
            if self.app.remoto:
                self.app.sito = api.accedi(codice, utente, password)
            else:
                self.app.sito.login(utente, password)
            s = self.app.sito.struttura()
        except ErroreApi as e:
            self.app.call_from_thread(self.query_one("#errore", Label).update, str(e))
            return
        self.app.call_from_thread(self.app.apri_dashboard, s)


class Dashboard(Screen):
    sugg: list = []
    sugg_i: int | None = None
    BINDINGS = [
        Binding("left", "muovi(-1)", show=False),
        Binding("right", "muovi(1)", show=False),
        Binding("enter,down", "apri", show=False),
        Binding("escape", "app.quit", "esci"),
        Binding("ctrl+k", "comando", "comando", show=False, priority=True),
    ]

    def __init__(self, struttura: dict):
        super().__init__()
        self.struttura = struttura
        self.voci = voci_barra(struttura.get("menu", {}).get("admin", []))
        self.indice = 0
        self.hotkey = scegli_hotkey([_etichetta(v) for v in self.voci])
        self.comandi = comandi_rapidi(struttura.get("menu", {}).get("admin", []))

    def compose(self) -> ComposeResult:
        with Vertical(id="testa"):
            yield Static(id="briciole")
            with Horizontal(id="barra"):
                for i, v in enumerate(self.voci):
                    yield Static(_con_hotkey(_etichetta(v), self.hotkey[i]), classes="voce-barra", id=f"barra-{i}")
        yield Static("Alt + la lettera sottolineata apre il menu, frecce per muoversi, Invio per scegliere, "
                     "Esc per chiudere.\nCtrl+K: comando rapido ( p.es. VANAG apre la vista anagrafica ).", id="corpo")
        with Horizontal(id="stato"):
            yield Static(self._info(), id="info")
            yield Static(classes="spazio")
            yield Comando(placeholder="Ctrl+K", suggester=SuggerisciComando(self.comandi), id="comando")
            yield Static(classes="spazio")
            yield Static(id="orologio")
        yield Static(id="suggerimenti")

    def _info(self) -> str:
        acc = self.struttura.get("account", {})
        return f"{acc.get('username', '?')}  ·  {self.app.sito.url}  ·  glisweb {self.struttura.get('version') or '?'}"

    def action_comando(self):
        # Ctrl+K fa da interruttore: col campo attivo lo svuota e lo spegne
        c = self.query_one("#comando", Comando)
        if self.app.focused is c:
            c.value = ""
            self.lascia_comando()
            return
        c.can_focus = True
        c.focus()

    def lascia_comando(self):
        # si torna alla tabella della vista aperta, se c'e'
        self.query_one("#comando", Comando).can_focus = False
        self._suggerisci([])
        t = self.query("#tabella")
        if t:
            t.first().focus()
        else:
            self.set_focus(None)

    def _suggerisci(self, righe: list[str], scelta: int | None = None):
        """La tendina dei suggerimenti, che sale dal campo comandi: il piede resta fermo."""
        self.sugg, self.sugg_i = righe, scelta
        w = self.query_one("#suggerimenti", Static)
        if not righe:
            w.display = False
            return
        t = Text()
        for n, x in enumerate(righe):
            t.append(f" {x} ".ljust(36)[:36] + ("\n" if n < len(righe) - 1 else ""),
                     style="reverse" if n == scelta else "")
        w.update(t)
        c = self.query_one("#comando", Comando)
        w.styles.offset = (c.region.x, c.region.y - len(righe))
        w.display = True

    def scorri_suggerimenti(self, d: int):
        # su e giu' nel campo: si sceglie fra i suggerimenti ( che sono codici solo se c'e' un codice )
        codici = [x.split()[0] for x in self.sugg if x.split() and (x.split()[0] in self.comandi or x.split()[0] in SPECIALI)]
        if not codici:
            return
        i = len(codici) - 1 if self.sugg_i is None else (self.sugg_i + d) % len(codici)
        self._suggerisci(self.sugg, i)

    @on(Input.Changed, "#comando")
    def _comando_cambiato(self, ev):
        x = ev.value.strip().upper()
        if not x:
            self._suggerisci([])
            return
        trovati = [f"{c} {_etichetta(v)}" for c, v in sorted(self.comandi.items()) if c.startswith(x)]
        trovati += [f"{c} {e}" for c, e in SPECIALI.items() if c.startswith(x)]
        self._suggerisci(trovati[:12] or ["nessun comando"])

    @on(Input.Submitted, "#comando")
    def _comando_invio(self, ev):
        x = ev.value.strip().upper()
        if self.sugg_i is not None:
            # scelto con le frecce nella tendina
            x = self.sugg[self.sugg_i].split()[0]
        if x in SPECIALI:
            self.app.exit()
            return
        trovati = [c for c in sorted(self.comandi) if c.startswith(x)] if x else []
        # il codice esatto, oppure l'unico che comincia cosi'
        c = x if x in self.comandi else (trovati[0] if len(trovati) == 1 else None)
        if not c:
            self._suggerisci([f"{x}: comando sconosciuto"] if not trovati else
                             [f"{c} {_etichetta(self.comandi[c])}" for c in trovati[:12]])
            return
        ev.input.value = ""
        self.lascia_comando()
        self.mostra(self.comandi[c])

    def briciole(self, v: dict | None = None, coda: str | None = None):
        # riga nera sopra il menu: il percorso della pagina aperta, dalla radice; coda la aggiunge
        # chi sta dentro la pagina ( il form: record e scheda ) senza cambiare la voce di menu
        if coda is None:
            self.voce = v
        else:
            v = getattr(self, "voce", None)
        voci = percorso(self.struttura.get("menu", {}).get("admin", []), v["id"]) if v else []
        if v and not voci:
            voci = [v]
        testo = " > ".join(_etichetta(x) for x in voci) or "home"
        self.query_one("#briciole", Static).update(testo + (f" > {coda}" if coda else ""))

    def on_mount(self):
        self.briciole()
        self._orologio()
        self.set_interval(1, self._orologio)

    def _orologio(self):
        # data e ora in basso a destra; i due punti lampeggiano ogni secondo, cosi' si vede che l'orologio va
        ora = datetime.now()
        sep = ":" if ora.second % 2 == 0 else " "
        self.query_one("#orologio", Static).update(ora.strftime(f"%d/%m/%Y %H{sep}%M"))

    def _evidenzia(self):
        for i, w in enumerate(self.query(".voce-barra")):
            w.set_class(i == self.indice, "attiva")

    def on_key(self, ev):
        # alt+lettera: apre il menu con quella lettera sottolineata
        if ev.key.startswith("alt+") and len(ev.key) == 5:
            lettera = ev.key[-1].lower()
            if lettera in self.hotkey:
                ev.stop()
                self.indice = self.hotkey.index(lettera)
                self.action_apri()

    def action_barra(self):
        self._evidenzia()
        self.action_apri()

    def action_muovi(self, d: int):
        if self.voci:
            self.indice = (self.indice + d) % len(self.voci)
            self._evidenzia()

    def action_apri(self):
        if not self.voci:
            return
        self._evidenzia()
        v = self.voci[self.indice]
        if not v.get("content"):
            self.mostra(v)
            return
        w = self.query_one(f"#barra-{self.indice}")
        self.app.push_screen(Tendina(voci_tendina(v), w.region.x, w.region.y + 1), self._dopo_tendina)

    def _dopo_tendina(self, r):
        if isinstance(r, str) and r.startswith("alt+"):
            lettera = r[-1].lower()
            if lettera in self.hotkey:
                self.indice = self.hotkey.index(lettera)
                self.action_apri()
        elif r in ("<", ">"):
            self.action_muovi(-1 if r == "<" else 1)
            self.action_apri()
        elif isinstance(r, dict):
            self.mostra(r)

    def on_click(self, ev):
        w = ev.widget
        if w is not None and w.id and w.id.startswith("barra-"):
            self.indice = int(w.id.split("-")[1])
            self.action_apri()

    def mostra(self, v: dict):
        self.briciole(v)
        # le viste si aprono nel corpo, sotto la barra del menu, al posto della vista di prima
        for w in [*self.query(Vista), *self.query(Form)]:
            w.remove()
        corpo = self.query_one("#corpo", Static)
        if (v.get("schema") or "").endswith(".view.twig"):
            corpo.display = False
            self.mount(Vista(v, v.get("__nuovo__", False)), after=corpo)
            return
        corpo.display = True
        # TODO: qui si apre la pagina vera ( vista, form a schede, tools ) secondo lo schema
        loc = v.get("location") or {}
        self.query_one("#corpo", Static).update(
            f"[b]{_etichetta(v)}[/b]\n\npagina: {v.get('id')}\nschema: {v.get('schema') or '-'}\n"
            f"percorso: {next(iter(loc.values()), '-') if isinstance(loc, dict) else loc}")


def _testo(x) -> str:
    """Un valore di glisweb in testo semplice: i tag via, le entita' decodificate, una riga sola."""
    if x is None:
        return ""
    t = html.unescape(re.sub(r"<[^>]*>", "", str(x)))
    return " ".join(t.split())


def colonne_visibili(cols: dict, classi: dict) -> list:
    """Le colonne da mostrare: via quelle nascoste ( d-none, salvo d-md-table-cell ) e quelle senza titolo
    ( le azioni ); nomi, cognomi e denominazioni nascosti sono gia' dentro __label__."""
    out = []
    for k, titolo in (cols or {}).items():
        c = (classi or {}).get(k) or ""
        if not _testo(titolo) or k in ("", "NULL"):  # la colonna senza chiave ( NULL ) e' quella dei pulsanti
            continue
        if "d-none" in c.split() and "d-md-table-cell" not in c:
            continue
        out.append((k, _testo(titolo)))
    return out


ORDINI = [{"id": "ASC", "label": "crescente"}, {"id": "DESC", "label": "decrescente"}, {"id": "", "label": "nessuno"}]
FRECCE = {"ASC": " ▲", "DESC": " ▼"}


class Tabella(DataTable):
    """La DataTable della Vista, con la testata navigabile: freccia su dalla prima riga porta sui campi
    della testata, sinistra e destra scelgono il campo, Invio apre il menu dell'ordinamento,
    freccia su ancora va alla ricerca, freccia giu' torna alle righe."""

    testata: int | None = None
    BINDINGS = [Binding("home", "riga(0)", show=False), Binding("end", "riga(-1)", show=False)]

    def _on_mouse_move(self, ev):
        # il mouse sposta la barra del cursore, non ne disegna una seconda ( l'hover di DataTable )
        ev.prevent_default()
        meta = ev.style.meta or {}
        r = meta.get("row")
        if self.testata is None and isinstance(r, int) and 0 <= r < self.row_count and r != self.cursor_row:
            self.move_cursor(row=r)

    def action_riga(self, n: int):
        # Home alla prima riga, Fine all'ultima; anche dalla testata
        if self.testata is not None:
            self._testata(None)
        if self.row_count:
            self.move_cursor(row=n % self.row_count)

    @property
    def vista(self) -> "Vista":
        return self.query_ancestor(Vista)

    def _testata(self, i: int | None):
        self.testata = i
        self.show_cursor = i is None
        self.vista.disegna()

    def action_cursor_up(self):
        if self.testata is not None:
            self.vista.vai_ricerca()
        elif self.cursor_row <= 0 and self.columns:
            self._testata(0)
        else:
            super().action_cursor_up()

    def action_cursor_down(self):
        if self.testata is not None:
            self._testata(None)
        elif self.cursor_row >= self.row_count - 1:
            # dall'ultima riga si scende nel piede, a sfogliare le pagine
            self.vista.query_one("#vista-piede", Piede).focus()
        else:
            super().action_cursor_down()

    def action_cursor_left(self):
        if self.testata is not None:
            self._testata(max(0, self.testata - 1))
        else:
            super().action_cursor_left()

    def action_cursor_right(self):
        if self.testata is not None:
            self._testata(min(len(self.columns) - 1, self.testata + 1))
        else:
            super().action_cursor_right()

    def action_select_cursor(self):
        if self.testata is not None:
            self.vista.menu_ordine(self.testata)
        elif self.row_count:
            self.vista.apri_riga()


class Piede(Static, can_focus=True):
    """Il piede della Vista: freccia giu' dall'ultima riga ci arriva, sinistra e destra sfogliano
    le pagine, freccia su torna all'ultima riga della tabella."""
    BINDINGS = [Binding("left", "pagina(-1)", show=False), Binding("right", "pagina(1)", show=False),
                Binding("up", "su", show=False), Binding("home", "riga(0)", show=False),
                Binding("end", "riga(-1)", show=False)]

    def action_riga(self, n: int):
        t = self.query_ancestor(Vista).tabella
        t.focus()
        t.action_riga(n)

    def action_pagina(self, d: int):
        self.query_ancestor(Vista).action_pagina(d, fuoco=False)

    def action_su(self):
        t = self.query_ancestor(Vista).tabella
        t.focus()
        if t.row_count:
            t.move_cursor(row=t.row_count - 1)

    def on_focus(self):
        self.query_ancestor(Vista).scrivi_piede(True)

    def on_blur(self):
        self.query_ancestor(Vista).scrivi_piede(False)


class Vista(Vertical):
    """Una pagina *.view.twig dentro la Dashboard, sotto il menu: la riga di ricerca e la tabella delle righe,
    pagina per pagina come nel pager di glisweb, ordinabile dalla testata. Esc la chiude e torna al corpo."""
    BINDINGS = [
        Binding("pagedown,ctrl+right", "pagina(1)", "pagina dopo", show=False, priority=True),
        Binding("pageup,ctrl+left", "pagina(-1)", "pagina prima", show=False, priority=True),
        Binding("ctrl+f", "vai_ricerca", "cerca", show=False, priority=True),
        Binding("ctrl+n", "nuovo", "nuovo", show=False, priority=True),
        Binding("down", "giu", show=False),
        Binding("escape", "chiudi", "chiudi", show=False),
    ]

    def __init__(self, voce: dict, nuovo: bool = False):
        super().__init__()
        self.voce = voce
        self.nuovo = nuovo  # comando N...: alla prima lettura si apre il form vuoto
        self.vid = None
        self.pager = {"page": 0, "pages": 1, "total": 0}
        self.ordine: dict[str, str] = {}   # __sort__ di glisweb: campo -> ASC / DESC
        self.cerca = ""                    # __search__ di glisweb
        self.ultima: dict = {}
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Static("", id="vista-titolo")  # riga vuota: il nome sta gia' nelle briciole
        with Horizontal(id="vista-cerca"):
            yield Label("cerca: ", classes="campo")
            yield Input(id="ricerca")
        yield Tabella(cursor_type="row", zebra_stripes=True, id="tabella")
        yield Piede("carico...", id="vista-piede")

    def on_mount(self):
        self.carica(0)

    @property
    def tabella(self) -> Tabella:
        return self.query_one("#tabella", Tabella)

    def action_chiudi(self):
        # Esc dalla ricerca torna alla tabella; dalla tabella chiude la vista
        if self.query_one("#ricerca", Input).has_focus:
            self.tabella.focus()
            return
        self.screen.query_one("#corpo", Static).display = True
        self.screen.briciole()
        self.remove()

    def action_vai_ricerca(self):
        self.vai_ricerca()

    def vai_ricerca(self):
        t = self.tabella
        if t.testata is not None:
            t.testata, t.show_cursor = None, True
            self.disegna()
        self.query_one("#ricerca", Input).focus()

    def action_giu(self):
        # freccia giu' dalla ricerca: sulla testata
        if self.query_one("#ricerca", Input).has_focus and self.tabella.columns:
            self.tabella.focus()
            self.tabella._testata(0)

    @on(Input.Changed, "#ricerca")
    def _cambiata(self, ev):
        # si cerca da soli dopo mezzo secondo di pausa, o subito con Invio
        if self._timer:
            self._timer.stop()
        self._timer = self.set_timer(0.5, self._cerca)

    @on(Input.Submitted, "#ricerca")
    def _invio(self, ev):
        if self._timer:
            self._timer.stop()
        self._cerca()

    def _cerca(self):
        testo = self.query_one("#ricerca", Input).value.strip()
        if testo != self.cerca:
            self.cerca = testo
            self._stato("carico...")
            self.carica(0, False)

    def menu_ordine(self, i: int):
        t = self.tabella
        k = str(list(t.columns.keys())[i].value)
        # la tendina si apre sotto il campo della testata
        x = t.region.x - int(t.scroll_x) + sum(c.get_render_width(t) for c in list(t.columns.values())[:i])

        def scelto(o):
            if o is None:
                return
            self.ordine.pop(k, None)
            if o["id"]:
                self.ordine[k] = o["id"]
            self._stato("carico...")
            self.carica(0, False)
        self.app.push_screen(Tendina(ORDINI, x, t.region.y + 1, False), scelto)

    def _righe_schermo(self) -> int:
        # tante righe quante ne stanno: briciole con le due righe vuote attorno, barra del menu, riga vuota, ricerca e la riga vuota sotto,
        # intestazione, piede con le due righe vuote attorno, stato
        return max(5, self.app.size.height - 12)

    @work(thread=True, exclusive=True)
    def carica(self, page: int, fuoco: bool = True):
        self._carica(page, fuoco)

    def _view(self, page: int) -> dict:
        if not self.vid:
            return {}
        w = {"__pager__": {"page": page, "rows": self._righe_schermo()}}
        if self.ordine:
            w["__sort__"] = dict(self.ordine)
        if self.cerca:
            w["__search__"] = self.cerca
        return {self.vid: w}

    def _carica(self, page: int, fuoco: bool = True, giro: int = 0):
        try:
            d = self.app.sito.pagina(self.voce["id"], self._view(page))
        except ErroreApi as e:
            self.app.call_from_thread(self._stato, f"errore: {e}")
            return
        v = d.get("view") or {}
        # la prima chiamata non sa l'id della vista: lo impara e richiede con le righe giuste
        if not self.vid and v.get("id") and giro == 0:
            self.vid = v["id"]
            if int((v.get("pager") or {}).get("rows") or 0) != self._righe_schermo():
                return self._carica(page, fuoco, 1)
        self.app.call_from_thread(self._riempi, v, fuoco)

    def _riempi(self, v: dict, fuoco: bool = True):
        self.ultima = v
        self.disegna(riga=0)
        self.pager = v.get("pager") or self.pager
        self.scrivi_piede()
        if fuoco:
            self.tabella.focus()
        if self.nuovo:
            self.nuovo = False
            self._apri_form(None)

    def scrivi_piede(self, nel_piede: bool | None = None):
        p, v = self.pager, self.ultima
        n, m = int(p.get("page") or 0) + 1, int(p.get("pages") or 1)
        totale = f"{p.get('total') or len(v.get('data') or [])} righe"
        if nel_piede is None:
            nel_piede = self.query_one("#vista-piede", Piede).has_focus
        if nel_piede:
            # nel piede: le frecce mostrano dove si puo' andare
            self._stato(f"{'◄' if n > 1 else ' '} pagina {n} di {m} {'►' if n < m else ' '}  ·  {totale}"
                        f"  ·  sinistra/destra sfoglia, su torna alla tabella")
        else:
            self._stato(f"{v.get('table') or ''}  ·  pagina {n} di {m}  ·  {totale}  ·  PgSu/PgGiu' sfoglia,"
                        f" giu' in fondo va al piede, Ctrl+F cerca, Invio apre, Ctrl+N nuovo, Esc chiude")

    def disegna(self, riga: int | None = None):
        """Ridisegna la tabella dall'ultima risposta: le frecce dell'ordinamento e il campo scelto in testata."""
        t, v = self.tabella, self.ultima
        r = t.cursor_row if riga is None else riga
        t.clear(columns=True)
        cols = colonne_visibili(v.get("cols") or {}, v.get("class") or {})
        for i, (k, titolo) in enumerate(cols):
            # due caratteri tenuti sempre per la freccia, cosi' le colonne non ballano
            et = Text(titolo + FRECCE.get(self.ordine.get(k, ""), "  "))
            if i == t.testata:
                et.stylize("reverse")
            t.add_column(et, key=k)
        for i, rr in enumerate(v.get("data") or []):
            t.add_row(*[_testo(rr.get(k)) for k, _ in cols], key=f"{i}:{rr.get('id')}")
        if t.row_count:
            t.move_cursor(row=min(r, t.row_count - 1))

    def apri_riga(self):
        """Invio su una riga: il form della vista ( open ) col record di quella riga."""
        v, t = self.ultima, self.tabella
        pagina = v.get("open")
        chiave = str(t.coordinate_to_cell_key(t.cursor_coordinate).row_key.value)
        id = chiave.split(":", 1)[1]
        if not id or id == "None":
            self._stato("questa riga non ha un id")
            return
        self._apri_form(id)

    def action_nuovo(self):
        """Ctrl+N: il form della vista vuoto, senza id; il salvataggio inserisce."""
        self._apri_form(None)

    def _apri_form(self, id):
        v = self.ultima
        pagina = v.get("open")
        if not pagina:
            self._stato("questa vista non apre un form")
            return
        # la vista legge da <tabella>_view: il record si chiede all'entita'
        tabella = re.sub(r"_view(_static)?$", "", v.get("table") or "")
        self.display = False
        self.screen.mount(Form(pagina, tabella, id, self), after=self)

    def on_data_table_header_selected(self, ev):
        # click sul titolo di una colonna: il menu dell'ordinamento
        ev.stop()
        self.menu_ordine(ev.column_index)

    def _stato(self, testo: str):
        self.query_one("#vista-piede", Static).update(testo)

    def action_pagina(self, d: int, fuoco: bool = True):
        n = int(self.pager.get("page") or 0) + d
        if 0 <= n < int(self.pager.get("pages") or 1):
            self._stato("carico...")
            self.carica(n, fuoco)


# i campi dei form, riga per riga come nei Twig ( frm.input, frm.select, frm.textarea ): campo, etichetta,
# tendina ( la chiave di etc.select ) o "testo" per una textarea; per i form che non sono qui, i campi del record
# le sottotabelle mostrate come righe dentro una scheda: (tabella, titolo, campo del padre, colonne);
# l'ultima riga e' vuota, per aggiungerne una; una riga svuotata nella prima colonna si toglie
SOTTO = {
    "anagrafica.form": [
        ("mail", "e-mail", "id_anagrafica",
         [("indirizzo", "indirizzo", None), ("se_pec", "tipo", "se_pec"), ("note", "note", None)]),
        ("telefoni", "telefoni", "id_anagrafica",
         [("numero", "numero", None), ("id_tipologia", "tipo", "tipologie_telefoni"), ("note", "note", None)]),
        ("url", "URL", "id_anagrafica",
         [("url", "url", None), ("id_tipologia", "tipo", "tipologie_url"), ("note", "note", None)]),
        ("anagrafica_indirizzi", "indirizzi", "id_anagrafica",
         [("id_ruolo", "ruolo", "ruoli_indirizzi"), ("id_tipologia", "tipo", "tipologie_indirizzi"),
          ("indirizzo", "indirizzo", None), ("civico", "civico", None), ("interno", "int.", None),
          ("localita", "località", None), ("cap", "cap", None), ("id_comune", "comune", "api:comuni")]),
        ("anagrafica_categorie", "categorie", "id_anagrafica",
         [("id_categoria", "categoria", "categorie_anagrafica")]),
    ],
    # immagini e file: il path e' un Caricatore ( file trascinati, o Invio ), la riga si completa e si salva da sola
    "anagrafica.form.immagini": [
        ("immagini", "immagini collegate", "id_anagrafica",
         [("ordine", "ord.", None), ("nome", "etichetta", None), ("id_lingua", "lingua", "lingue"),
          ("id_ruolo", "ruolo", "ruoli_immagini"), ("orientamento", "orient.", "orientamenti"),
          ("taglio", "taglio", "tagli"), ("path", "file", "file")]),
    ],
    "anagrafica.form.file": [
        ("file", "file collegati", "id_anagrafica",
         [("ordine", "ord.", None), ("nome", "etichetta", None), ("id_lingua", "lingua", "lingue"),
          ("id_ruolo", "ruolo", "ruoli_file"), ("path", "file", "file")]),
    ],
    # video e audio: un link di YouTube o Vimeo nel codice, oppure un file caricato ( embed html5 )
    "anagrafica.form.video": [
        ("video", "video collegati", "id_anagrafica",
         [("ordine", "ord.", None), ("nome", "etichetta", None), ("id_lingua", "lingua", "lingue"),
          ("id_ruolo", "ruolo", "ruoli_video"), ("embed", "embed", "embed"),
          ("codice_embed", "link o codice", "link"), ("path", "file", "file")]),
    ],
    "anagrafica.form.audio": [
        ("audio", "audio collegati", "id_anagrafica",
         [("ordine", "ord.", None), ("nome", "etichetta", None), ("id_lingua", "lingua", "lingue"),
          ("id_ruolo", "ruolo", "ruoli_audio"), ("embed", "embed", "embed"),
          ("codice_embed", "link o codice", "link"), ("path", "file", "file")]),
    ],
}

# le colonne strette delle sottotabelle, in caratteri
STRETTI = {"civico": 7, "interno": 5, "cap": 6, "ordine": 6}

FORMS = {
    "anagrafica.form": ("dati generali", [
        [("id_tipologia", "tipologia", "tipologie_anagrafica"), ("codice", "codice", None),
         ("nome", "nome", None), ("cognome", "cognome", None), ("sesso", "sesso", "sesso")],
        [("denominazione", "denominazione", None), ("soprannome", "soprannome", None)],
        [("note", "note", "testo")],
    ]),
    # le tendine con 'source': { 'api': 'anagrafica' } ( agente, responsabili ) per ora sono l'id da scrivere
    "anagrafica.form.cliente": ("cliente", [
        [("id_ranking", "ranking", "ranking"), ("id_agente", "agente", "api:anagrafica")],
        [("note_commerciali", "note commerciali", "testo")],
        [("id_responsabile_operativo", "responsabile operativo", "api:anagrafica")],
        [("condizioni_vendita", "condizioni di vendita", "testo"), ("note_amministrative", "note amministrative", "testo")],
        [("codice_fiscale", "codice fiscale", None), ("partita_iva", "partita IVA", None), ("id_regime", "regime fiscale", "regimi")],
        [("rea_ufficio", "ufficio REA", None), ("rea_numero", "numero REA", None), ("capitale_sociale", "capitale sociale", None),
         ("socio_unico", "soci", "socio_unico"), ("stato_liquidazione", "liquidazione", "stato_liquidazione")],
        [("id_rappresentante_fiscale", "rappresentante fiscale in Italia", "api:anagrafica")],
        [("codice_archivium", "codice Archivium", "fisso"), ("codice_sdi", "cod. destinatario SDI", None),
         ("id_pec_sdi", "PEC per la fatturazione", "pec")],
    ]),
    "anagrafica.form.archiviazione": ("archiviazione", [
        [("data_archiviazione", "data", None)],
        [("note_archiviazione", "note", "testo")],
    ]),
    # schede fatte solo di sottotabelle ( SOTTO ): nessun campo del record
    "anagrafica.form.immagini": ("immagini", []),
    "anagrafica.form.file": ("file", []),
    "anagrafica.form.video": ("video", []),
    "anagrafica.form.audio": ("audio", []),
}


class Scelta(Static, can_focus=True):
    """Un campo a tendina ( frm.select ): mostra l'etichetta della voce scelta, Invio o freccia giu' aprono la tendina."""
    BINDINGS = [Binding("enter,space,down", "apri", show=False),
                Binding("right", "app.focus_next", show=False), Binding("left", "app.focus_previous", show=False),
                Binding("up", "su", show=False)]

    def action_su(self):
        if not (_in_verticale(self, -1) or _alle_schede(self)):
            raise SkipAction()

    def __init__(self, voci: list, valore, **kw):
        super().__init__(**kw)
        # etc.select.lingue arriva indicizzata per codice ietf ( {"it-IT": {"id": 1, ...}} ): contano i valori
        if isinstance(voci, dict):
            voci = list(voci.values())
        self.voci = [{"id": str(x.get("id")), "label": _testo(x.get("__label__") or x.get("nome") or x.get("id"))}
                     for x in voci or [] if isinstance(x, dict)]
        self.valore = None if valore is None else str(valore)

    def on_mount(self):
        self._scrivi()

    def _scrivi(self):
        e = next((x["label"] for x in self.voci if x["id"] == self.valore), "")
        w = max(4, self.size.width or 20)
        self.update(Text((e + " ").ljust(w - 1, "_")[:w - 1] + "▼"))

    def on_resize(self):
        self._scrivi()

    def action_apri(self):
        if not self.voci:
            return

        def scelto(v):
            if v is not None:
                self.valore = v["id"]
                self._scrivi()
        self.app.push_screen(Tendina(self.voci, self.region.x, self.region.y + 1, False, chiara=True), scelto)

    def on_click(self):
        self.focus()
        self.action_apri()


class Ricerca(Campo):
    """Un campo con 'source': {'api': '<tabella>'} ( il comune, l'agente... ): mostra l'etichetta della voce scelta;
    si scrive parte del nome, Invio cerca sul server ( api/cli, "cerca" ) e apre la tendina di quello che ha
    trovato. Svuotato vuol dire nessun valore; un testo scritto e non confermato torna all'etichetta uscendo."""
    BINDINGS = [Binding("enter", "cerca", show=False)]

    def __init__(self, tabella: str, valore, **kw):
        super().__init__(value="", **kw)
        self.tabella, self.etichetta, self._cercando = tabella, "", False
        self.valore = None if valore in (None, "") else str(valore)

    def on_mount(self):
        if self.valore:
            self._chiedi({"id": self.valore}, self._mostra)

    @work(thread=True)
    def _chiedi(self, cosa: dict, poi):
        try:
            v = self.app.sito._post("api/cli", {"cerca": {"tabella": self.tabella, **cosa}})["cerca"]["voci"]
        except Exception:
            v = []
        self.app.call_from_thread(poi, [{"id": str(x.get("id")), "label": _testo(x.get("__label__") or x.get("id"))}
                                        for x in v or []])

    def _mostra(self, voci):
        self.etichetta = voci[0]["label"] if voci else f"#{self.valore}"
        if not self.value:
            self.value = self.etichetta

    def action_cerca(self):
        q = self.value.strip()
        if len(q) >= 2 and q != self.etichetta:
            self._chiedi({"q": q}, self._apri)

    def _apri(self, voci):
        if not voci:
            self.app.bell()
            return

        def scelto(v):
            self._cercando = False
            if v is not None:
                self.valore, self.etichetta, self.value = v["id"], v["label"], v["label"]
        self._cercando = True
        self.app.push_screen(Tendina(voci, self.region.x, self.region.y + 1, False, chiara=True), scelto)

    def on_input_changed(self, ev):
        if not self.value.strip():
            self.valore, self.etichetta = None, ""

    def on_blur(self):
        if not self._cercando and self.value.strip() != self.etichetta:
            self.value = self.etichetta


def _percorsi(testo: str) -> list[str]:
    """I file trascinati nel terminale: gnome-terminal incolla i percorsi fra apici e separati da spazi, altri
    terminali come file:// uno per riga. Torna i percorsi cosi' come sono, esistano o no su questa macchina."""
    import shlex
    from urllib.parse import unquote, urlparse
    testo = testo.strip()
    if not testo:
        return []
    if "file://" in testo:
        return [unquote(urlparse(x).path) for x in testo.split() if x.startswith("file://")]
    try:
        pezzi = shlex.split(testo)
    except ValueError:
        pezzi = [testo]
    return [x for x in pezzi if x.startswith(("/", "~"))]


def _link_video(testo: str):
    """Un link di YouTube o Vimeo: (servizio, codice), il codice e' quello che il framework vuole in codice_embed
    ( l'id del video: _default.twig ne fa https://www.youtube.com/embed/<codice> ). None se non e' un link."""
    s = testo.strip()
    m = re.search(r"(?:youtu\.be/|youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/|v/))"
                  r"([A-Za-z0-9_-]{11})", s)
    if m:
        return "youtube", m.group(1)
    m = re.search(r"vimeo\.com/(?:.*/)?(?:video/)?(\d+)", s)
    if m:
        return "vimeo", m.group(1)
    return None


def _titolo_video(url: str, servizio: str) -> str:
    """Il titolo del video dall'oEmbed del servizio, per l'etichetta della riga; vuoto se non risponde."""
    import requests
    base = {"youtube": "https://www.youtube.com/oembed", "vimeo": "https://vimeo.com/api/oembed.json"}[servizio]
    try:
        t = (requests.get(base, params={"url": url, "format": "json"}, timeout=8).json().get("title") or "").strip()
    except Exception:
        return ""
    # via le aggiunte fra parentesi ( "(Official Video) (4K Remaster)" ): rumore, e il titolo intero il
    # ModSecurity di web03 lo rifiuta come attacco
    return re.sub(r"\s+", " ", re.sub(r"\s*[(\[][^)\]]*[)\]]", "", t)).strip() or t


def _riga_di(w):
    """(sottotabella, indice) di un campo di sottotabella dal suo id s-<sub>-<i>-<campo>; None nel form."""
    m = re.match(r"s-(.+)-(\d+)-[^-]+$", w.id or "")
    return (m.group(1), int(m.group(2))) if m else None


class Sfoglia(ModalScreen):
    """La scelta di un file fra quelli di questa macchina ( anche via ssh, dove il trascinamento porterebbe il
    percorso del computer di chi scrive ): Invio su un file lo sceglie, Esc chiude."""
    BINDINGS = [Binding("escape", "chiudi", show=False)]
    CSS = """
    Sfoglia { align: center middle; }
    #sfoglia { width: 80%; height: 80%; border: solid #ffffff; background: #000080; }
    #sfoglia-dove { height: 1; }
    """

    def __init__(self, partenza: str):
        super().__init__()
        self.partenza = partenza

    def compose(self) -> ComposeResult:
        from textual.widgets import DirectoryTree
        with Vertical(id="sfoglia"):
            yield Static(f"scegli un file ( {self.partenza} ) · Invio sceglie, Esc chiude", id="sfoglia-dove")
            yield DirectoryTree(self.partenza, id="sfoglia-albero")

    def on_mount(self):
        self.query_one("#sfoglia-albero").focus()

    def on_directory_tree_file_selected(self, e):
        self.dismiss(str(e.path))

    def action_chiudi(self):
        self.dismiss(None)


def _partenza() -> str:
    import os
    for d in ("~/Immagini", "~/Pictures", "~/Scaricati", "~/Downloads", "~"):
        d = os.path.expanduser(d)
        if os.path.isdir(d):
            return d
    return os.getcwd()


class Caricatore(Campo):
    """Il path di un'immagine, di un file o di un video ( frm.uploader ): mostra il percorso sul sito. Ci si
    trascinano sopra uno o piu' file ( il terminale ne incolla il percorso ) e si caricano da soli; in
    alternativa si scrive un percorso e Invio, o Invio sul campo vuoto apre la scelta fra i file di questa
    macchina. Caricato il file, la riga si completa ( etichetta, ordine, ruolo, lingua ) e si salva; piu' file
    insieme fanno una riga l'uno."""
    BINDINGS = [Binding("enter", "carica", show=False)]

    def _form(self):
        return next((a for a in self.ancestors if isinstance(a, Form)), None)

    def _avvisa(self, testo: str, bell: bool = False):
        f = self._form()
        if f:
            f._piede(testo)
        if bell:
            self.app.bell()

    def _on_paste(self, event: events.Paste):
        p = _percorsi(event.text)
        if p:
            event.prevent_default()
            event.stop()
            self._prova(p)

    def action_carica(self):
        q = self.value.strip()
        if q.startswith(("var/", "tmp/")):
            return
        if not q:
            def scelto(x):
                if x:
                    self._prova([x])
            self.app.push_screen(Sfoglia(_partenza()), scelto)
            return
        self._prova(_percorsi(q) or [q])

    def _prova(self, percorsi: list[str]):
        import os
        ok = [os.path.expanduser(x) for x in percorsi if os.path.isfile(os.path.expanduser(x))]
        if not ok:
            self._avvisa(f"file non trovato su questa macchina: {percorsi[0]} ( via ssh il file trascinato sta "
                         "sul tuo computer: Invio sul campo vuoto per sceglierlo fra quelli del server )", True)
            return
        mancano = len(percorsi) - len(ok)
        nomi = ", ".join(os.path.basename(x) for x in ok)
        self._avvisa(f"carico {nomi}..." + (f" ( {mancano} non trovati )" if mancano else ""))
        self._carica(ok)

    @work(thread=True, exclusive=True)
    def _carica(self, locali: list[str]):
        fatti, errori = [], []
        for q in locali:
            try:
                fatti.append((q, self.app.sito.carica_file(q)))
            except Exception as e:
                errori.append(f"{q.rsplit('/', 1)[-1]}: {e}")
        self.app.call_from_thread(self._caricati, fatti, errori)

    def _caricati(self, fatti, errori):
        f = self._form()
        dove = _riga_di(self)
        if not fatti:
            self._avvisa("non caricato: " + "; ".join(errori), True)
            return
        if not f or not dove:
            self.value = fatti[0][1]
            self._avvisa(f"caricato in {fatti[0][1]}: Ctrl+S per salvare")
            return
        sub, i = dove
        f.riempi_righe(sub, i, [{"path": server, "__file__": locale} for locale, server in fatti],
                       nota="; ".join(errori))


class Collegamento(Campo):
    """Il codice di un video ( codice_embed ): ci si incolla il link di YouTube o Vimeo, o lo si scrive e Invio,
    e il campo tiene l'id del video, mette il servizio nella colonna embed, l'etichetta dal titolo del video, e
    salva la riga. Un codice gia' scritto a mano resta com'e'."""
    BINDINGS = [Binding("enter", "converti", show=False)]

    def _on_paste(self, event: events.Paste):
        if _link_video(event.text):
            event.prevent_default()
            event.stop()
            self._converti(event.text.strip())

    def action_converti(self):
        if _link_video(self.value):
            self._converti(self.value.strip())

    @work(thread=True, exclusive=True)
    def _converti(self, url: str):
        servizio, codice = _link_video(url)
        titolo = _titolo_video(url, servizio)
        self.app.call_from_thread(self._convertito, servizio, codice, titolo)

    def _convertito(self, servizio, codice, titolo):
        self.value = codice
        f = next((a for a in self.ancestors if isinstance(a, Form)), None)
        dove = _riga_di(self)
        if f and dove:
            f.riempi_righe(dove[0], dove[1], [{"codice_embed": codice, "embed": servizio, "nome": titolo}])


def _campo(tipo, val, wid, sel):
    """Il widget di un campo del form o di una sottotabella secondo il tipo: None un testo, 'testo' una
    textarea, 'api:<tabella>' una ricerca sul server, 'fisso' un testo in sola lettura ( 'disabled' nel twig,
    e non si manda al salvataggio ), altrimenti la tendina di form.select con quel nome."""
    if tipo == "fisso":
        return Campo(value="" if val is None else str(val), id=wid, disabled=True)
    if tipo == "file":
        return Caricatore(value="" if val is None else str(val), id=wid)
    if tipo == "link":
        return Collegamento(value="" if val is None else str(val), id=wid)
    if tipo == "testo":
        return Testo(_testo(val) if val is not None else "", id=wid)
    if tipo and tipo.startswith("api:"):
        return Ricerca(tipo[4:], val, id=wid)
    if tipo:
        return Scelta(sel.get(tipo) or [], val, id=wid)
    return Campo(value="" if val is None else str(val), id=wid)


def _errori(e):
    """Gli errori di controller(): la struttura c'e' sempre ( {"__codes__": null, "mail": [...]} ), conta solo
    se dentro c'e' un valore; torna None se e' vuota."""
    if isinstance(e, dict):
        e = {k: v for k, v in ((k, _errori(v)) for k, v in e.items()) if v is not None}
    elif isinstance(e, list):
        e = [v for v in map(_errori, e) if v is not None]
    return e if e not in (None, "", {}, []) else None


# gli errori MySQL che controller() raccoglie in __codes__: il motivo in chiaro e, dal testo, tabella e colonna.
# 1054 e 1062 il framework li riscrive senza dettagli ( _mysql.tools.php ): restano senza campo
MOTIVI = {
    "1048": "obbligatorio", "1292": "valore non valido", "1366": "valore non valido", "1406": "troppo lungo",
    "1264": "fuori dai limiti", "1452": "valore inesistente", "1451": "il record e' usato altrove",
    "1062": "valore gia' presente", "1054": "colonna sconosciuta",
}


def dove_errori(err) -> list[tuple[str | None, str | None, str]]:
    """Da err di controller() le righe ( tabella, colonna, motivo ): tabella None se il messaggio non la dice,
    colonna None se non dice nemmeno quella. Il valore rifiutato, quando c'e', finisce nel motivo."""
    out = []
    codici = err.get("__codes__") if isinstance(err, dict) else None
    for cod, msgs in (codici or {}).items():
        for m in (msgs if isinstance(msgs, list) else [msgs]):
            m, cod = str(m), str(cod)
            motivo = MOTIVI.get(cod, m[:80])
            tab = col = None
            if cod in ("1451", "1452"):
                x = re.search(r"\(`[^`]+`\.`([^`]+)`, CONSTRAINT `[^`]+` FOREIGN KEY \(`([^`]+)`\)", m)
                if x:
                    tab, col = x.groups()
                if cod == "1451":
                    motivo, tab, col = (f"il record e' usato in {tab}" if tab else motivo), None, None
            else:
                x = re.search(r"column `[^`]+`\.`([^`]+)`\.`([^`]+)`", m)
                if x:
                    tab, col = x.groups()
                elif x := re.search(r"[Cc]olumn '([^']+)'", m):
                    col = x.group(1)
            v = re.search(r"value: '([^']*)'", m)
            if v and cod in ("1292", "1366"):
                motivo += f" ( '{v.group(1)}' )"
            out.append((tab, col, motivo))
    return out


class Testo(TextArea):
    """La textarea dei form: come Campo, le frecce in cima o in fondo al testo cambiano campo, e la freccia su
    dalla prima riga porta alle schede."""

    def action_cursor_up(self, select: bool = False):
        if select or self.cursor_location[0] != 0 or not (_in_verticale(self, -1) or _alle_schede(self)):
            super().action_cursor_up(select)

    def action_cursor_down(self, select: bool = False):
        if select or self.cursor_location[0] != self.document.line_count - 1 or not _in_verticale(self, 1):
            super().action_cursor_down(select)

    def action_cursor_left(self, select: bool = False):
        if not select and self.cursor_location == (0, 0):
            self.screen.focus_previous()
        else:
            super().action_cursor_left(select)

    def action_cursor_right(self, select: bool = False):
        if not select and self.cursor_location == self.document.end:
            self.screen.focus_next()
        else:
            super().action_cursor_right(select)


class Piu(Static, can_focus=True):
    """I bottoni in fondo a una riga di sottotabella. [-] su ogni riga: Invio la svuota, e al salvataggio si toglie.
    [+] sull'ultima: Invio aggiunge una riga vuota sotto e ci porta il fuoco ( Ctrl++ e Ctrl+-
    non si usano: molti terminali non li distinguono da Ctrl+= e Ctrl+_ o non li mandano affatto )."""
    BINDINGS = [Binding("enter,space", "aggiungi", show=False),
                Binding("left", "app.focus_previous", show=False), Binding("right", "app.focus_next", show=False),
                Binding("up", "su", show=False), Binding("down", "giu", show=False)]

    def __init__(self, sub: str, piu: bool = True, **kw):
        super().__init__("[+]" if piu else "[-]", classes="sub-piu", **kw)
        self.sub, self.piu = sub, piu

    def action_aggiungi(self):
        if self.piu:
            next(a for a in self.ancestors if isinstance(a, Form)).aggiungi_riga(self.sub)
            return
        for w in self.parent.children:
            if isinstance(w, Campo):
                w.value = ""
            elif isinstance(w, Scelta):
                w.valore = None
                w._scrivi()

    def action_su(self):
        _in_verticale(self, -1)

    def action_giu(self):
        _in_verticale(self, 1)

    def on_click(self):
        self.action_aggiungi()


class Schede(Static, can_focus=True):
    """La riga delle schede del form: col fuoco sopra, le frecce cambiano scheda."""
    BINDINGS = [Binding("right", "scheda(1)", show=False), Binding("left", "scheda(-1)", show=False),
                Binding("down", "giu", show=False)]

    def action_scheda(self, d: int):
        self.parent.action_scheda(d)

    def action_giu(self):
        # freccia giu' dalle schede: il primo campo della scheda
        campi = self.parent.query("#form-campi Campo, #form-campi Scelta, #form-campi Testo")
        if campi:
            campi.first().focus()


class Form(Vertical):
    """Una pagina *.form.twig: il record letto da api/cli, i campi come nel Twig. Ctrl+S salva ( controller()
    in UPDATE sul server, senza id inserisce ) e il form si riempie col record riletto; Ctrl+N passa a un form
    vuoto, Ctrl+D due volte cancella ( DELETE ). Esc torna alla vista da cui si e' aperto, ricaricata se qualcosa
    e' cambiato; con modifiche non salvate Esc e Ctrl+N chiedono di ripetere il tasto."""
    BINDINGS = [Binding("escape", "chiudi", "chiudi", show=False, priority=True),
                Binding("ctrl+s", "salva", "salva", show=False, priority=True),
                Binding("ctrl+n", "nuovo", "nuovo", show=False, priority=True),
                Binding("ctrl+d", "elimina", "elimina", show=False, priority=True),
                Binding("alt+right", "scheda(1)", "scheda dopo", show=False, priority=True),
                Binding("alt+left", "scheda(-1)", "scheda prima", show=False, priority=True)]
    # l'aiuto sta su una riga: i tasti di tutti i form, piu' quelli che servono solo sulla scheda aperta ( _aiuto )
    AIUTO = "Tab/S-Tab campo · Alt+←→ scheda · ^S salva · ^N nuovo · ^D elimina · Esc vista"
    AIUTO_TENDINA = "Invio/↓ tendina"
    AIUTO_SUB = "Invio su [+] riga in più, [-] svuota"

    def _aiuto(self, tendine: bool, sottotabelle: bool):
        self.query_one("#form-piede", Static).update(" · ".join(
            [self.AIUTO] + ([self.AIUTO_TENDINA] if tendine else []) + ([self.AIUTO_SUB] if sottotabelle else [])))

    AIUTO_VISTA = "↑↓ riga · Invio apre · ^N nuovo · Alt+←→ scheda · Esc vista"

    def __init__(self, pagina: str, tabella: str, id, vista: "Vista | Form | None" = None,
                 preset: dict | None = None):
        super().__init__()
        self.pagina, self.tabella, self.rid, self.vista = pagina, tabella, id, vista
        # vista e' da dove si e' aperto: una Vista, o un altro Form quando la riga viene da una scheda-vista
        self.preset = preset or {}  # i campi gia' decisi di un record nuovo ( il cliente, aperto dalla sua scheda )
        self.vista_dentro: dict | None = None  # la scheda e' una vista ( lavoro, attivita ): le sue righe
        self.cambiato_figlio = False  # un form aperto da questa scheda-vista ha salvato: le righe si rileggono
        self.dati: dict = {}
        self.letti: dict = {}       # i valori com'erano dopo l'ultima lettura, per sapere se si e' modificato
        self.esc_avvisato = False   # tasto ( escape, ctrl+n ) gia' premuto una volta con modifiche non salvate
        self.del_avvisato = False
        self.cambiato = False       # salvato o cancellato: la vista va ricaricata
        self.schede: list[str] = []  # le pagine di etc.tabs: la prima e' il form principale
        self.spazi: list[tuple[int, int, str]] = []  # dove sta ogni scheda nella riga, per il clic
        self._sel: dict = {}  # le voci delle tendine dell'ultima lettura, per le righe aggiunte col [+]
        self.righe_sub: dict[str, list] = {}  # per ogni sottotabella mostrata, l'id di ogni riga ( None = nuova )
        self.teste: dict[str, list] = {}  # per ogni sottotabella mostrata, le etichette della testata

    def compose(self) -> ComposeResult:
        yield Schede("", id="form-schede")
        with VerticalScroll(id="form-corpo", can_focus=False):
            yield Vertical(id="form-campi")
            yield Static("", id="form-figli")
        with Vertical(id="form-fondo"):
            yield Static("", id="form-stato")
            yield Static(self.AIUTO, id="form-piede")

    def on_mount(self):
        self.carica()

    def _piede(self, testo: str):
        # esiti e conferme stanno nella riga di stato, sopra l'aiuto dei tasti che resta sempre visibile
        self.query_one("#form-stato", Static).update(testo)

    @work(thread=True, exclusive=True)
    def carica(self, salva: dict | None = None, elimina: bool = False):
        pagina = self.pagina
        try:
            d = self.app.sito.pagina(pagina, {}, {"tabella": self.tabella, "id": self.rid}, salva, elimina)
        except ErroreApi as e:
            if pagina != self.pagina:
                return
            if elimina:
                self.app.call_from_thread(self._piede, f"non eliminato: {e}")
            elif salva is None:
                self.app.call_from_thread(self._vuota, f"{self._nome(self.pagina)}: {e}")
            else:
                self.app.call_from_thread(self._piede, f"non salvato: {e}")
            return
        if pagina != self.pagina:
            return  # nel frattempo si e' passati a un'altra scheda: questa risposta non serve piu'
        f = d.get("form") or {}
        # le schede sono quelle del form principale: alcune pagine figlie ( audio, video ) ne danno una lista diversa.
        # Il server le filtra sul record ( la scheda cliente solo se l'anagrafica e' un cliente, _anagrafica.form.default.php ):
        # a ogni lettura del form principale si riprendono, cosi' una categoria cambiata e salvata le aggiorna
        t = d.get("tabs") or []
        if t and (not self.schede or (t[0] if isinstance(t[0], str) else str(t[0].get("id"))) == self.pagina):
            self.schede = [t if isinstance(t, str) else str(t.get("id")) for t in d["tabs"]]
        if elimina:
            esito, err = f.get("eliminato"), _errori(f.get("err"))
            if isinstance(esito, int) and 200 <= esito < 300 and not err:
                self.cambiato = True
                self.app.call_from_thread(self._esci)
            else:
                self.app.call_from_thread(self._piede, f"non eliminato: {self._motivi(err, esito)}"[:200])
            return
        if salva is not None:
            esito, err = f.get("salvato"), _errori(f.get("err"))
            ok = isinstance(esito, int) and 200 <= esito < 300 and not err
            # un record nuovo: dopo l'inserimento il form prosegue sull'id che ha preso
            # un record nuovo: dopo l'inserimento il form prosegue sull'id che ha preso, anche se una sottotabella
            # e' stata rifiutata, cosi' il salvataggio dopo la correzione non lo inserisce una seconda volta
            nuovo = (f.get("record") or {}).get("id")
            if nuovo and (ok or not self.rid):
                self.rid = str(nuovo)
            self.cambiato = self.cambiato or ok
            if not ok:
                # i campi restano come li ha scritti l'utente: si segna quello che il server ha rifiutato
                self.app.call_from_thread(self._segna_errori, err, esito)
                return
        self.app.call_from_thread(self._riempi, f, d.get("view"))
        if salva is not None:
            self.app.call_from_thread(self._piede, "salvato")

    @staticmethod
    def _motivi(err, esito) -> str:
        righe = dove_errori(err)
        if not righe:
            return f"esito {esito}" + (": " + _testo(json.dumps(err, ensure_ascii=False)) if err else "")
        return "; ".join(f"{(t + '.') if t else ''}{(c + ': ') if c else ''}{m}" for t, c, m in righe)

    def _segna_errori(self, err, esito):
        """Un salvataggio rifiutato: l'etichetta del campo ( o la testata della colonna, in una sottotabella )
        diventa negativa col motivo, il fuoco va sul primo campo segnato, il riepilogo nella riga di stato."""
        for l in self.query("Label.errore"):
            l.remove_class("errore")
            l.update(l.testo)
        primo, resto = None, []
        for tab, col, motivo in dove_errori(err):
            segnato = None
            if col and tab in (None, self.tabella) and self.query(f"#f-{col}"):
                w = self.query_one(f"#f-{col}")
                segnato, etichetta = w, w.parent.query_one(Label)
            elif col:
                for sub, testa in self.teste.items():
                    nomi = [c for c, _, _ in next(c for s_, _, _, c in SOTTO[self.pagina] if s_ == sub)]
                    if tab in (None, sub) and col in nomi:
                        etichetta = testa[nomi.index(col)]
                        segnato = next((w for w in self.query("#form-campi *")
                                        if (w.id or "").startswith(f"s-{sub}-") and w.id.endswith(f"-{col}")), None)
                        break
            if segnato is None:
                resto.append(f"{(tab + '.') if tab else ''}{(col + ': ') if col else ''}{motivo}")
                continue
            if not hasattr(etichetta, "testo"):
                etichetta.testo = str(etichetta.render())
            etichetta.add_class("errore")
            etichetta.update(f"{etichetta.testo}: {motivo}")
            primo = primo or segnato
        if primo is not None:
            primo.focus()
        n = len(self.query("Label.errore"))
        testo = "non salvato" + (f": {n} campi segnati" if n > 1 else ": campo segnato" if n else "")
        if resto or not n:
            testo += " · " + ("; ".join(resto) if resto else f"esito {esito}")
        self._piede(testo[:200])

    def _riga_sub(self, sub: str, colonne: list, i: int, r: dict, ultima: bool):
        """Una riga di sottotabella e i suoi campi: in fondo il [-] per svuotarla e, sull'ultima, il [+] per
        aggiungerne un'altra."""
        celle = []
        for campo, _, tipo in colonne:
            w = _campo(tipo, r.get(campo), f"s-{sub}-{i}-{campo}", self._sel)
            if campo in STRETTI:
                w.styles.width = STRETTI[campo]
            celle.append(w)
        coda = [Piu(sub, piu=False), Piu(sub) if ultima else Static("", classes="sub-piu")]
        return Horizontal(*celle, *coda, classes="form-sub"), celle

    def aggiungi_riga(self, sub: str, r: dict | None = None, fuoco: bool = True):
        """Il [+]: una riga vuota sotto l'ultima, col fuoco sul suo primo campo; il [+] passa alla riga nuova.
        Con r la riga nasce gia' con quei valori ( i file trascinati insieme )."""
        colonne = next(c for s_, _, _, c in SOTTO.get(self.pagina, []) if s_ == sub)
        piu = next(p for p in self.query(Piu) if p.sub == sub and p.piu)
        vecchia = piu.parent
        i = len(self.righe_sub[sub])
        self.righe_sub[sub].append(None)
        nuova, celle = self._riga_sub(sub, colonne, i, r or {}, ultima=True)
        piu.remove()
        vecchia.mount(Static("", classes="sub-piu"))
        vecchia.parent.mount(nuova, after=vecchia)
        if fuoco:
            self.call_after_refresh(celle[0].focus)
        return celle

    # le voci preferite per il ruolo di una riga nuova, se la tendina le ha; altrimenti la prima
    RUOLI_PREFERITI = ("principale", "immagine", "allegato", "video", "audio")

    def _predefinito(self, tipo: str, campo: str):
        """La voce di una tendina per una riga completata da sola: per ruolo e lingua la preferita o la prima."""
        if campo not in ("id_ruolo", "id_lingua") or not isinstance(tipo, str):
            return None
        voci = self._sel.get(tipo) or []
        voci = [x for x in (voci.values() if isinstance(voci, dict) else voci) if isinstance(x, dict)]
        if not voci:
            return None
        nomi = {_testo(x.get("__label__") or x.get("nome") or "").strip().lower(): x for x in voci}
        x = next((nomi[n] for n in self.RUOLI_PREFERITI if n in nomi), voci[0])
        return str(x.get("id"))

    def riempi_righe(self, sub: str, i: int, valori: list[dict], nota: str = ""):
        """Dopo un caricamento o un link: il primo dei valori va nella riga i, gli altri in righe nuove in fondo.
        Ogni riga si completa dove e' vuota ( etichetta dal nome del file, ordine dopo l'ultimo, ruolo e lingua,
        embed html5 per un file in video e audio ), poi si salva."""
        colonne = next(c for s_, _, _, c in SOTTO.get(self.pagina, []) if s_ == sub)
        campi = {c: tipo for c, _, tipo in colonne}

        def leggi(k, c):
            try:
                return _valore(self.query_one(f"#s-{sub}-{k}-{c}"))
            except Exception:
                return ""
        ordini = [int(v) for k in range(len(self.righe_sub[sub])) if str(v := leggi(k, "ordine")).strip().isdigit()]
        prossimo = max(ordini, default=0) + 10
        for n, v in enumerate(valori):
            locale = v.pop("__file__", None)
            if locale:
                base = locale.rsplit("/", 1)[-1].rsplit(".", 1)[0]
                v.setdefault("nome", re.sub(r"[\s_.-]+", " ", base).strip())
                if "embed" in campi:
                    v.setdefault("embed", "html5")
            k = i if n == 0 else None
            # i campi gia' scritti a mano restano: si completa solo il vuoto ( il path e il codice si scrivono sempre )
            pieni = {c for c in campi if k is not None and str(leggi(k, c)).strip()} - {"path", "codice_embed"}
            if "embed" in v and v.get("codice_embed"):
                pieni.discard("embed")
            r = {c: x for c, x in v.items() if c in campi and x not in (None, "") and c not in pieni}
            if "ordine" in campi and "ordine" not in pieni:
                r.setdefault("ordine", str(prossimo))
                prossimo += 10
            for c, tipo in campi.items():
                if c not in pieni and c not in r and (d := self._predefinito(tipo, c)):
                    r[c] = d
            if k is None:
                self.aggiungi_riga(sub, r, fuoco=False)
                continue
            for c, x in r.items():
                w = self.query_one(f"#s-{sub}-{k}-{c}")
                if isinstance(w, Scelta):
                    w.valore = x
                    w._scrivi()
                else:
                    w.value = x
        self._piede("salvo..." + (f" non caricati: {nota}" if nota else ""))
        self.call_after_refresh(self.action_salva)

    def valori(self) -> dict:
        """I valori dei campi come li manda il form web: stringhe, vuoto per nessun valore."""
        out = {}
        for w in self.query("#form-campi Campo, #form-campi Scelta, #form-campi TextArea"):
            if not (w.id or "").startswith("s-") and not w.disabled:
                out[(w.id or "")[2:]] = _valore(w)
        # i campi del preset che il form non mostra si mandano lo stesso
        for k, x in self.preset.items():
            out.setdefault(k, "" if x is None else str(x))
        # le sottotabelle come le manda il form web: una lista di righe, col padre in __parent_id__
        for sub, _, padre, colonne in SOTTO.get(self.pagina, []):
            if sub not in self.righe_sub:
                continue
            righe, via = [], []
            for i, rid in enumerate(self.righe_sub[sub]):
                try:
                    r = {c: _valore(self.query_one(f"#s-{sub}-{i}-{c}")) for c, _, _ in colonne}
                except Exception:
                    continue
                if not any(str(v).strip() for v in r.values()):
                    if rid:
                        via.append(rid)
                    continue
                if rid:
                    r["id"] = rid
                r[padre] = "__parent_id__"
                righe.append(r)
            out[sub] = righe
            if via:
                out.setdefault("__elimina__", {})[sub] = via
        return out

    def modificato(self) -> bool:
        return bool(self.letti) and self.valori() != self.letti

    def action_salva(self):
        if not self.dati or not self.query("#form-campi Campo, #form-campi Scelta, #form-campi TextArea"):
            return
        self.esc_avvisato = self.del_avvisato = False
        self._piede("salvo...")
        self.carica(self.valori())

    def _nome(self, pagina: str) -> str:
        base = self.schede[0] if self.schede else ""
        return pagina[len(base) + 1:] if base and pagina.startswith(base + ".") else "generale"

    def _disegna_schede(self):
        t, x, self.spazi = Text(), 0, []
        for p in self.schede:
            nome = f" {self._nome(p)} "
            t.append(nome, style="bold #000000 on #ffffff" if p == self.pagina else "#ffffff on #000000")
            self.spazi.append((x, x + len(nome), p))
            t.append(" ")
            x += len(nome) + 1
        self.query_one("#form-schede", Static).update(t)

    def _dove(self, rid=None):
        """Record e scheda in coda alle briciole: il dove sta li', non in una riga del form."""
        rid = rid or self.rid
        coda = f"{self.tabella} #{rid}" if rid else f"{self.tabella} nuovo"
        if self.schede:
            coda += f" > {self._nome(self.pagina)}"
        if hasattr(self.screen, "briciole"):
            self.screen.briciole(coda=coda)

    def _vuota(self, testo: str):
        """Una scheda che il server non da' ( stampe, tools ): niente campi, cosi' non si salva per sbaglio."""
        self.dati, self.letti, self.righe_sub, self.teste = {}, {}, {}, {}
        self._piede(testo)
        self._dove()
        self.query_one("#form-campi", Vertical).remove_children()
        self.query_one("#form-figli", Static).update("")
        self._disegna_schede()
        self.query_one("#form-schede").focus()

    def action_scheda(self, d: int):
        if len(self.schede) < 2:
            return
        i = self.schede.index(self.pagina) if self.pagina in self.schede else 0
        self.vai_scheda(self.schede[(i + d) % len(self.schede)])

    def vai_scheda(self, pagina: str):
        if pagina == self.pagina or self._avvisa("Alt+freccia"):
            return
        self.esc_avvisato = self.del_avvisato = False
        self.pagina, self.letti = pagina, {}
        self._disegna_schede()
        self._piede("carico...")
        self.carica()

    def on_click(self, ev):
        if getattr(ev.widget, "id", None) == "form-schede":
            x = ev.get_content_offset(ev.widget)
            if x is not None and x.y == 0:
                p = next((p for a, b, p in self.spazi if a <= x.x < b), None)
                if p:
                    self.vai_scheda(p)

    def _righe(self, f: dict):
        if self.pagina in FORMS:
            return FORMS[self.pagina]
        if self.schede and self.pagina != self.schede[0]:
            return (self._nome(self.pagina), None)  # scheda senza campi descritti: non si indovinano
        # un record nuovo arriva vuoto: i campi dalle colonne della tabella
        rec = f.get("record") or {c: None for c in f.get("colonne") or []}
        campi = [(k, k.replace("_", " "), None) for k, v in rec.items()
                 if not isinstance(v, (list, dict)) and k != "id" and not k.startswith("timestamp")
                 and not k.startswith("id_account")]
        return ("dati", [campi[i:i + 3] for i in range(0, len(campi), 3)])

    async def _riempi(self, f: dict, v: dict | None = None):
        self.dati = f
        rec, sel = f.get("record") or {}, f.get("select") or {}
        if not self.rid and self.preset:
            rec = {**rec, **{k: x for k, x in self.preset.items() if rec.get(k) in (None, "")}}
        self._sel = sel
        self.vista_dentro = v if v and v.get("table") else None
        if self.vista_dentro is not None:
            await self._riempi_vista(self.vista_dentro, rec.get("id") or self.rid)
            return
        titolo, righe = self._righe(f)
        self._disegna_schede()
        if righe is None:
            self._vuota(f"{titolo}: scheda non ancora gestita dal client")
            return
        self._dove(rec.get("id"))
        box = self.query_one("#form-campi", Vertical)
        fuoco = (self.app.focused.id or "") if self.app.focused is not None else ""
        await box.remove_children()
        widgets = []
        for riga in righe:
            celle = []
            for campo, etichetta, tipo in riga:
                w = _campo(tipo, rec.get(campo), f"f-{campo}", sel)
                widgets.append(w)
                celle.append(Vertical(Label(etichetta, classes="campo"), w, classes="form-campo"))
            box.mount(Horizontal(*celle, classes="form-riga"))
        # le sottotabelle descritte in SOTTO: una riga per record piu' una vuota per aggiungere
        self.righe_sub, self.teste = {}, {}
        mostrate = set()
        for sub, nome, _, colonne in SOTTO.get(self.pagina, []):
            mostrate.add(sub)
            esistenti = [r for r in (rec.get(sub) or []) if isinstance(r, dict)]
            # una riga vuota solo se non ce n'e' nessuna, come invito alla prima: le altre si aggiungono col [+]
            self.righe_sub[sub] = [r.get("id") for r in esistenti] or [None]
            box.mount(Label(nome, classes="sub-titolo"))
            testa = self.teste[sub] = [Label(e) for _, e, _ in colonne]
            for l, (c, _, _) in zip(testa, colonne):
                if c in STRETTI:
                    l.styles.width = STRETTI[c]
            box.mount(Horizontal(*testa, Label("", classes="sub-piu"),
                                 Label("", classes="sub-piu"), classes="form-sub-testa"))
            for i, r in enumerate(esistenti or [{}]):
                riga, celle = self._riga_sub(sub, colonne, i, r, ultima=(i == max(len(esistenti), 1) - 1))
                widgets.extend(celle)
                box.mount(riga)
            box.mount(Static("", classes="sub-fine"))
        # le altre sottotabelle ( indirizzi, url... ): per ora solo quante righe hanno
        figli = [f"{k} {len(v)}" for k, v in rec.items() if isinstance(v, (list, dict)) and v and k not in mostrate]
        self.query_one("#form-figli", Static).update(("collegati: " + " · ".join(figli)) if figli else "")
        self._aiuto(any(isinstance(w, Scelta) for w in widgets), bool(mostrate))
        # dopo un salvataggio il fuoco resta sul campo dov'era
        # senza campi il fuoco va sulle schede, cosi' Esc e gli altri tasti del form arrivano comunque
        primo = next((w for w in widgets if w.id == fuoco), widgets[0] if widgets else self.query_one("#form-schede"))
        if primo is not None:
            self.call_after_refresh(primo.focus)
        self.call_after_refresh(lambda: setattr(self, "letti", self.valori()))

    async def _riempi_vista(self, v: dict, rid):
        """Una scheda che e' una vista ( lavoro, attivita ): le righe legate al record, Invio apre la riga
        nel suo form, Ctrl+N ne inserisce una nuova gia' legata al record. Qui non si salva niente."""
        self._disegna_schede()
        self._dove(rid)
        box = self.query_one("#form-campi", Vertical)
        await box.remove_children()
        self.righe_sub, self.teste = {}, {}
        t = DataTable(cursor_type="row", zebra_stripes=True, id="form-vista")
        t.styles.height = "auto"
        cols = colonne_visibili(v.get("cols") or {}, v.get("class") or {})
        for k, titolo in cols:
            t.add_column(titolo, key=k)
        righe = v.get("data") or []
        for i, rr in enumerate(righe):
            t.add_row(*[_testo(rr.get(k)) for k, _ in cols], key=f"{i}:{rr.get('id')}")
        box.mount(t)
        self.query_one("#form-figli", Static).update("" if righe else "nessuna riga")
        self.query_one("#form-piede", Static).update(self.AIUTO_VISTA)
        self._piede(f"{v.get('table')}  ·  {len(righe)} righe")
        self.call_after_refresh(t.focus)
        self.letti = {}

    def _tabella_vista(self) -> str:
        # la vista legge da <tabella>_view: il record si chiede all'entita'
        return re.sub(r"_view(_static)?$", "", (self.vista_dentro or {}).get("table") or "")

    def on_data_table_row_selected(self, ev):
        if self.vista_dentro is None or ev.data_table.id != "form-vista":
            return
        ev.stop()
        id = str(ev.row_key.value).split(":", 1)[1]
        pagina = self.vista_dentro.get("open")
        if not pagina or not id or id == "None":
            self._piede("questa riga non si apre")
            return
        self._apri_figlio(Form(pagina, self._tabella_vista(), id, self))

    def _apri_figlio(self, f: "Form"):
        self.display = False
        self.screen.mount(f, after=self)

    def ricarica(self):
        """Di ritorno da un form aperto da questa scheda: le righe si rileggono."""
        self._piede("carico...")
        self.carica()

    def _avvisa(self, tasto: str) -> bool:
        """Con modifiche non salvate il primo tasto avvisa e basta: True se ci si deve fermare."""
        if self.modificato() and self.esc_avvisato != tasto:
            self.esc_avvisato = tasto
            self._piede(f"modifiche non salvate: Ctrl+S salva, {tasto} di nuovo prosegue senza salvare")
            return True
        return False

    def action_elimina(self):
        if not self.rid:
            self._piede("record nuovo, non ancora salvato: niente da eliminare")
            return
        if not self.del_avvisato:
            self.del_avvisato = True
            self._piede(f"eliminare {self.tabella} #{self.rid}? Ctrl+D di nuovo per confermare, Esc annulla")
            return
        self.del_avvisato = False
        self._piede("elimino...")
        self.carica(None, True)

    def action_nuovo(self):
        if self.vista_dentro is not None:
            # dalla scheda-vista: un record nuovo della vista, legato a questo ( il preset )
            v = self.vista_dentro
            pagina, campo = v.get("insert") or v.get("open"), v.get("preset")
            if not pagina:
                self._piede("questa scheda non inserisce")
                return
            self._apri_figlio(Form(pagina, self._tabella_vista(), None, self,
                                   {campo: str(self.rid)} if campo and self.rid else None))
            return
        if self._avvisa("Ctrl+N"):
            return
        # il form vuoto prende il posto di questo, sulla stessa vista
        self.screen.mount(Form(self.pagina, self.tabella, None, self.vista, self.preset), after=self)
        if self.cambiato and isinstance(self.vista, Vista) and self.vista.is_attached:
            self.vista.carica(int(self.vista.pager.get("page") or 0), False)
        elif self.cambiato and isinstance(self.vista, Form) and self.vista.is_attached:
            self.vista.cambiato_figlio = True
        self.remove()

    def action_chiudi(self):
        if self.del_avvisato:
            self.del_avvisato = False
            self._piede("eliminazione annullata")
            return
        if self._avvisa("Esc"):
            return
        self._esci()

    def _esci(self):
        if hasattr(self.screen, "briciole"):
            self.screen.briciole(coda="")
        if isinstance(self.vista, Form) and self.vista.is_attached:
            # si torna alla scheda-vista del form da cui si era aperta la riga
            padre = self.vista
            padre.display = True
            if self.cambiato or padre.cambiato_figlio:
                padre.cambiato_figlio = False
                padre.ricarica()
            else:
                padre._dove(padre.rid)
                if padre.query("#form-vista"):
                    padre.call_after_refresh(padre.query_one("#form-vista").focus)
        elif self.vista is not None and self.vista.is_attached:
            self.vista.display = True
            self.vista.tabella.focus()
            if self.cambiato:
                self.vista._stato("carico...")
                self.vista.carica(int(self.vista.pager.get("page") or 0))
        else:
            self.screen.query_one("#corpo", Static).display = True
        self.remove()


class GliswebApp(App):
    TITLE = "glisweb-cli"
    CSS = CSS
    BINDINGS = [Binding("ctrl+q,ctrl+c", "quit", "esci", priority=True)]

    def __init__(self, radice, cx, sito: Sito | None, remoto: bool = False, codice: str | None = None,
                 preset: dict | None = None):
        super().__init__()
        self.codice = codice  # -k: il codice da proporre nel login
        self.preset = preset or {}  # da ~/.glisweb-cli.rc: codice, utente, password
        self.radice, self.cx, self.sito = radice, cx, sito
        # remoto: niente deploy in locale, il login passa dal codice ( configserver e profili )
        self.remoto = remoto

    INATTIVITA = 3600   # dopo un'ora senza tasti ne' clic si torna al login
    RINNOVO = 60        # mentre si lavora, il token si rinnova se l'ultima chiamata ha piu' di un minuto
    MARGINE = 5         # si esce qualche secondo prima che il token scada sul server

    def on_mount(self):
        # sempre dal login, anche col token valido: si puo' cambiare codice o utente ( 10/11/2026 )
        self.push_screen(Login())
        self.attivita = time.time()
        self._rinnovo_in_corso = False
        self.set_interval(1, self._sorveglia)

    async def on_event(self, event):
        # l'uso vero: tasti, clic e rotella ( non il solo passaggio del mouse )
        if isinstance(event, (events.Key, events.MouseDown, events.MouseScrollDown, events.MouseScrollUp)):
            self.attivita = time.time()
        await super().on_event(event)

    def _collegato(self) -> bool:
        return any(isinstance(s, Dashboard) for s in self.screen_stack)

    def _sorveglia(self):
        """Ogni secondo: col token scaduto, o dopo un'ora senza uso, i dati spariscono subito dallo schermo."""
        s = self.sito
        if not self._collegato() or s is None or s.scade is None:
            return
        ora = time.time()
        if ora - self.attivita >= self.INATTIVITA:
            self.esci_sessione("sessione chiusa dopo un'ora di inattivita'")
        elif ora >= s.scade - self.MARGINE:
            self.esci_sessione("sessione scaduta")
        elif self.attivita > s.ultima_chiamata and ora - s.ultima_chiamata >= self.RINNOVO and not self._rinnovo_in_corso:
            self._rinnovo_in_corso = True
            self._rinnova()

    @work(thread=True, exit_on_error=False)
    def _rinnova(self):
        try:
            self.sito.rinnova()
        except ErroreApi:
            pass  # il 401 porta gia' al login da solo; il sito che non risponde si riprova al giro dopo
        finally:
            self._rinnovo_in_corso = False

    def _scaduta(self):
        # chiamato da Sito a ogni 401, spesso da un thread: l'uscita si fa sul thread della TUI
        if threading.get_ident() == self._thread_id:
            self.call_later(self.esci_sessione, "sessione scaduta")
        else:
            self.call_from_thread(self.esci_sessione, "sessione scaduta")

    def esci_sessione(self, motivo: str):
        """Via tutte le schermate con dati, il token buttato, e il login col motivo."""
        if not self._collegato():
            return
        if self.sito is not None:
            self.sito.esci()
            self.sito.scade = None
        while len(self.screen_stack) > 1:
            self.pop_screen()
        self.push_screen(Login(motivo))

    @work(thread=True)
    def _riprendi(self):
        try:
            s = self.sito.struttura()
        except ErroreApi:
            self.sito.esci()
            self.call_from_thread(self.push_screen, Login())
            return
        self.call_from_thread(self.apri_dashboard, s)

    def apri_dashboard(self, struttura: dict):
        self.attivita = time.time()
        self.sito.su_scaduta = self._scaduta
        self.switch_screen(Dashboard(struttura)) if self.screen_stack[-1].__class__ is Login else self.push_screen(Dashboard(struttura))

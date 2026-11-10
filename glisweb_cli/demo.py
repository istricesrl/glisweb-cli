"""Un sito finto per provare l'interfaccia senza rete ( --demo ): qualunque utente, password 'demo'."""
from .api import ErroreApi, Sito


def _p(id, label, figli=(), schema=None):
    return {"id": id, "label": label, "schema": schema, "content": list(figli)}


MENU = [
    _p("dashboard", "dashboard"),
    _p("anagrafica", "anagrafica", [
        _p("anagrafica.view", "elenco", schema="default.view.twig"),
        _p("anagrafica.form", "nuova", schema="ext.form"),
        _p("anagrafica.tools", "strumenti", [
            _p("anagrafica.tools.import", "importa", schema="ext.tools"),
            _p("anagrafica.tools.export", "esporta", schema="ext.tools")])]),
    _p("catalogo", "catalogo", [
        _p("prodotti.view", "prodotti", schema="ext.view"),
        _p("categorie.view", "categorie", schema="ext.view")]),
    _p("amministrazione", "amministrazione", [
        _p("fatture.view", "fatture", schema="ext.view"),
        _p("pagamenti.view", "pagamenti", schema="ext.view")]),
    _p("sistema", "sistema", [
        _p("account.view", "account", schema="ext.view"),
        _p("cron.view", "cron", schema="ext.view")]),
]


class SitoDemo(Sito):
    def rinnova(self):
        pass

    def riprendi(self):
        return False

    def login(self, utente, password):
        if password != "demo":
            raise ErroreApi("login errato ( in demo la password e' 'demo' )")
        self.account = {"username": utente}
        return self.account

    def struttura(self):
        return {"status": "OK", "version": "demo", "account": self.account, "menu": {"admin": MENU}}

    def pagina(self, id, view=None):
        # 56 anagrafiche finte, con le stesse colonne e classi della vista vera di glisdev
        if id != "anagrafica.view":
            raise ErroreApi("in demo c'e' solo anagrafica.view")
        vid = "demo-anagrafica"
        w = (view or {}).get(vid) or {}
        pg = w.get("__pager__") or {}
        rows = int(pg.get("rows") or 20)
        tutti = [{"id": i, "codice": f"C{i:04d}", "__label__": f"Cliente {i} &amp; figli",
                  "telefoni": f"051 {i:06d}", "mail": f"cliente{i}@esempio.it",
                  "categorie": "contatti &gt; clienti", "azioni": "<a href='#'>x</a>"} for i in range(1, 57)]
        if w.get("__search__"):
            tutti = [d for d in tutti if all(any(t.lower() in str(x).lower() for x in d.values())
                                             for t in w["__search__"].split())]
        for k, dr in reversed(list((w.get("__sort__") or {}).items())):
            tutti.sort(key=lambda d: d.get(k), reverse=dr == "DESC")
        tot = len(tutti)
        pages = max(1, -(-tot // rows))
        page = max(0, min(int(pg.get("page") or 0), pages - 1))
        dati = tutti[page * rows:(page + 1) * rows]
        return {"status": "OK", "pagina": id, "schema": "default.view.twig", "tabs": [id],
                "view": {"id": vid, "table": "anagrafica", "open": "anagrafica.form",
                         "cols": {"id": "#", "codice": "codice", "__label__": "contatto", "telefoni": "telefoni",
                                  "mail": "mail", "categorie": "categorie", "azioni": ""},
                         "class": {"id": "d-none", "telefoni": "d-none d-md-table-cell",
                                   "mail": "d-none d-md-table-cell"},
                         "data": dati, "pager": {"page": page, "rows": rows, "total": str(tot), "pages": pages}}}

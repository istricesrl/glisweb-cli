"""I comandi secchi ( Typer ). Senza sottocomando parte l'interfaccia Textual."""
from pathlib import Path

import typer

from . import config

app = typer.Typer(no_args_is_help=False, add_completion=False)


@app.callback(invoke_without_command=True)
def principale(
    ctx: typer.Context,
    config_file: Path = typer.Option(None, "--config-file", "-c", help="un file di config del deploy, o la sua radice ( sul server )"),
    codice: str = typer.Option(None, "--codice", "-k", help="codice deploy, o nome di un preset di ~/.glisweb-cli.rc ( senza: il preset di default, poi l'ultimo profilo )"),
    url: str = typer.Option(None, "--url", help="indirizzo del sito, se non si ricava dalla config"),
    stato: str = typer.Option("DEV", "--stato", help="DEV, TEST o PROD: quale url del sito usare"),
    demo: bool = typer.Option(False, "--demo", help="sito finto, senza rete: password 'demo'"),
):
    from . import api
    radice, cx, letti = config.carica(config_file) if config_file else (None, {}, [])
    ctx.obj = {"radice": radice, "cx": cx, "letti": letti}
    if ctx.invoked_subcommand is None:
        from .tui import GliswebApp
        from . import rc
        remoto = not (demo or url or config_file)
        # da remoto, i preset di ~/.glisweb-cli.rc compilano il login ( niente autologin )
        preset = rc.scegli(codice) if remoto else {}
        if preset:
            rc.avvisa_permessi()
            codice = preset.get("codice") or codice
        try:
            if demo:
                from .demo import SitoDemo
                sito = SitoDemo(url or "https://demo.glisweb/")
            elif url or config_file:
                sito = api.Sito(url or api.url_del_deploy(cx, stato))
            else:
                # da remoto: l'ultimo profilo salvato, o il login a tre campi col configserver
                sito = api.sito_del_profilo(codice)
        except api.ErroreApi as e:
            raise typer.BadParameter(str(e))
        GliswebApp(radice, cx, sito, remoto=remoto, codice=codice, preset=preset).run()


@app.command()
def configurazione(ctx: typer.Context, chiave: str = typer.Argument(None, help="p.es. db.default")):
    """Mostra i file letti e la configurazione fusa ( le password restano nascoste )."""
    import json
    o = ctx.obj
    if not o["radice"]:
        raise typer.BadParameter("serve -c con il percorso del deploy")
    typer.echo(f"radice: {o['radice']}")
    for f in o["letti"]:
        typer.echo(f"  letto: {f}")
    val = o["cx"]
    for k in (chiave.split(".") if chiave else []):
        val = val.get(k, {}) if isinstance(val, dict) else {}
    typer.echo(json.dumps(_nascondi(val), indent=2, ensure_ascii=False))


def _nascondi(v):
    if isinstance(v, dict):
        return {k: ("***" if "pass" in k.lower() else _nascondi(x)) for k, x in v.items()}
    return v

"""Legge la pila di configurazione di un deploy glisweb, nello stesso ordine di _src/_config.php."""
from __future__ import annotations

import glob
import json
from pathlib import Path

import yaml


def trova_radice(percorso: Path) -> Path:
    """Risale da un file o da una cartella fino alla radice del deploy ( quella con _src/_config.php )."""
    p = percorso.resolve()
    for d in [p, *p.parents]:
        if (d / "_src" / "_config.php").is_file():
            return d
    raise FileNotFoundError(f"nessun deploy glisweb sopra {percorso}")


def path2custom(radice: Path, rel: str) -> Path:
    """Come glisweb: la versione custom ( senza '_' davanti ) vince su quella standard."""
    # TODO: replicare path2custom() di glisweb per intero; per ora il percorso tale e quale
    return radice / rel


def fondi(a: dict, b: dict) -> dict:
    """array_replace_recursive di PHP."""
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            fondi(a[k], v)
        else:
            a[k] = v
    return a


def _pila(radice: Path, ext: str) -> list[Path]:
    fissi = ["src/config/ext/config", "src/config/ext/shadow", "src/config", "src/shadow"]
    pila = [path2custom(radice, f"{f}.{ext}") for f in fissi]
    for cartella in ("src/config/ext", "src"):
        pila += sorted(Path(x) for x in glob.glob(str(radice / cartella / f"config.*.{ext}")))
    return pila


def carica(percorso: Path) -> tuple[Path, dict, list[Path]]:
    """Restituisce radice del deploy, configurazione fusa e file effettivamente letti."""
    radice = trova_radice(percorso)
    cx: dict = {}
    letti: list[Path] = []
    for ext, leggi in (("yaml", yaml.safe_load), ("json", json.loads)):
        for f in _pila(radice, ext):
            if f.is_file():
                fondi(cx, leggi(f.read_text()) or {})
                letti.append(f)
    return radice, cx, letti

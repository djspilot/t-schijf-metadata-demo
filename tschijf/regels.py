"""Vaste regels: project, fase en discipline afleiden uit de mapstructuur."""
import re
from dataclasses import dataclass
from pathlib import PurePosixPath


@dataclass
class Veld:
    waarde: str
    zekerheid: float  # 0.0 - 1.0
    bron: str = ""    # waar de waarde vandaan komt, voor het logboek


# Eerste alias is de officiële code; een map die precies zo heet scoort het hoogst.
FASEN = {
    "SO": ["so", "schetsontwerp"],
    "VO": ["vo", "voorlopig ontwerp", "voorontwerp"],
    "DO": ["do", "definitief ontwerp"],
    "UO": ["uo", "uitvoeringsontwerp", "bestek"],
    "Uitvoering": ["uitvoering", "realisatie", "bouw"],
    "Beheer": ["beheer", "nazorg", "oplevering"],
}
DISCIPLINES = {
    "Constructie": ["constructie", "constructief", "con"],
    "Civiel": ["civiel", "civ", "wegen"],
    "Installaties": ["installaties", "e&w", "ew", "elektra", "werktuigbouw"],
    "Geotechniek": ["geotechniek", "geo", "grondonderzoek"],
    "Projectmanagement": ["projectmanagement", "pm", "projectleiding"],
}
PROJECTMAP = re.compile(r"^(P\d{4}-\d{3})[ _-]+(\S.*)$")
PROJECTCODE = re.compile(r"(?<![A-Za-z0-9])(P\d{4}-\d{3})(?!\d)")


def _norm(mapnaam: str) -> str:
    """'03 DO' en '3_DO' worden 'do'."""
    return re.sub(r"^[\d\s._-]+", "", mapnaam.lower()).strip()


def _tokens(tekst: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9&]+", tekst.lower()) if t]


def _zoek_in_mappen(mappen: list[str], tabel: dict) -> Veld:
    beste = Veld("", 0.0, "geen map herkend")
    for mapnaam in mappen:
        naam = _norm(mapnaam)
        tokens = _tokens(naam)
        for waarde, aliassen in tabel.items():
            if naam == aliassen[0] or naam == waarde.lower():
                z = 0.95                      # map heet precies zo
            elif naam in aliassen:
                z = 0.85                      # bekende andere schrijfwijze
            elif any(a in tokens for a in aliassen):
                z = 0.70                      # woord komt voor in een langere mapnaam
            else:
                continue
            if z > beste.zekerheid:
                beste = Veld(waarde, z, f"map '{mapnaam}'")
    return beste


def leid_af(relpad: str) -> dict[str, Veld]:
    """Geef project, fase en discipline voor een pad relatief aan de schijf."""
    delen = PurePosixPath(relpad.replace("\\", "/")).parts
    mappen, naam = list(delen[:-1]), delen[-1]

    project = Veld("", 0.0, "geen projectmap")
    overige = []
    for m in mappen:
        hit = PROJECTMAP.match(m)
        if hit and not project.waarde:
            project = Veld(f"{hit.group(1)} {hit.group(2).strip()}", 1.0, f"map '{m}'")
        else:
            overige.append(m)
    if not project.waarde:
        hit = PROJECTCODE.search(naam)
        if hit:
            project = Veld(hit.group(1), 0.6, "projectcode in bestandsnaam")

    fase = _zoek_in_mappen(overige, FASEN)
    discipline = _zoek_in_mappen(overige, DISCIPLINES)
    if not discipline.waarde:
        tokens = _tokens(naam.rsplit(".", 1)[0])
        for waarde, aliassen in DISCIPLINES.items():
            if any(a in tokens for a in aliassen):
                discipline = Veld(waarde, 0.6, "bestandsnaam")
                break
    return {"project": project, "fase": fase, "discipline": discipline}

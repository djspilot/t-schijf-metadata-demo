"""Documenttype bepalen. Eén interface, twee implementaties.

Standaard: RegelClassificeerder (geen internet, geen sleutel).
Optioneel: LlmClassificeerder, aan te zetten met CLASSIFICATIE=llm.
"""
import json
import os
import re
import urllib.request
from typing import Protocol

from .regels import Veld

TYPES = ["tekening", "rapport", "offerte", "verslag", "berekening", "onbekend"]


class Classificeerder(Protocol):
    def classificeer(self, naam: str, tekst: str) -> Veld: ...


# per type: woorden in de bestandsnaam, extensies, woorden in de tekst
KENMERKEN = {
    "tekening": (["tek", "tekening", "doorsnede", "plattegrond", "situatie"],
                 [".dwg", ".dxf"],
                 ["tekeningnummer", "schaal 1:", "bladnummer", "getekend door"]),
    "rapport": (["rap", "rapport", "rapportage", "advies"], [],
                ["samenvatting", "conclusie", "aanbeveling", "inleiding"]),
    "offerte": (["offerte", "aanbieding", "prijsopgave"], [],
                ["offertenummer", "excl. btw", "geldigheid", "prijsopgave"]),
    "verslag": (["verslag", "notulen", "bouwverg"], [],
                ["aanwezig", "actiepunten", "agenda", "afwezig"]),
    "berekening": (["ber", "berekening", "sterkteberekening"], [],
                   ["uitgangspunten", "unity check", "kn/m", "toetsing"]),
}


class RegelClassificeerder:
    def classificeer(self, naam: str, tekst: str) -> Veld:
        stam, _, ext = naam.lower().rpartition(".")
        tokens = [t for t in re.split(r"[^a-z0-9]+", stam or naam.lower()) if t]
        laag = tekst.lower()
        naamtype = teksttype = ""
        meeste = 0
        for soort, (woorden, extensies, tekstwoorden) in KENMERKEN.items():
            if not naamtype and (any(w in tokens for w in woorden) or f".{ext}" in extensies):
                naamtype = soort
            treffers = sum(w in laag for w in tekstwoorden)
            if treffers > meeste:
                meeste, teksttype = treffers, soort
        if meeste < 2:
            teksttype = ""          # één los woord is te weinig bewijs

        if naamtype and naamtype == teksttype:
            return Veld(naamtype, 0.95, "bestandsnaam en tekst komen overeen")
        if naamtype and teksttype:
            return Veld(naamtype, 0.50, f"naam zegt {naamtype}, tekst lijkt {teksttype}")
        if naamtype:
            return Veld(naamtype, 0.80, "bestandsnaam of extensie")
        if teksttype:
            return Veld(teksttype, 0.70, "alleen woorden in de tekst")
        return Veld("onbekend", 0.10, "geen kenmerken gevonden")


class LlmClassificeerder:
    """Vraagt het type aan een taalmodel via een OpenAI-compatibele API.

    Werkt daardoor ook met een lokaal model (bijv. Ollama) binnen het eigen
    netwerk. Instellen met LLM_BASE_URL, LLM_MODEL en eventueel LLM_API_KEY.
    Bij elke fout valt de stap terug op de regels: de demo blijft werken.
    """

    def __init__(self):
        self.url = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
        self.model = os.environ.get("LLM_MODEL", "llama3.1")
        self.sleutel = os.environ.get("LLM_API_KEY", "")
        self.regels = RegelClassificeerder()

    def classificeer(self, naam: str, tekst: str) -> Veld:
        vraag = (
            f"Bepaal het documenttype. Kies uit: {', '.join(TYPES)}.\n"
            'Antwoord alleen met JSON: {"type": "...", "zekerheid": 0.0-1.0}\n\n'
            f"Bestandsnaam: {naam}\nTekst (begin):\n{tekst[:1500]}"
        )
        body = json.dumps({"model": self.model, "temperature": 0,
                           "messages": [{"role": "user", "content": vraag}]}).encode()
        kop = {"Content-Type": "application/json"}
        if self.sleutel:
            kop["Authorization"] = f"Bearer {self.sleutel}"
        try:
            verzoek = urllib.request.Request(f"{self.url}/chat/completions", body, kop)
            with urllib.request.urlopen(verzoek, timeout=30) as antwoord:
                inhoud = json.load(antwoord)["choices"][0]["message"]["content"]
            data = json.loads(re.search(r"\{.*\}", inhoud, re.S).group(0))
            soort = str(data["type"]).lower()
            if soort not in TYPES:
                raise ValueError(f"onbekend type {soort!r}")
            z = min(1.0, max(0.0, float(data["zekerheid"])))
            return Veld(soort, z, f"taalmodel {self.model}")
        except Exception as fout:  # netwerk, sleutel, vorm van het antwoord
            veld = self.regels.classificeer(naam, tekst)
            veld.bron = f"regels (taalmodel faalde: {type(fout).__name__})"
            return veld


def maak_classificeerder() -> Classificeerder:
    if os.environ.get("CLASSIFICATIE", "regels").lower() == "llm":
        return LlmClassificeerder()
    return RegelClassificeerder()

"""Vult demo-t-schijf/ met verzonnen bestanden van een verzonnen ingenieursbureau.

Alle projecten, plaatsen en bedrijven zijn bedacht. Er staan geen namen van
personen in. Gebruik: python maak_demodata.py [doelmap]
"""
import os
import random
import sys
from datetime import datetime
from pathlib import Path

A = "P2022-031 Fietsbrug Noorderplas"
B = "P2023-007 Gemaal Wilgenpolder"
C = "P2024-019 Herinrichting Merelplein"

# (pad, soort inhoud). Soort 'leeg' = nietszeggende tekst; '=pad' = exacte kopie.
BESTANDEN = [
    (f"{A}/01 SO/Constructie/TEK_SO_overzicht_variantA.dwg", "tekening"),
    (f"{A}/01 SO/Constructie/TEK_SO_overzicht_variantB.dwg", "tekening"),
    (f"{A}/01 SO/Projectmanagement/verslag startoverleg 2022-03-14.docx", "verslag"),
    (f"{A}/01 SO/Projectmanagement/Offerte grondonderzoek.pdf", "offerte"),
    (f"{A}/02 VO/Constructie/BER_hoofdligger_v1.pdf", "berekening"),
    (f"{A}/02 VO/Constructie/BER_hoofdligger_v2.pdf", "berekening"),
    (f"{A}/02 VO/Constructie/TEK-VO-101 langsdoorsnede.dwg", "tekening"),
    (f"{A}/02 VO/Constructie/TEK-VO-101 langsdoorsnede.pdf", "tekening"),
    (f"{A}/02 VO/Geotechniek/RAP geotechnisch advies concept.docx", "rapport"),
    (f"{A}/02 VO/Geotechniek/RAP geotechnisch advies DEF.pdf", "rapport"),
    (f"{A}/02 VO/Geotechniek/sonderingen.xlsx", "leeg"),
    (f"{A}/03 DO/Constructie/berekening landhoofd_v3.pdf", "berekening"),
    (f"{A}/03 DO/Constructie/Kopie van berekening landhoofd_v3.pdf",
     f"={A}/03 DO/Constructie/berekening landhoofd_v3.pdf"),
    (f"{A}/03 DO/Constructie/TEK-DO-201 landhoofd wapening.dwg", "tekening"),
    (f"{A}/03 DO/Constructie/TEK-DO-202 brugdek.dwg", "tekening"),
    (f"{A}/03 DO/Civiel/tekening aansluiting fietspad.pdf", "tekening"),
    (f"{A}/03 DO/Civiel/notitie.txt", "leeg"),
    (f"{A}/03 DO/PM/Verslag ontwerpoverleg nr 4.docx", "verslag"),
    (f"{A}/03 DO/verslag ontwerpoverleg nr 5 (1).docx", "verslag"),
    (f"{A}/05 Uitvoering/Projectleiding/bouwverg 01 verslag.docx", "verslag"),
    (f"{A}/05 Uitvoering/Projectleiding/bouwverg 02 verslag.docx", "verslag"),
    (f"{A}/05 Uitvoering/Projectleiding/offerte_aannemer_DEF2.pdf", "offerte"),
    (f"{A}/05 Uitvoering/IMG_2231.jpg", "leeg"),
    (f"{A}/diversen/scan0042.pdf", "offerte"),
    (f"{A}/diversen/Nieuw document.txt", "leeg"),
    (f"{A}/diversen/rapport ecologie quickscan.pdf", "verslag"),   # naam en inhoud spreken elkaar tegen

    (f"{B}/1_SO/Civiel/rapport variantenstudie.pdf", "rapport"),
    (f"{B}/1_SO/PM/Overleg waterbeheer notulen.docx", "verslag"),
    (f"{B}/2_VO/Installaties/BER pompcapaciteit.xlsx", "leeg"),
    (f"{B}/2_VO/Installaties/berekening pompcapaciteit toelichting.pdf", "berekening"),
    (f"{B}/2_VO/Installaties/TEK_VO_pompkelder.dwg", "tekening"),
    (f"{B}/2_VO/Installaties/offerte pompen leverancier A.pdf", "offerte"),
    (f"{B}/2_VO/Installaties/offerte pompen leverancier B.pdf", "offerte"),
    (f"{B}/2_VO/constructief/sterkteberekening kelderwand v1.pdf", "berekening"),
    (f"{B}/2_VO/constructief/sterkteberekening kelderwand v2.pdf", "berekening"),
    (f"{B}/3_DO/E&W/TEK-DO-310 schakelkast.dwg", "tekening"),
    (f"{B}/3_DO/E&W/TEK-DO-311 leidingwerk.pdf", "tekening"),
    (f"{B}/3_DO/E&W/Rapport geluidsonderzoek.docx", "rapport"),
    (f"{B}/3_DO/Geo/RAP_bemalingsadvies.pdf", "rapport"),
    (f"{B}/3_DO/Geo/RAP_bemalingsadvies (2).pdf", f"={B}/3_DO/Geo/RAP_bemalingsadvies.pdf"),
    (f"{B}/Uitvoeringsontwerp/bestek concept.docx", "leeg"),
    (f"{B}/Uitvoeringsontwerp/TEK-UO-401 detail vloer.dwg", "tekening"),
    (f"{B}/oud/TEK_VO_pompkelder_OUD.dwg", "tekening"),
    (f"{B}/oud/verslag 2023-02 oud.docx", "verslag"),
    (f"{B}/planning.xlsx", "leeg"),
    (f"{B}/memo aan projectleider.txt", "leeg"),

    (f"{C}/SO/Verslag bewonersavond.docx", "verslag"),
    (f"{C}/SO/Civiel/TEK_SO_situatie.pdf", "tekening"),
    (f"{C}/VO/Civiel/TEK_VO_plattegrond_v1.dwg", "tekening"),
    (f"{C}/VO/Civiel/TEK_VO_plattegrond_v2.dwg", "tekening"),
    (f"{C}/VO/Civiel/berekening riolering.pdf", "berekening"),
    (f"{C}/VO/Civiel/Rapport verkeerstelling.pdf", "rapport"),
    (f"{C}/VO/PM/offerte landmeter.pdf", "offerte"),
    (f"{C}/VO/PM/Verslag projectteam 3.docx", "verslag"),
    (f"{C}/Nieuwe map/Document1.docx", "rapport"),
    (f"{C}/Nieuwe map/tekening.pdf", "tekening"),

    ("_inbox/scan0007.pdf", "leeg"),
    ("_inbox/offerte onbekend project.pdf", "offerte"),
    ("_inbox/P2022-031 verslag nazorg.docx", "verslag"),
    ("Algemeen/Sjablonen/Sjabloon verslag.docx", "verslag"),
    ("Algemeen/Sjablonen/Sjabloon rapport.docx", "rapport"),
]

TEKST = {
    "tekening": ["Tekeningnummer: {nr}", "Schaal 1:{schaal}", "Bladnummer 1 van 1",
                 "Getekend door: tekenkamer", "Onderdeel: {titel}", "Status: ter beoordeling"],
    "rapport": ["Inleiding", "Dit rapport beschrijft het onderzoek voor {titel}.",
                "Samenvatting", "De resultaten voldoen aan de gestelde eisen.",
                "Conclusie", "Het ontwerp is haalbaar binnen de randvoorwaarden.",
                "Aanbeveling: nader onderzoek in de volgende fase."],
    "offerte": ["Offertenummer: OF-{nr}", "Betreft: {titel}",
                "Hierbij ontvangt u onze prijsopgave voor de gevraagde werkzaamheden.",
                "Totaal: EUR {bedrag},00 excl. btw", "Geldigheid: 30 dagen na dagtekening."],
    "verslag": ["Verslag overleg: {titel}", "Aanwezig: projectleider, constructeur, opdrachtgever",
                "Afwezig: geen", "Agenda: 1. opening 2. voortgang 3. planning 4. rondvraag",
                "Actiepunten: tekeningen bijwerken, planning rondsturen."],
    "berekening": ["Berekening: {titel}", "Uitgangspunten: belastingen volgens projectnorm.",
                   "Permanente belasting 12,5 kN/m, veranderlijke belasting 5,0 kN/m.",
                   "Toetsing uiterste grenstoestand.", "Unity check 0,{uc} - voldoet."],
    "leeg": ["{titel}", "Zie eerdere mail.", "Nog aanvullen."],
}


def _regels(soort: str, pad: str, rnd: random.Random) -> list[str]:
    titel = Path(pad).stem
    project = pad.split("/")[0] if pad.startswith("P2") else "algemeen"
    waarden = dict(titel=titel, nr=rnd.randint(1000, 9999), schaal=rnd.choice([50, 100, 200, 500]),
                   bedrag=rnd.randint(4, 180) * 500, uc=rnd.randint(55, 97))
    kop = ["Ingenieursbureau Waterstede (verzonnen demodata)", f"Project: {project}", ""]
    return kop + [r.format(**waarden) for r in TEKST[soort]]


def _schrijf(pad: Path, soort: str, rel: str, rnd: random.Random):
    regels = _regels(soort, rel, rnd)
    ext = pad.suffix.lower()
    if ext == ".txt":
        pad.write_text("\n".join(regels), encoding="utf-8")
    elif ext == ".docx":
        from docx import Document
        doc = Document()
        for r in regels:
            doc.add_paragraph(r)
        doc.save(pad)
    elif ext == ".pdf":
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        for r in regels:
            pdf.cell(0, 7, r, new_x="LMARGIN", new_y="NEXT")
        pdf.output(str(pad))
    else:  # dwg, xlsx, jpg: nepinhoud, alleen om een bestand van die soort te hebben
        pad.write_bytes(f"NEPBESTAND {rel}\n".encode() + rnd.randbytes(rnd.randint(2000, 60000)))


def maak(doelmap: Path) -> int:
    doelmap = Path(doelmap)
    rnd = random.Random(2024)
    for rel, soort in BESTANDEN:
        pad = doelmap / rel
        pad.parent.mkdir(parents=True, exist_ok=True)
        if soort.startswith("="):
            pad.write_bytes((doelmap / soort[1:]).read_bytes())
        else:
            _schrijf(pad, soort, rel, rnd)
        jaar = int(rel[1:5]) if rel.startswith("P2") else 2021
        moment = datetime(jaar, 1, 1).timestamp() + rnd.randint(30, 700) * 86400 + rnd.randint(8, 17) * 3600
        os.utime(pad, (moment, moment))
    return len(BESTANDEN)


if __name__ == "__main__":
    doel = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "demo-t-schijf")
    print(f"{maak(doel)} verzonnen bestanden geschreven naar {doel}")

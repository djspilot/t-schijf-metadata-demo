import pytest

from tschijf.classificatie import LlmClassificeerder, RegelClassificeerder
from tschijf.regels import leid_af

P = "P2022-031 Fietsbrug Noorderplas"


@pytest.mark.parametrize("pad, project, fase, discipline", [
    (f"{P}/03 DO/Constructie/x.pdf", P, "DO", "Constructie"),
    (f"{P}/3_DO/E&W/x.dwg", P, "DO", "Installaties"),
    (f"{P}/02-VO/Geo/x.pdf", P, "VO", "Geotechniek"),
    (f"{P}/Uitvoeringsontwerp/x.docx", P, "UO", ""),
    (f"{P}/05 Uitvoering/x.docx", P, "Uitvoering", ""),
    (f"{P}/VO/PM/x.pdf", P, "VO", "Projectmanagement"),
    (f"{P}/diversen/x.pdf", P, "", ""),
    ("Algemeen/Sjablonen/x.docx", "", "", ""),
])
def test_waarden_uit_mapstructuur(pad, project, fase, discipline):
    v = leid_af(pad)
    assert (v["project"].waarde, v["fase"].waarde, v["discipline"].waarde) == (project, fase, discipline)


def test_zekerheid_volgt_de_kwaliteit_van_de_map():
    exact = leid_af(f"{P}/03 DO/Constructie/x.pdf")
    assert exact["project"].zekerheid == 1.0
    assert exact["fase"].zekerheid == 0.95
    assert exact["discipline"].zekerheid == 0.95
    assert leid_af(f"{P}/Uitvoeringsontwerp/x.pdf")["fase"].zekerheid == 0.85   # andere schrijfwijze
    assert leid_af(f"{P}/DO definitief/x.pdf")["fase"].zekerheid == 0.70        # woord in langere naam
    assert leid_af(f"{P}/diversen/x.pdf")["fase"].zekerheid == 0.0


def test_projectmap_telt_niet_mee_als_fase_of_discipline():
    v = leid_af("P2024-001 Bouw nieuw gemaal/x.pdf")   # 'bouw' is ook een alias voor Uitvoering
    assert v["project"].waarde == "P2024-001 Bouw nieuw gemaal"
    assert v["fase"].waarde == ""


def test_projectcode_in_bestandsnaam_is_onzeker():
    v = leid_af("_inbox/P2022-031 verslag nazorg.docx")
    assert v["project"].waarde == "P2022-031"
    assert v["project"].zekerheid == 0.6


def test_discipline_uit_bestandsnaam_als_map_ontbreekt():
    v = leid_af(f"{P}/03 DO/TEK_CON_ligger.dwg")
    assert (v["discipline"].waarde, v["discipline"].zekerheid) == ("Constructie", 0.6)


def test_windows_pad_werkt_ook():
    assert leid_af(f"{P}\\03 DO\\Civiel\\x.pdf")["discipline"].waarde == "Civiel"


@pytest.mark.parametrize("naam, tekst, soort, z", [
    ("TEK-DO-201 wapening.dwg", "", "tekening", 0.80),
    ("verslag overleg.docx", "Aanwezig: a. Agenda: b. Actiepunten: c.", "verslag", 0.95),
    ("scan0042.pdf", "Offertenummer 12. Totaal excl. btw. Geldigheid 30 dagen.", "offerte", 0.70),
    ("rapport quickscan.pdf", "Aanwezig: a. Agenda: b. Actiepunten: c.", "rapport", 0.50),
    ("Nieuw document.txt", "Zie eerdere mail.", "onbekend", 0.10),
])
def test_regelclassificatie(naam, tekst, soort, z):
    v = RegelClassificeerder().classificeer(naam, tekst)
    assert (v.waarde, v.zekerheid) == (soort, z)


def test_llm_valt_terug_op_regels_zonder_bereikbare_dienst(monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "http://127.0.0.1:9")   # niets luistert hier
    v = LlmClassificeerder().classificeer("offerte pompen.pdf", "")
    assert v.waarde == "offerte" and "regels" in v.bron

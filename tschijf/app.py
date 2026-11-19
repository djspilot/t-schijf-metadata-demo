"""Webinterface: overzicht, controlelijst en logboek."""
import os
from html import escape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from . import pijplijn
from .classificatie import TYPES, maak_classificeerder
from .doel import NepSharePoint
from .regels import DISCIPLINES, FASEN

BASIS = Path(__file__).resolve().parent.parent
BRON = Path(os.environ.get("TSCHIJF_BRON", BASIS / "demo-t-schijf"))
DOELMAP = Path(os.environ.get("TSCHIJF_DOEL", BASIS / "demo-sharepoint"))
WERKDB = Path(os.environ.get("TSCHIJF_WERKDB", BASIS / "demo-werk.db"))

app = FastAPI(title="T-schijf metadata-demo")
classificeerder = maak_classificeerder()
doel = NepSharePoint(DOELMAP, bron=BRON)   # later: GraphSharePoint() of AlfrescoDoel()


def db():
    return pijplijn.open_db(WERKDB)


@app.on_event("startup")
def eerste_scan():
    with db() as con:
        if con.execute("SELECT COUNT(*) FROM bestanden").fetchone()[0] == 0:
            pijplijn.scan(BRON, con, classificeerder)


CSS = """
:root{--bg:#f4f6f8;--kaart:#fff;--tekst:#1c2733;--zacht:#5b6b7b;--lijn:#dde3ea;
--accent:#0b5cad;--goed:#1a7f4b;--let:#b25e00;--fout:#b3261e}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:var(--bg);color:var(--tekst)}
header{background:#12324f;color:#fff;padding:14px 24px;display:flex;gap:28px;align-items:center;flex-wrap:wrap}
header b{font-size:17px}nav a{color:#cfe0f1;text-decoration:none;margin-right:18px;padding:4px 0}
nav a.actief{color:#fff;border-bottom:2px solid #fff}
.demo{background:#fff4d6;border-bottom:1px solid #ecd9a0;padding:6px 24px;font-size:13px}
main{max-width:1100px;margin:0 auto;padding:24px 16px}
h1{font-size:22px;margin:0 0 16px}h2{font-size:16px;margin:28px 0 10px}
.tegels{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px}
.tegel,.kaart{background:var(--kaart);border:1px solid var(--lijn);border-radius:8px;padding:16px}
.tegel .getal{font-size:34px;font-weight:650;line-height:1.1}.tegel .naam{color:var(--zacht)}
.stappen{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:0;padding:0;list-style:none}
.stappen li{background:var(--kaart);border:1px solid var(--lijn);border-radius:8px;padding:12px 14px}
.stappen b{display:block}.stappen span{color:var(--zacht);font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--kaart);border:1px solid var(--lijn);border-radius:8px;overflow:hidden}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--lijn);vertical-align:top;font-size:14px}
th{background:#eaf0f6;font-weight:600}tr:last-child td{border-bottom:0}
.wikkel{overflow-x:auto}.pad{font-family:ui-monospace,monospace;font-size:13px;overflow-wrap:anywhere}.nw{white-space:nowrap}
.knop{background:var(--accent);color:#fff;border:0;border-radius:6px;padding:8px 14px;font:inherit;cursor:pointer}
.knop.stil{background:#fff;color:var(--tekst);border:1px solid var(--lijn)}
.acties{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.kaart{margin-bottom:14px}.kaart .reden{color:var(--let);font-size:13px;margin:4px 0}
.kaart .fragment{color:var(--zacht);font-size:13px;margin:6px 0 10px;font-style:italic}
.velden{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-bottom:12px}
label{display:block;font-size:13px;color:var(--zacht)}
input,select{width:100%;padding:6px 8px;border:1px solid var(--lijn);border-radius:6px;font:inherit;background:#fff}
.z{font-size:12px;border-radius:10px;padding:1px 7px;margin-left:6px;color:#fff;background:var(--goed)}
.z.laag{background:var(--fout)}
.stap{font-size:12px;border-radius:4px;padding:1px 7px;background:#e3ebf3}
.leeg{color:var(--zacht);padding:24px;text-align:center}
"""


def pagina(titel: str, actief: str, inhoud: str) -> HTMLResponse:
    links = "".join(
        f'<a href="{url}" class="{"actief" if url == actief else ""}">{naam}</a>'
        for url, naam in (("/", "Overzicht"), ("/controle", "Controlelijst"), ("/logboek", "Logboek")))
    return HTMLResponse(
        f"<!doctype html><html lang=nl><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{escape(titel)} - T-schijf demo</title><style>{CSS}</style>"
        f"<header><b>T-schijf → documentomgeving</b><nav>{links}</nav></header>"
        f"<div class=demo>Demo met volledig verzonnen data en een nagemaakte SharePoint. "
        f"De bronschijf wordt alleen gelezen.</div><main><h1>{escape(titel)}</h1>{inhoud}</main></html>")


def score(z: float) -> str:
    return f'<span class="z{" laag" if z < pijplijn.DREMPEL else ""}">{z:.0%}</span>'


def tabel(koppen: list[str], rijen: list[list[str]]) -> str:
    if not rijen:
        return '<div class="kaart leeg">Nog niets.</div>'
    kop = "".join(f"<th>{k}</th>" for k in koppen)
    lijf = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rijen)
    return f'<div class=wikkel><table><tr>{kop}</tr>{lijf}</table></div>'


@app.get("/", response_class=HTMLResponse)
def overzicht():
    with db() as con:
        tel = dict(con.execute("SELECT status, COUNT(*) FROM bestanden GROUP BY status").fetchall())
        per_type = con.execute(
            "SELECT documenttype, COUNT(*) n FROM bestanden GROUP BY 1 ORDER BY n DESC").fetchall()
        per_project = con.execute(
            "SELECT COALESCE(NULLIF(project,''),'(geen project herkend)') p, COUNT(*) n, "
            "SUM(status='gespiegeld') g, SUM(status='wacht_controle') w "
            "FROM bestanden GROUP BY 1 ORDER BY 1").fetchall()
    totaal = sum(tel.values())
    tegels = "".join(
        f'<div class=tegel><div class=getal>{n}</div><div class=naam>{naam}</div></div>'
        for naam, n in (("Gescand", totaal), ("Gespiegeld", tel.get("gespiegeld", 0)),
                        ("Wacht op controle", tel.get("wacht_controle", 0)),
                        ("Goedgekeurd, nog te spiegelen", tel.get("goedgekeurd", 0)),
                        ("Overgeslagen", tel.get("overgeslagen", 0))))
    stappen = "".join(
        f"<li><b>{i}. {naam}</b><span>{uitleg}</span></li>" for i, (naam, uitleg) in enumerate((
            ("Uitlezen", "Pad, naam, datum, grootte en tekst per bestand."),
            ("Metadata toekennen", "Project, fase en discipline uit de mappen; type via classificatie."),
            ("Controle", f"Zekerheid onder {pijplijn.DREMPEL:.0%}, dubbelen en oude versies gaan langs een mens."),
            ("Spiegelen", "Goedgekeurde bestanden worden gekopieerd. De bron blijft ongewijzigd.")), 1))
    sp = doel.inhoud(8)
    inhoud = f"""
<div class=tegels>{tegels}</div>
<div class=acties>
 <form method=post action=/scan><button class=knop>Schijf opnieuw uitlezen</button></form>
 <form method=post action=/spiegel><button class=knop>Goedgekeurde bestanden spiegelen</button></form>
 <a class="knop stil" href=/controle style="text-decoration:none">Naar de controlelijst</a>
</div>
<h2>Hoe het werkt</h2><ul class=stappen>{stappen}</ul>
<h2>Per project</h2>
{tabel(["Project", "Bestanden", "Gespiegeld", "Wacht op controle"],
       [[escape(r["p"]), r["n"], r["g"], r["w"]] for r in per_project])}
<h2>Per documenttype</h2>
{tabel(["Documenttype", "Bestanden"], [[escape(r["documenttype"]), r["n"]] for r in per_type])}
<h2>Laatst gespiegeld naar de nagemaakte SharePoint</h2>
{tabel(["Naam", "Project", "Fase", "Discipline", "Documenttype", "Locatie in bibliotheek"],
       [[escape(r["naam"]), escape(r["project"]), escape(r["fase"]), escape(r["discipline"]),
         escape(r["documenttype"]), f'<span class=pad>{escape(r["doelpad"])}</span>'] for r in sp])}
<p style="color:var(--zacht);font-size:13px">Bron: <span class=pad>{escape(str(BRON))}</span> ·
Classificatie: {escape(type(classificeerder).__name__)} · Doel: {escape(type(doel).__name__)}</p>"""
    return pagina("Overzicht", "/", inhoud)


def keuze(naam: str, opties: list[str], huidig: str) -> str:
    alle = [""] + opties + ([huidig] if huidig and huidig not in opties else [])
    return f"<select name={naam}>" + "".join(
        f'<option value="{escape(o)}"{" selected" if o == huidig else ""}>{escape(o) or "(leeg)"}</option>'
        for o in alle) + "</select>"


@app.get("/controle", response_class=HTMLResponse)
def controle():
    with db() as con:
        rijen = con.execute(
            "SELECT * FROM bestanden WHERE status='wacht_controle' ORDER BY pad").fetchall()
        projecten = [r[0] for r in con.execute(
            "SELECT DISTINCT project FROM bestanden WHERE project<>'' ORDER BY 1")]
    if not rijen:
        return pagina("Controlelijst", "/controle",
                      '<div class="kaart leeg">Niets te controleren. Alles is beoordeeld.</div>')
    lijst = "".join(f'<option value="{escape(p)}">' for p in projecten)
    kaarten = [f"<p>{len(rijen)} bestanden wachten op een mens. Pas aan waar nodig en keur goed, "
               f"of sla over als het bestand niet mee hoeft.</p><datalist id=projecten>{lijst}</datalist>"]
    for r in rijen:
        laag = [v for v in pijplijn.VELDEN if r[f"{v}_z"] < pijplijn.DREMPEL]
        redenen = ([f"lage zekerheid: {', '.join(laag)}"] if laag else []) + \
                  ([r["opmerking"]] if r["opmerking"] else [])
        fragment = f'<div class=fragment>“{escape(r["fragment"][:220])}…”</div>' if r["fragment"] else \
                   '<div class=fragment>Geen tekst leesbaar uit dit bestand.</div>'
        kaarten.append(f"""
<form class=kaart method=post action=/controle/{r["id"]}>
 <div class=pad>{escape(r["pad"])}</div>
 <div class=reden>{escape("; ".join(redenen))}</div>{fragment}
 <div class=velden>
  <label>Project {score(r["project_z"])}
   <input name=project list=projecten value="{escape(r["project"])}"></label>
  <label>Fase {score(r["fase_z"])}{keuze("fase", list(FASEN), r["fase"])}</label>
  <label>Discipline {score(r["discipline_z"])}{keuze("discipline", list(DISCIPLINES), r["discipline"])}</label>
  <label>Documenttype {score(r["documenttype_z"])}{keuze("documenttype", TYPES, r["documenttype"])}</label>
 </div>
 <button class=knop name=actie value=goedkeuren>Goedkeuren</button>
 <button class="knop stil" name=actie value=overslaan>Overslaan</button>
</form>""")
    return pagina("Controlelijst", "/controle", "".join(kaarten))


@app.post("/controle/{bestand_id}")
async def beoordeel(bestand_id: int, request: Request):
    formulier = {k: v[0] for k, v in parse_qs((await request.body()).decode(),
                                              keep_blank_values=True).items()}
    with db() as con:
        if formulier.get("actie") == "overslaan":
            pijplijn.sla_over(con, bestand_id)
        else:
            pijplijn.keur_goed(con, bestand_id, formulier)
    return RedirectResponse("/controle", status_code=303)


@app.post("/scan")
def scan():
    with db() as con:
        pijplijn.scan(BRON, con, classificeerder)
    return RedirectResponse("/", status_code=303)


@app.post("/spiegel")
def spiegel():
    with db() as con:
        pijplijn.spiegel(BRON, con, doel)
    return RedirectResponse("/", status_code=303)


@app.get("/logboek", response_class=HTMLResponse)
def logboek():
    with db() as con:
        rijen = con.execute("SELECT * FROM logboek ORDER BY id DESC LIMIT 400").fetchall()
    return pagina("Logboek", "/logboek",
                  "<p>Elke stap per bestand, nieuwste bovenaan (maximaal 400 regels).</p>" +
                  tabel(["Tijd", "Stap", "Bestand", "Wat er gebeurde"],
                        [[f'<span class=nw>{r["tijd"].replace("T", " ")}</span>',f'<span class=stap>{r["stap"]}</span>',
                          f'<span class=pad>{escape(r["pad"])}</span>', escape(r["detail"])]
                         for r in rijen]))

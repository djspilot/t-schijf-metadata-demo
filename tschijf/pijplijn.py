"""De vier stappen: uitlezen, metadata toekennen, controle, spiegelen.

De bronschijf wordt alleen geopend om te lezen. Alles wat de tool bijhoudt
staat in een eigen werkdatabase buiten de bron.
"""
import hashlib
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from .classificatie import Classificeerder
from .doel import Doelsysteem
from .regels import leid_af

DREMPEL = float(os.environ.get("ZEKERHEID_DREMPEL", "0.75"))
VELDEN = ("project", "fase", "discipline", "documenttype")

SCHEMA = """
CREATE TABLE IF NOT EXISTS bestanden(
  id INTEGER PRIMARY KEY, pad TEXT UNIQUE, naam TEXT, gewijzigd TEXT, grootte INTEGER,
  sha256 TEXT, fragment TEXT,
  project TEXT, project_z REAL, fase TEXT, fase_z REAL,
  discipline TEXT, discipline_z REAL, documenttype TEXT, documenttype_z REAL,
  opmerking TEXT, status TEXT);
CREATE TABLE IF NOT EXISTS logboek(
  id INTEGER PRIMARY KEY, tijd TEXT, stap TEXT, pad TEXT, detail TEXT);
"""
VERSIE = re.compile(r"[ _-]?v(\d+)$", re.I)
OUD = re.compile(r"(?<![a-z])(oud|old|vervallen|kopie|archief)(?![a-z])", re.I)


def open_db(pad: Path) -> sqlite3.Connection:
    con = sqlite3.connect(pad)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def log(con, stap: str, pad: str, detail: str):
    con.execute("INSERT INTO logboek(tijd, stap, pad, detail) VALUES(?,?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), stap, pad, detail))


def lees_tekst(pad: Path) -> str:
    """Tekst uit txt, pdf en docx. Andere soorten: lege tekst."""
    ext = pad.suffix.lower()
    try:
        if ext == ".txt":
            with open(pad, "rb") as f:
                return f.read(20000).decode("utf-8", errors="replace")
        if ext == ".pdf":
            from pypdf import PdfReader
            with open(pad, "rb") as f:
                return "\n".join((p.extract_text() or "") for p in PdfReader(f).pages[:3])
        if ext == ".docx":
            from docx import Document
            with open(pad, "rb") as f:
                return "\n".join(p.text for p in Document(f).paragraphs)
    except Exception:
        return ""       # beschadigd of beveiligd bestand: verder zonder tekst
    return ""


def _sha256(pad: Path) -> str:
    h = hashlib.sha256()
    with open(pad, "rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def scan(bron: Path, con: sqlite3.Connection, classificeerder: Classificeerder) -> int:
    """Stap 1 en 2. Geeft het aantal nieuwe of gewijzigde bestanden terug."""
    bron = Path(bron)
    gevonden = []
    for map_, mappen, namen in os.walk(bron):
        mappen.sort()
        for naam in sorted(namen):
            pad = Path(map_) / naam
            gevonden.append((pad.relative_to(bron).as_posix(), pad, pad.stat(), _sha256(pad)))

    eerste_met_hash: dict[str, str] = {}
    hoogste_versie: dict[tuple, tuple[int, str]] = {}
    for rel, pad, _, sha in gevonden:
        if len(rel) < len(eerste_met_hash.get(sha, rel + " ")):
            eerste_met_hash[sha] = rel        # kortste pad geldt als origineel
        hit = VERSIE.search(pad.stem)
        if hit:
            sleutel = (pad.parent, VERSIE.sub("", pad.stem).lower(), pad.suffix.lower())
            if int(hit.group(1)) > hoogste_versie.get(sleutel, (0, ""))[0]:
                hoogste_versie[sleutel] = (int(hit.group(1)), pad.name)

    nieuw = 0
    for rel, pad, st, sha in gevonden:
        bekend = con.execute("SELECT sha256 FROM bestanden WHERE pad=?", (rel,)).fetchone()
        if bekend and bekend["sha256"] == sha:
            continue                      # al verwerkt; besluiten van mensen blijven staan
        tekst = lees_tekst(pad)
        velden = leid_af(rel)
        velden["documenttype"] = classificeerder.classificeer(pad.name, tekst)

        opmerkingen = []
        if eerste_met_hash[sha] != rel:
            opmerkingen.append(f"dubbel van {eerste_met_hash[sha]}")
        hit = VERSIE.search(pad.stem)
        if hit:
            sleutel = (pad.parent, VERSIE.sub("", pad.stem).lower(), pad.suffix.lower())
            hoogste, naam_hoogste = hoogste_versie[sleutel]
            if int(hit.group(1)) < hoogste:
                opmerkingen.append(f"oude versie (nieuwer: {naam_hoogste})")
        if not opmerkingen and OUD.search(rel):
            opmerkingen.append("mogelijk oude versie of kopie")

        laag = [v for v in VELDEN if velden[v].zekerheid < DREMPEL]
        status = "wacht_controle" if laag or opmerkingen else "goedgekeurd"
        rij = {"pad": rel, "naam": pad.name, "grootte": st.st_size, "sha256": sha,
               "gewijzigd": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
               "fragment": " ".join(tekst.split())[:300],
               "opmerking": "; ".join(opmerkingen), "status": status}
        for v in VELDEN:
            rij[v], rij[f"{v}_z"] = velden[v].waarde, velden[v].zekerheid
        kolommen = ", ".join(rij)
        con.execute(f"INSERT OR REPLACE INTO bestanden({kolommen}) "
                    f"VALUES({', '.join(':' + k for k in rij)})", rij)
        samenvatting = ", ".join(
            f"{v}={velden[v].waarde or '?'} ({velden[v].zekerheid:.0%}, {velden[v].bron})"
            for v in VELDEN)
        log(con, "metadata", rel, samenvatting)
        if status == "wacht_controle":
            reden = [f"lage zekerheid: {', '.join(laag)}"] if laag else []
            log(con, "controle", rel, "naar controlelijst: " + "; ".join(reden + opmerkingen))
        nieuw += 1
    log(con, "uitlezen", "", f"{len(gevonden)} bestanden gelezen, {nieuw} nieuw of gewijzigd")
    con.commit()
    return nieuw


def keur_goed(con, bestand_id: int, waarden: dict):
    """Stap 3: een mens keurt goed, eventueel met aangepaste waarden."""
    rij = con.execute("SELECT * FROM bestanden WHERE id=?", (bestand_id,)).fetchone()
    if not rij or rij["status"] != "wacht_controle":
        return
    aangepast = []
    for v in VELDEN:
        nieuw = (waarden.get(v) or "").strip()
        if nieuw != rij[v]:
            aangepast.append(f"{v}: '{rij[v]}' -> '{nieuw}'")
        con.execute(f"UPDATE bestanden SET {v}=?, {v}_z=1.0 WHERE id=?", (nieuw, bestand_id))
    con.execute("UPDATE bestanden SET status='goedgekeurd' WHERE id=?", (bestand_id,))
    log(con, "controle", rij["pad"],
        "goedgekeurd door mens" + (", aangepast: " + "; ".join(aangepast) if aangepast else ""))
    con.commit()


def sla_over(con, bestand_id: int):
    rij = con.execute("SELECT * FROM bestanden WHERE id=?", (bestand_id,)).fetchone()
    if not rij or rij["status"] != "wacht_controle":
        return
    con.execute("UPDATE bestanden SET status='overgeslagen' WHERE id=?", (bestand_id,))
    log(con, "controle", rij["pad"], "overgeslagen door mens: wordt niet gespiegeld")
    con.commit()


def spiegel(bron: Path, con, doel: Doelsysteem) -> int:
    """Stap 4: goedgekeurde bestanden naar het doelsysteem kopiëren."""
    aantal = 0
    for rij in con.execute("SELECT * FROM bestanden WHERE status='goedgekeurd'").fetchall():
        metadata = {"bronpad": rij["pad"], **{k: rij[k] for k in
                    ("naam", "gewijzigd", "grootte", "sha256", *VELDEN)}}
        try:
            doelpad = doel.schrijf(Path(bron) / rij["pad"], metadata)
        except OSError as fout:
            log(con, "spiegelen", rij["pad"], f"mislukt: {fout}")
            continue
        con.execute("UPDATE bestanden SET status='gespiegeld' WHERE id=?", (rij["id"],))
        log(con, "spiegelen", rij["pad"], f"gekopieerd naar {doelpad}")
        aantal += 1
    con.commit()
    return aantal

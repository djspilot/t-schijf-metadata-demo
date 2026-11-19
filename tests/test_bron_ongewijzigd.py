"""Garantie: de hele keten (scan, controle, spiegelen) wijzigt de bron nooit."""
import hashlib
import os

import pytest

from maak_demodata import maak
from tschijf import pijplijn
from tschijf.classificatie import RegelClassificeerder
from tschijf.doel import NepSharePoint


def afdruk(map_):
    """Alles wat aan de bron kan veranderen: paden, inhoud, grootte, wijzigingsdatum."""
    uit = {}
    for wortel, mappen, namen in os.walk(map_):
        for n in mappen + namen:
            p = os.path.join(wortel, n)
            st = os.stat(p)
            inhoud = "" if os.path.isdir(p) else hashlib.sha256(open(p, "rb").read()).hexdigest()
            uit[os.path.relpath(p, map_)] = (inhoud, st.st_size if inhoud else 0, st.st_mtime_ns)
    return uit


def draai_keten(bron, tmp_path):
    con = pijplijn.open_db(tmp_path / "werk.db")
    doel = NepSharePoint(tmp_path / "sharepoint", bron=bron)
    pijplijn.scan(bron, con, RegelClassificeerder())
    wachtend = con.execute("SELECT * FROM bestanden WHERE status='wacht_controle'").fetchall()
    for i, r in enumerate(wachtend):        # mens: afwisselend overslaan en aangepast goedkeuren
        if i % 4 == 0:
            pijplijn.sla_over(con, r["id"])
        else:
            pijplijn.keur_goed(con, r["id"], {**dict(r), "documenttype": "rapport"})
    gespiegeld = pijplijn.spiegel(bron, con, doel)
    pijplijn.scan(bron, con, RegelClassificeerder())    # tweede ronde hoort niets te doen
    return con, doel, len(wachtend), gespiegeld


def test_bron_blijft_byte_voor_byte_gelijk(tmp_path):
    bron = tmp_path / "t-schijf"
    aantal = maak(bron)
    voor = afdruk(bron)

    con, doel, wachtend, gespiegeld = draai_keten(bron, tmp_path)

    assert afdruk(bron) == voor
    assert 0 < wachtend < aantal and gespiegeld > 0
    tel = dict(con.execute("SELECT status, COUNT(*) FROM bestanden GROUP BY status").fetchall())
    assert sum(tel.values()) == aantal
    assert tel["gespiegeld"] == gespiegeld == len(doel.inhoud(1000))
    assert "wacht_controle" not in tel


def test_keten_werkt_op_een_schijf_zonder_schrijfrechten(tmp_path):
    bron = tmp_path / "t-schijf"
    maak(bron)
    paden = [bron] + [os.path.join(w, n) for w, ms, ns in os.walk(bron) for n in ms + ns]
    for p in paden:
        os.chmod(p, 0o555 if os.path.isdir(p) else 0o444)
    try:
        _, _, _, gespiegeld = draai_keten(bron, tmp_path)
        assert gespiegeld > 0       # elke schrijfpoging op de bron had hier een fout gegeven
    finally:
        for p in paden:
            os.chmod(p, 0o755 if os.path.isdir(p) else 0o644)


def test_doel_binnen_de_bron_wordt_geweigerd(tmp_path):
    bron = tmp_path / "t-schijf"
    bron.mkdir()
    with pytest.raises(ValueError):
        NepSharePoint(bron / "sharepoint", bron=bron)
    assert list(bron.iterdir()) == []


def test_gespiegelde_kopie_is_gelijk_aan_de_bron_met_metadata(tmp_path):
    bron = tmp_path / "t-schijf"
    maak(bron)
    _, doel, _, _ = draai_keten(bron, tmp_path)
    for rij in doel.inhoud(1000):
        kopie = (doel.map / rij["doelpad"]).read_bytes()
        assert hashlib.sha256(kopie).hexdigest() == rij["sha256"]
        assert (bron / rij["bronpad"]).read_bytes() == kopie
        assert rij["documenttype"]

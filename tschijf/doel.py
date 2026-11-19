"""Het doelsysteem achter één interface.

De demo gebruikt NepSharePoint. De echte koppelingen zijn bewust niet gebouwd.
"""
import shutil
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

KOLOMMEN = ("bronpad", "naam", "project", "fase", "discipline", "documenttype",
            "gewijzigd", "grootte", "sha256")


class Doelsysteem(ABC):
    @abstractmethod
    def schrijf(self, bronbestand: Path, metadata: dict) -> str:
        """Kopieer het bestand met metadata naar het doel; geef de doellocatie terug.

        Mag het bronbestand alleen lezen.
        """

    def inhoud(self, limiet: int = 10) -> list[dict]:
        """Laatst geschreven documenten, voor het overzichtsscherm."""
        return []


class NepSharePoint(Doelsysteem):
    """Lokale map (de 'bibliotheek') plus een SQLite-tabel met de metadatakolommen."""

    def __init__(self, map_: Path, bron: Path | None = None):
        self.map = Path(map_).resolve()
        if bron is not None and self.map.is_relative_to(Path(bron).resolve()):
            raise ValueError("Het doel mag niet binnen de bronschijf liggen.")
        (self.map / "bibliotheek").mkdir(parents=True, exist_ok=True)
        self.db = self.map / "sharepoint.db"
        with self._con() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS documenten(id INTEGER PRIMARY KEY, "
                "bronpad TEXT UNIQUE, doelpad TEXT, naam TEXT, project TEXT, fase TEXT, "
                "discipline TEXT, documenttype TEXT, gewijzigd TEXT, grootte INTEGER, "
                "sha256 TEXT, gespiegeld_op TEXT)")

    def _con(self):
        con = sqlite3.connect(self.db)
        con.row_factory = sqlite3.Row
        return con

    def schrijf(self, bronbestand: Path, metadata: dict) -> str:
        rel = Path(metadata["project"] or "_zonder project") / (metadata["fase"] or "_zonder fase")
        doelmap = self.map / "bibliotheek" / rel
        doelmap.mkdir(parents=True, exist_ok=True)
        with self._con() as con:
            rij = con.execute("SELECT doelpad FROM documenten WHERE bronpad=?",
                              (metadata["bronpad"],)).fetchone()
            if rij:                                   # opnieuw spiegelen: zelfde plek
                doel = self.map / rij["doelpad"]
            else:
                doel = doelmap / metadata["naam"]
                if doel.exists():                     # zelfde naam uit een andere bronmap
                    stam, punt, ext = metadata["naam"].rpartition(".")
                    doel = doelmap / f"{stam} ({metadata['sha256'][:6]}){punt}{ext}"
            shutil.copy2(bronbestand, doel)           # kopiëren, nooit verplaatsen
            doelpad = doel.relative_to(self.map).as_posix()
            con.execute(
                "INSERT INTO documenten(bronpad, doelpad, naam, project, fase, discipline, "
                "documenttype, gewijzigd, grootte, sha256, gespiegeld_op) "
                "VALUES(:bronpad, :doelpad, :naam, :project, :fase, :discipline, "
                ":documenttype, :gewijzigd, :grootte, :sha256, :nu) "
                "ON CONFLICT(bronpad) DO UPDATE SET doelpad=:doelpad, project=:project, "
                "fase=:fase, discipline=:discipline, documenttype=:documenttype, "
                "gewijzigd=:gewijzigd, grootte=:grootte, sha256=:sha256, gespiegeld_op=:nu",
                {**{k: metadata[k] for k in KOLOMMEN}, "doelpad": doelpad,
                 "nu": datetime.now().isoformat(timespec="seconds")})
        return doelpad

    def inhoud(self, limiet: int = 10) -> list[dict]:
        with self._con() as con:
            return [dict(r) for r in con.execute(
                "SELECT * FROM documenten ORDER BY gespiegeld_op DESC, id DESC LIMIT ?", (limiet,))]


class GraphSharePoint(Doelsysteem):
    """NIET GEBOUWD. Plek voor de echte SharePoint-koppeling via Microsoft Graph.

    Wat hier moet komen:
    - Aanmelden met een app-registratie in Entra ID (client-credentials),
      met alleen schrijfrecht op de ene site (Sites.Selected).
    - Bestand uploaden naar de documentbibliotheek (upload-sessie voor grote bestanden).
    - De metadata schrijven naar de kolommen van het lijstitem (listItem/fields).
      De kolommen project, fase, discipline en documenttype moeten vooraf bestaan.
    - Zelfde afspraak als de demo: de bron wordt alleen gelezen.
    """

    def schrijf(self, bronbestand: Path, metadata: dict) -> str:
        raise NotImplementedError("Microsoft Graph-koppeling is geen onderdeel van de demo.")


class AlfrescoDoel(Doelsysteem):
    """NIET GEBOUWD. Plek voor een koppeling met Alfresco (of een ander DMS/archief).

    Wat hier moet komen:
    - Aanmelden met een service-account op de Alfresco REST API.
    - Node aanmaken in de juiste map en de metadata als eigenschappen meegeven,
      volgens het metadatamodel van functioneel beheer.
    - Pas bouwen na akkoord van functioneel beheer van het archiefsysteem.
    """

    def schrijf(self, bronbestand: Path, metadata: dict) -> str:
        raise NotImplementedError("Alfresco-koppeling is geen onderdeel van de demo.")

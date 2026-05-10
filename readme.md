# DV + HDR → Profile 8.1 Hybrid Batch Mux

Automatisiertes Python-Script zum Erstellen von **Dolby Vision Profile 8.1**-MKVs aus getrennten HDR10- und DV-Quellen.

Das Ergebnis enthält sowohl einen **HDR10-Fallback** (Base Layer) als auch **Dolby Vision**-Metadaten (RPU) und ist kompatibel mit allen DV-fähigen Geräten sowie als Standard-HDR10 auf Geräten ohne DV-Support abspielbar.

---

## Ergebnis

```
Video : Base Layer (HDR10) + RPU (Dolby Vision Profile 8, CM v2.9)
Codec : HEVC-10Bit-YUV-4:2:0
```

---

## Voraussetzungen

### Tools

| Tool | Bezugsquelle |
|------|-------------|
| **DDVT** (dovi_tool, ffmpeg, mkvextract, mkvmerge, mediainfo) | [github.com/DonaldFaQ/DDVT](https://github.com/DonaldFaQ/DDVT) |
| **Python 3.6+** | [python.org](https://www.python.org/downloads/) |

Keine zusätzlichen Python-Pakete erforderlich — nur die Standardbibliothek.

### Eingabedateien

- HDR-Quelle (`C:\HDR\`) — MKV mit HDR10-Video, Audio und Untertiteln
- DV-Quelle (`C:\DV\`) — MKV mit Dolby Vision Video

Die Dateinamen müssen **nicht exakt übereinstimmen**. Das Script erkennt automatisch zusammengehörige Dateien auch wenn sich die Namen nur im `HDR`- bzw. `DV`-Token unterscheiden (siehe [Datei-Matching](#datei-matching)).

### Unterstützte DV-Profile

| DV-Profil | Beschreibung | Konvertierung |
|-----------|-------------|---------------|
| **Profile 5** | IPT-PQ Single Layer | `dovi_tool -m 3 convert` → P8.1 |
| **Profile 7** | Dual Layer BL+EL | `dovi_tool -m 2 convert` → P8.1 (EL verworfen) |
| **Profile 8** | BL+RPU (bereits kompatibel) | RPU direkt extrahieren |

---

## Installation

```
git clone https://github.com/DEIN_USER/dv-hdr-batch-mux
cd dv-hdr-batch-mux
```

Kein `pip install` notwendig.

---

## Konfiguration

Die Konfiguration befindet sich direkt am Anfang von `dv_hdr_batch_mux.py`:

```python
HDR_DIR  = r"C:\HDR"               # Ordner mit HDR10-MKVs
DV_DIR   = r"C:\DV"                # Ordner mit DV-MKVs
OUT_DIR  = r"C:\FERTIG"            # Ausgabeordner
TEMP_DIR = r"C:\TEMP_MUX"          # Temporaerer Arbeitsordner
DDVT_DIR = r"C:\DDVT\tools"        # Pfad zum tools-Ordner von DDVT
```

> **Hinweis:** Der `TEMP_DIR` sollte ausreichend freien Speicherplatz haben.
> Pro Film werden temporaer ca. 2× die Groesse des Videostreams benoetigt (DV.hevc + HDR.hevc).
> Die Temp-Dateien werden nach jedem Job automatisch geloescht.

---

## Datei-Matching

Das Script unterstützt zwei Matching-Strategien die automatisch in dieser Reihenfolge angewendet werden:

### 1. Exakter Name (Prioritaet)

Wenn HDR- und DV-Datei identisch heissen wird direkt gematcht:

```
HDR\Film.mkv  <=>  DV\Film.mkv
```

### 2. Normalisierter Name

Wenn die Namen sich nur im `HDR`/`DV`-Token unterscheiden werden folgende Begriffe
aus beiden Dateinamen entfernt und der Rest verglichen:

| Entfernte Tokens |
|-----------------|
| `HDR`, `HDR10` |
| `DV`, `DoVi`, `Dolby Vision` |

Trennzeichen (Punkt, Leerzeichen, Unterstrich, Bindestrich) werden dabei beruecksichtigt.

**Beispiele:**

```
Movie.Name.HDR.2160p.mkv   <=>  Movie.Name.DV.2160p.mkv    OK
Series.S01E01.HDR.mkv      <=>  Series.S01E01.DV.mkv        OK
Film.HDR10.4K.mkv          <=>  Film.DV.4K.mkv              OK
Show.S02E05.2160p.HDR.mkv  <=>  Show.S02E05.2160p.DV.mkv    OK
```

Wird kein Match gefunden zeigt das Log beide normalisierten Keys zur Diagnose:

```
SKIP: Kein passender DV-File gefunden.
      HDR-Key : movie.name.2160p
      DV-Keys : movie.name.2160p, other.film, ...
```

Der **Ausgabedateiname** entspricht immer dem HDR-Dateinamen.

---

## Verwendung

### Direkt per Python

```bash
python dv_hdr_batch_mux.py
```

### Per Batch-Datei (Windows)

Doppelklick auf `START_Batch_Mux.bat`.

---

## Ablauf pro Datei

```
Profile 5 (IPT-PQ):
  mkvextract DV.mkv       =>  DV.hevc
  dovi_tool -m 3 convert  =>  DV_P8.hevc      (P5 => P8.1)
  dovi_tool extract-rpu   =>  RPU_P8.bin
  mkvextract HDR.mkv      =>  HDR.hevc
  dovi_tool inject-rpu    =>  RESULT.hevc     (HDR10 BL + P8.1 RPU)
  mkvmerge                =>  OUTPUT.mkv      (RESULT.hevc + Audio/Subs aus HDR)

Profile 7 (Dual Layer):
  mkvextract DV.mkv       =>  DV.hevc
  dovi_tool -m 2 convert  =>  DV_P8.hevc      (P7 => P8.1, EL verworfen)
  dovi_tool extract-rpu   =>  RPU_P8.bin
  mkvextract HDR.mkv      =>  HDR.hevc
  dovi_tool inject-rpu    =>  RESULT.hevc
  mkvmerge                =>  OUTPUT.mkv

Profile 8 (bereits BL+RPU):
  ffmpeg | dovi_tool extract-rpu  =>  RPU_P8.bin   (kein Convert noetig)
  mkvextract HDR.mkv              =>  HDR.hevc
  dovi_tool inject-rpu            =>  RESULT.hevc
  mkvmerge                        =>  OUTPUT.mkv
```

---

## Log

Pro Durchlauf wird automatisch eine Log-Datei in `OUT_DIR` erstellt:

```
C:\FERTIG\batch_log_20240501_163045.txt
```

Das Log enthaelt alle Tool-Aufrufe, Ausgaben und Fehlermeldungen.

---

## Fehlerbehandlung

- Kein passender DV-File gefunden → Datei wird uebersprungen, Log zeigt beide Keys
- Ausgabedatei existiert bereits → Datei wird uebersprungen (kein Ueberschreiben)
- Fehler bei einer Datei → Script laeuft weiter fuer alle weiteren Dateien
- Unvollstaendige Ausgabedatei bei Fehler → wird automatisch geloescht

---

## Ordnerstruktur

```
C:\HDR\
    Film_A.HDR.2160p.mkv
    Film_B.HDR.2160p.mkv
    Serie.S01E01.HDR.2160p.mkv

C:\DV\
    Film_A.DV.2160p.mkv          <- wird automatisch gematch (HDR/DV Token)
    Film_B.DV.2160p.mkv
    Serie.S01E01.DV.2160p.mkv

C:\FERTIG\                       <- Ausgabe (Dateiname = HDR-Dateiname)
    Film_A.HDR.2160p.mkv         <- BL(HDR10) + RPU(DV P8.1)
    Film_B.HDR.2160p.mkv
    Serie.S01E01.HDR.2160p.mkv

C:\TEMP_MUX\                     <- Temp (wird nach jedem Job automatisch geleert)
```

---

## Danksagung

- [DonaldFaQ/DDVT](https://github.com/DonaldFaQ/DDVT) — DDVT Toolchain
- [quietvoid/dovi_tool](https://github.com/quietvoid/dovi_tool) — Dolby Vision RPU Tool
- [MKVToolNix](https://mkvtoolnix.download/) — mkvmerge / mkvextract

---

## Lizenz

MIT

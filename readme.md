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

- HDR-Quelle (`C:\HDR\`) — MKV mit HDR10-Video, Audio, Untertiteln
- DV-Quelle (`C:\DV\`) — MKV mit Dolby Vision Video
- **Dateinamen müssen identisch sein** (`Film.mkv` in beiden Ordnern)

### Unterstützte DV-Profile

| DV-Profil | Beschreibung | Konvertierung |
|-----------|-------------|---------------|
| **Profile 5** | IPT-PQ Single Layer | `dovi_tool -m 3 convert` → P8.1 |
| **Profile 7** | Dual Layer BL+EL | `dovi_tool -m 2 convert` → P8.1 (EL verworfen) |
| **Profile 8** | BL+RPU (bereits kompatibel) | RPU direkt extrahieren |

---

## Installation

```
git clone https://github.com/PatriotM/dv-hdr-batch-mux
cd dv-hdr-batch-mux
```

Kein `pip install` notwendig.

---

## Konfiguration

Die Konfiguration befindet sich direkt am Anfang von `dv_hdr_batch_mux.py`:

```python
HDR_DIR  = r"C:\HDR"               # Ordner mit HDR10-MKVs
DV_DIR   = r"C:\DV"                # Ordner mit DV-MKVs (gleiche Dateinamen)
OUT_DIR  = r"C:\FERTIG"            # Ausgabeordner
TEMP_DIR = r"C:\TEMP_MUX"          # Temporärer Arbeitsordner
DDVT_DIR = r"C:\DDVT\tools"        # Pfad zum tools-Ordner von DDVT
```

> **Hinweis:** Der `TEMP_DIR` sollte genug freien Speicherplatz haben.
> Pro Film werden temporär ca. 2× die Größe des Videostreams benötigt (DV.hevc + HDR.hevc).
> Die Temp-Dateien werden nach jedem Job automatisch gelöscht.

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
  mkvextract DV.mkv      →  DV.hevc
  dovi_tool -m 3 convert →  DV_P8.hevc      (P5 → P8.1)
  dovi_tool extract-rpu  →  RPU_P8.bin
  mkvextract HDR.mkv     →  HDR.hevc
  dovi_tool inject-rpu   →  RESULT.hevc     (HDR10 BL + P8.1 RPU)
  mkvmerge               →  OUTPUT.mkv      (RESULT.hevc + Audio/Subs aus HDR)

Profile 7 (Dual Layer):
  mkvextract DV.mkv      →  DV.hevc
  dovi_tool -m 2 convert →  DV_P8.hevc      (P7 → P8.1, EL verworfen)
  dovi_tool extract-rpu  →  RPU_P8.bin
  mkvextract HDR.mkv     →  HDR.hevc
  dovi_tool inject-rpu   →  RESULT.hevc
  mkvmerge               →  OUTPUT.mkv

Profile 8 (bereits BL+RPU):
  ffmpeg | dovi_tool extract-rpu  →  RPU_P8.bin   (kein Convert nötig)
  mkvextract HDR.mkv              →  HDR.hevc
  dovi_tool inject-rpu            →  RESULT.hevc
  mkvmerge                        →  OUTPUT.mkv
```

---

## Log

Pro Durchlauf wird automatisch eine Log-Datei in `OUT_DIR` erstellt:

```
C:\FERTIG\batch_log_20240501_163045.txt
```

Das Log enthält alle Tool-Aufrufe, Ausgaben und Fehlermeldungen.

---

## Fehlerbehandlung

- Fehlt die passende DV-Datei → Datei wird übersprungen, nächste wird verarbeitet
- Ausgabedatei existiert bereits → Datei wird übersprungen (kein Überschreiben)
- Fehler bei einer Datei → Script läuft weiter für alle weiteren Dateien
- Unvollständige Ausgabedatei bei Fehler → wird automatisch gelöscht

---

## Ordnerstruktur

```
C:\HDR\
    Film_A.mkv
    Film_B.mkv
    Serie_S01E01.mkv

C:\DV\
    Film_A.mkv        ← gleicher Name wie in HDR\
    Film_B.mkv
    Serie_S01E01.mkv

C:\FERTIG\            ← Ausgabe (wird erstellt falls nicht vorhanden)
C:\TEMP_MUX\          ← Temp (wird erstellt, nach Job geleert)
```

---

## Danksagung

- [DonaldFaQ/DDVT](https://github.com/DonaldFaQ/DDVT) — DDVT Toolchain
- [quietvoid/dovi_tool](https://github.com/quietvoid/dovi_tool) — Dolby Vision RPU Tool
- [MKVToolNix](https://mkvtoolnix.download/) — mkvmerge / mkvextract

---

## Lizenz

MIT

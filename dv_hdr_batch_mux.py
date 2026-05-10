#!/usr/bin/env python3
"""
DV + HDR => Profile 8.1 Hybrid Batch Mux
==========================================

Ablauf pro Datei:

  P5 (IPT-PQ Single Layer):
    1. DV-HEVC extrahieren     (mkvextract)
    2. dovi_tool convert -m 3  (P5 => P8.1 in HEVC)
    3. RPU extrahieren         (dovi_tool extract-rpu aus konvertiertem HEVC)
    4. HDR-HEVC extrahieren    (mkvextract)
    5. inject-rpu              (dovi_tool)
    6. mkvmerge

  P7 (Dual Layer BL+EL):
    1. DV-HEVC extrahieren     (mkvextract)
    2. dovi_tool convert -m 2  (P7 => P8.1, entfernt EL/Mapping)
    3. RPU extrahieren         (dovi_tool extract-rpu aus konvertiertem HEVC)
    4. HDR-HEVC extrahieren    (mkvextract)
    5. inject-rpu              (dovi_tool)
    6. mkvmerge

  P8 (schon BL+RPU):
    1. RPU extrahieren         (ffmpeg | dovi_tool extract-rpu, kein Convert)
    2. HDR-HEVC extrahieren    (mkvextract)
    3. inject-rpu              (dovi_tool)
    4. mkvmerge

dovi_tool convert Modi:
  -m 2  => P8.1 kompatibel, entfernt Mapping (fuer P7)
  -m 3  => konvertiert P5 zu P8.1
  -m 5  => P8.1, behaelt Luma/Chroma Mapping (Alternative zu -m 2)
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime

# ============================================================
#  KONFIGURATION  <-- hier anpassen
# ============================================================
HDR_DIR  = r"C:\HDR"
DV_DIR   = r"C:\DV"
OUT_DIR  = r"C:\FERTIG"
TEMP_DIR = r"C:\TEMP_MUX"      # Temp-Ordner, wird pro Job als Unterordner genutzt
DDVT_DIR = r"C:\DDVT\tools"   # Pfad zum tools-Ordner von DDVT

# ============================================================

FFMPEG      = os.path.join(DDVT_DIR, "ffmpeg.exe")
DOVI_TOOL   = os.path.join(DDVT_DIR, "dovi_tool.exe")
MKV_EXTRACT = os.path.join(DDVT_DIR, "mkvextract.exe")
MKV_MERGE   = os.path.join(DDVT_DIR, "mkvmerge.exe")
MEDIA_INFO  = os.path.join(DDVT_DIR, "mediainfo.exe")


# ============================================================
#  LOGGING
# ============================================================
def setup_logging(out_dir: str) -> logging.Logger:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(out_dir, f"batch_log_{ts}.txt")
    logger = logging.getLogger("dvmux")
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(ch)
    logger.info(f"Log: {log_path}")
    return logger


# ============================================================
#  HILFSFUNKTIONEN
# ============================================================
def normalize_name(stem: str) -> str:
    """
    Entfernt HDR/DV-Tokens aus dem Dateinamen fuer den Vergleich.
    Erkennt Trennzeichen Punkt, Leerzeichen, Unterstrich, Bindestrich.
    Beispiele:
      Movie.Name.HDR.2160p  =>  movie.name.2160p
      Movie.Name.DV.2160p   =>  movie.name.2160p
      Film HDR 4K           =>  film 4k
      Film.DV               =>  film
    """
    import re
    # Tokens die entfernt werden (Gross/Kleinschreibung egal)
    tokens = r'(?<![A-Za-z])(HDR10|HDR|DV|DoVi|Dolby[\s._-]?Vision)(?![A-Za-z])'
    result = re.sub(tokens, '', stem, flags=re.IGNORECASE)
    # Mehrfache Trennzeichen zusammenfuehren die durch das Entfernen entstehen
    result = re.sub(r'[._\- ]{2,}', '.', result)
    result = result.strip('._- ')
    return result.lower()


def run(args: list, log: logging.Logger) -> int:
    """Fuehrt Prozess aus, loggt Output, gibt Exit-Code zurueck."""
    log.debug("  > " + " ".join(
        f'"{a}"' if " " in str(a) else str(a) for a in args
    ))
    result = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace"
    )
    for line in result.stdout.splitlines():
        if line.strip():
            log.debug(f"    {line}")
    return result.returncode


def get_video_track_id(mkv_path: str, log: logging.Logger) -> str:
    """Video-Track-ID per mkvmerge --identify."""
    result = subprocess.run(
        [MKV_MERGE, "--identify", mkv_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, errors="replace"
    )
    for line in result.stdout.splitlines():
        if "video" in line.lower() and "Track ID" in line:
            tid = line.split(":")[0].replace("Track ID", "").strip()
            if tid.isdigit():
                return tid
    return "0"


def mkvextract_hevc(mkv_path: str, hevc_out: str, log: logging.Logger) -> bool:
    """Extrahiert Video-Track als raw HEVC per mkvextract."""
    track_id = get_video_track_id(mkv_path, log)
    log.info(f"      mkvextract Track {track_id} aus {Path(mkv_path).name} ...")
    rc = run([MKV_EXTRACT, "tracks", mkv_path, f"{track_id}:{hevc_out}"], log)
    return (os.path.isfile(hevc_out)
            and os.path.getsize(hevc_out) > 1024 * 1024
            and rc == 0)


def extract_rpu_from_hevc(hevc_path: str, rpu_out: str, log: logging.Logger) -> bool:
    """dovi_tool extract-rpu direkt aus HEVC-Datei (kein ffmpeg noetig)."""
    log.info(f"      dovi_tool extract-rpu aus {Path(hevc_path).name} ...")
    rc = run([DOVI_TOOL, "extract-rpu", "-o", rpu_out, hevc_path], log)
    return os.path.isfile(rpu_out) and os.path.getsize(rpu_out) > 0


def extract_rpu_from_mkv_pipe(dv_mkv: str, rpu_out: str, log: logging.Logger) -> bool:
    """
    Fuer P8: ffmpeg | dovi_tool extract-rpu (kein Convert noetig,
    kein Temp-HEVC fuer DV notwendig).
    """
    log.info("      ffmpeg | dovi_tool extract-rpu ...")
    p_ffmpeg = subprocess.Popen(
        [FFMPEG, "-loglevel", "panic", "-i", dv_mkv,
         "-c:v", "copy", "-bsf:v", "hevc_mp4toannexb",
         "-f", "hevc", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    p_dovi = subprocess.Popen(
        [DOVI_TOOL, "extract-rpu", "-o", rpu_out, "-"],
        stdin=p_ffmpeg.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    p_ffmpeg.stdout.close()
    out, _ = p_dovi.communicate()
    p_ffmpeg.wait()
    for line in out.decode("utf-8", errors="replace").splitlines():
        if line.strip():
            log.debug(f"    dovi: {line}")
    return os.path.isfile(rpu_out) and os.path.getsize(rpu_out) > 0


def detect_profile_from_rpu(rpu_bin: str, log: logging.Logger) -> int:
    """Liest DV-Profil aus dovi_tool info (auf .bin Datei)."""
    result = subprocess.run(
        [DOVI_TOOL, "info", "-s", rpu_bin],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace"
    )
    for line in result.stdout.splitlines():
        if "Profile:" in line:
            val = line.split(":")[-1].strip().split()[0]
            if val.isdigit():
                return int(val)
    return 0


def convert_hevc_to_p8(dv_hevc: str, converted_hevc: str,
                        mode: int, log: logging.Logger) -> bool:
    """
    dovi_tool convert -m <mode> -i dv.hevc -o converted.hevc
    Mode 2: P7 => P8.1 (entfernt Mapping)
    Mode 3: P5 => P8.1
    """
    log.info(f"      dovi_tool convert -m {mode} ...")
    rc = run([DOVI_TOOL, "-m", str(mode), "convert",
              "-i", dv_hevc, "-o", converted_hevc], log)
    return (os.path.isfile(converted_hevc)
            and os.path.getsize(converted_hevc) > 1024 * 1024
            and rc == 0)


def inject_rpu(hdr_hevc: str, rpu_bin: str, result_hevc: str,
               log: logging.Logger) -> bool:
    """dovi_tool inject-rpu: P8-RPU in HDR10-HEVC => RESULT.hevc"""
    log.info("      dovi_tool inject-rpu ...")
    rc = run([
        DOVI_TOOL, "inject-rpu",
        "-i", hdr_hevc,
        "--rpu-in", rpu_bin,
        "-o", result_hevc
    ], log)
    return (os.path.isfile(result_hevc)
            and os.path.getsize(result_hevc) > 1024 * 1024
            and rc == 0)


def mux_mkv(result_hevc: str, hdr_mkv: str, out_mkv: str,
            log: logging.Logger) -> bool:
    """mkvmerge: RESULT.hevc + Audio/Subs aus HDR-MKV => fertiges MKV"""
    rc = run([
        MKV_MERGE,
        "--output", out_mkv,
        "--language", "0:und",
        "--compression", "0:none",
        result_hevc,
        "--no-video",
        hdr_mkv
    ], log)
    return rc <= 1 and os.path.isfile(out_mkv)


# ============================================================
#  VERARBEITUNG EINER DATEI
# ============================================================
def process_file(hdr_mkv: str, dv_mkv: str, out_mkv: str,
                 log: logging.Logger) -> None:

    name = Path(hdr_mkv).stem
    safe = name[:60].replace(" ", "_")
    job_tmp = os.path.join(TEMP_DIR, safe)
    os.makedirs(job_tmp, exist_ok=True)

    dv_hevc         = os.path.join(job_tmp, "DV.hevc")
    dv_converted    = os.path.join(job_tmp, "DV_P8.hevc")
    rpu_bin         = os.path.join(job_tmp, "RPU_P8.bin")
    hdr_hevc        = os.path.join(job_tmp, "HDR.hevc")
    result_hevc     = os.path.join(job_tmp, "RESULT.hevc")

    try:
        # -- Schritt 1: Profil bestimmen --
        # Kurzen RPU-Probe-Extract per Pipe um Profil zu lesen
        # (nur fuer Profilbestimmung, kein langer Extrakt)
        log.info("  [1] Ermittle DV-Profil ...")
        rpu_probe = os.path.join(job_tmp, "RPU_probe.bin")
        if not extract_rpu_from_mkv_pipe(dv_mkv, rpu_probe, log):
            raise RuntimeError("Profil-Erkennung fehlgeschlagen (RPU-Probe-Extraktion)")
        profile = detect_profile_from_rpu(rpu_probe, log)
        log.info(f"  Erkanntes DV-Profil: {profile}")

        # -- Schritt 2+3: Profil-abhaengige RPU-Vorbereitung --
        if profile == 5:
            # P5: DV-HEVC auf Disk, convert -m 3, RPU aus konvertiertem HEVC
            log.info("  [2] P5 => extrahiere DV-HEVC fuer convert -m 3 ...")
            if not mkvextract_hevc(dv_mkv, dv_hevc, log):
                raise RuntimeError("DV-HEVC-Extraktion fehlgeschlagen")

            log.info("  [3] dovi_tool convert -m 3 (P5 => P8.1) ...")
            if not convert_hevc_to_p8(dv_hevc, dv_converted, mode=3, log=log):
                raise RuntimeError("P5-Konvertierung fehlgeschlagen")

            log.info("  [3b] RPU aus konvertiertem HEVC extrahieren ...")
            if not extract_rpu_from_hevc(dv_converted, rpu_bin, log):
                raise RuntimeError("RPU-Extraktion aus konvertiertem P5-HEVC fehlgeschlagen")

        elif profile == 7:
            # P7: DV-HEVC auf Disk, convert -m 2 (entfernt EL+Mapping), RPU extrahieren
            log.info("  [2] P7 => extrahiere DV-HEVC fuer convert -m 2 ...")
            if not mkvextract_hevc(dv_mkv, dv_hevc, log):
                raise RuntimeError("DV-HEVC-Extraktion fehlgeschlagen")

            log.info("  [3] dovi_tool convert -m 2 (P7 => P8.1) ...")
            if not convert_hevc_to_p8(dv_hevc, dv_converted, mode=2, log=log):
                raise RuntimeError("P7-Konvertierung fehlgeschlagen")

            log.info("  [3b] RPU aus konvertiertem HEVC extrahieren ...")
            if not extract_rpu_from_hevc(dv_converted, rpu_bin, log):
                raise RuntimeError("RPU-Extraktion aus konvertiertem P7-HEVC fehlgeschlagen")

        elif profile == 8:
            # P8: RPU direkt per Pipe extrahieren, kein Convert noetig
            log.info("  [2] P8 => RPU direkt extrahieren (kein Convert) ...")
            if not extract_rpu_from_mkv_pipe(dv_mkv, rpu_bin, log):
                raise RuntimeError("RPU-Extraktion (P8) fehlgeschlagen")

        else:
            raise RuntimeError(
                f"DV-Profil {profile} nicht unterstuetzt. "
                f"Unterstuetzt: 5, 7, 8."
            )

        # -- Schritt 4: HDR-HEVC extrahieren --
        # Noetig weil dovi_tool inject-rpu keinen MKV-Input akzeptiert
        log.info("  [4] Extrahiere HDR-HEVC (mkvextract) ...")
        if not mkvextract_hevc(hdr_mkv, hdr_hevc, log):
            raise RuntimeError("HDR-HEVC-Extraktion fehlgeschlagen")

        # -- Schritt 5: RPU injizieren --
        log.info("  [5] inject-rpu => BL(HDR10) + RPU(P8.1) ...")
        if not inject_rpu(hdr_hevc, rpu_bin, result_hevc, log):
            raise RuntimeError("RPU-Injection fehlgeschlagen")

        # -- Schritt 6: In MKV muxen --
        log.info("  [6] mkvmerge => fertiges MKV ...")
        if not mux_mkv(result_hevc, hdr_mkv, out_mkv, log):
            raise RuntimeError("mkvmerge fehlgeschlagen")

        size_mb = os.path.getsize(out_mkv) / (1024 * 1024)
        log.info(f"  OK: {Path(out_mkv).name}  ({size_mb:.1f} MB)")

    finally:
        shutil.rmtree(job_tmp, ignore_errors=True)


# ============================================================
#  TOOL-PRUEFUNG
# ============================================================
def check_tools(log: logging.Logger) -> bool:
    missing = [t for t in [FFMPEG, DOVI_TOOL, MKV_EXTRACT, MKV_MERGE, MEDIA_INFO]
               if not os.path.isfile(t)]
    if missing:
        for t in missing:
            log.error(f"Tool nicht gefunden: {t}")
        log.error("Bitte DDVT_DIR anpassen.")
        return False
    return True


# ============================================================
#  MAIN
# ============================================================
def main():
    for d in (OUT_DIR, TEMP_DIR):
        os.makedirs(d, exist_ok=True)

    log = setup_logging(OUT_DIR)
    log.info("=" * 60)
    log.info("  DV + HDR => Profile 8.1 Hybrid Batch Mux")
    log.info("=" * 60)
    log.info(f"HDR  : {HDR_DIR}")
    log.info(f"DV   : {DV_DIR}")
    log.info(f"OUT  : {OUT_DIR}")
    log.info(f"TEMP : {TEMP_DIR}")
    log.info(f"DDVT : {DDVT_DIR}")

    if not check_tools(log):
        sys.exit(1)

    hdr_files = sorted(Path(HDR_DIR).glob("*.mkv"))
    dv_files  = sorted(Path(DV_DIR).glob("*.mkv"))
    total   = len(hdr_files)
    ok      = 0
    skipped = 0
    errors  = 0

    if total == 0:
        log.warning(f"Keine MKV-Dateien in {HDR_DIR} gefunden.")
        sys.exit(0)

    # DV-Dateien per normalisiertem Namen indexieren
    # z.B. "movie.name.2160p" => Path(...DV...)
    dv_index = {}
    for dv_path in dv_files:
        key = normalize_name(dv_path.stem)
        dv_index[key] = dv_path

    log.info(f"HDR-Dateien gefunden : {total}")
    log.info(f"DV-Dateien gefunden  : {len(dv_files)}")

    for idx, hdr_path in enumerate(hdr_files, 1):
        out_path = Path(OUT_DIR) / hdr_path.name

        log.info("")
        log.info("-" * 60)
        log.info(f"[{idx}/{total}]  {hdr_path.stem}")

        # Passende DV-Datei suchen: zuerst exakter Name, dann normalisiert
        hdr_key = normalize_name(hdr_path.stem)
        if (Path(DV_DIR) / hdr_path.name).is_file():
            dv_path = Path(DV_DIR) / hdr_path.name
            log.info(f"  Match (exakt)      : {dv_path.name}")
        elif hdr_key in dv_index:
            dv_path = dv_index[hdr_key]
            log.info(f"  Match (normalisiert): {dv_path.name}")
        else:
            log.warning(f"  SKIP: Kein passender DV-File gefunden.")
            log.warning(f"        HDR-Key : {hdr_key}")
            log.warning(f"        DV-Keys : {', '.join(sorted(dv_index.keys()))}")
            skipped += 1
            continue

        if out_path.is_file():
            log.warning("  SKIP: Ausgabe-Datei existiert bereits.")
            skipped += 1
            continue

        try:
            process_file(str(hdr_path), str(dv_path), str(out_path), log)
            ok += 1
        except Exception as e:
            log.error(f"  FEHLER: {e}")
            errors += 1
            if out_path.is_file():
                out_path.unlink(missing_ok=True)

    log.info("")
    log.info("=" * 60)
    log.info(f"  Erfolgreich  : {ok}")
    log.info(f"  Uebersprungen: {skipped}")
    log.info(f"  Fehler       : {errors}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()

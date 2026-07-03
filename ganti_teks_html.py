"""
ganti_teks_html.py
==================
Script untuk mengganti kata/kalimat/angka di banyak file HTML sekaligus.

Fitur:
  - Ganti banyak pasangan cari→ganti dalam sekali jalan
  - Mode preview (dry-run) — lihat dulu sebelum benar-benar diubah
  - Backup otomatis file asli sebelum diubah
  - Pencarian rekursif ke subfolder
  - Opsi case-sensitive / case-insensitive
  - Laporan lengkap: berapa file berubah, berapa total penggantian

Cara pakai:
  1. Edit bagian DAFTAR_PENGGANTIAN di bawah.
  2. Atur konfigurasi (folder target, backup, rekursif, dll).
  3. Jalankan: python ganti_teks_html.py
  4. Pertama coba dengan DRY_RUN = True untuk preview.
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  KONFIGURASI — EDIT BAGIAN INI
# ══════════════════════════════════════════════════════════════════

# Folder tempat file HTML berada (titik = folder yang sama dengan script)
FOLDER_TARGET = "."

# Cari file HTML di subfolder secara rekursif?
REKURSIF = True

# Preview saja tanpa benar-benar mengubah file (sangat disarankan dicoba dulu)
DRY_RUN = False

# Buat backup file asli sebelum diubah? (disimpan di folder "backup_html/")
BUAT_BACKUP = True

# Case-insensitive? (True = tidak peduli huruf besar/kecil)
ABAIKAN_KAPITAL = False

# ──────────────────────────────────────────────────────────────────
#  DAFTAR PENGGANTIAN
#  Format: ("CARI", "GANTI")
#  Bisa sebanyak yang dibutuhkan.
# ──────────────────────────────────────────────────────────────────
DAFTAR_PENGGANTIAN = [
    # Contoh penggantian teks biasa
    
    # Contoh penggantian angka / harga
    ("pusatrentalmobil.com", "pusatrentalmobil.id"),
  
  # Contoh penggantian URL / link
   

    # Contoh penggantian meta / tag HTML (tetap aman, hanya cari string)
    
]

# ══════════════════════════════════════════════════════════════════


def temukan_file_html(folder: str, rekursif: bool) -> list[Path]:
    """Cari semua file .html dan .htm di folder target."""
    root = Path(folder)
    if rekursif:
        files = list(root.rglob("*.html")) + list(root.rglob("*.htm"))
    else:
        files = list(root.glob("*.html")) + list(root.glob("*.htm"))
    return sorted(set(files))


def proses_file(
    path: Path,
    penggantian: list[tuple],
    abaikan_kapital: bool,
    dry_run: bool,
    backup_dir: Path | None,
) -> dict:
    """
    Proses satu file HTML.
    Mengembalikan dict hasil: jumlah penggantian per pasangan & konten baru.
    """
    try:
        konten_asli = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        konten_asli = path.read_text(encoding="latin-1")

    konten_baru  = konten_asli
    detail_ganti = []

    for cari, ganti in penggantian:
        flags = re.IGNORECASE if abaikan_kapital else 0
        pola  = re.compile(re.escape(cari), flags)

        jumlah = len(pola.findall(konten_baru))
        if jumlah > 0:
            konten_baru = pola.sub(ganti, konten_baru)
            detail_ganti.append((cari, ganti, jumlah))

    total_perubahan = sum(j for _, _, j in detail_ganti)
    ada_perubahan   = total_perubahan > 0

    if ada_perubahan and not dry_run:
        # Backup sebelum tulis
        if backup_dir:
            backup_path = backup_dir / path.name
            # Hindari overwrite backup jika nama file sama di subfolder berbeda
            if backup_path.exists():
                stem = path.stem
                suffix = path.suffix
                ts = datetime.now().strftime("%H%M%S%f")[:9]
                backup_path = backup_dir / f"{stem}_{ts}{suffix}"
            shutil.copy2(path, backup_path)

        # Tulis file yang sudah diubah
        path.write_text(konten_baru, encoding="utf-8")

    return {
        "path":           path,
        "ada_perubahan":  ada_perubahan,
        "total":          total_perubahan,
        "detail":         detail_ganti,
    }


def cetak_separator(char="─", lebar=70):
    print(char * lebar)


def main():
    print()
    cetak_separator("═")
    mode_label = "[ DRY-RUN / PREVIEW — tidak ada file yang diubah ]" if DRY_RUN else "[ MODE AKTIF — file akan diubah ]"
    print(f"  GANTI TEKS HTML MASSAL  |  {mode_label}")
    cetak_separator("═")

    # Validasi daftar penggantian
    if not DAFTAR_PENGGANTIAN:
        print("\n[ERROR] DAFTAR_PENGGANTIAN kosong. Isi dulu sebelum menjalankan script.")
        return

    # Temukan file HTML
    files = temukan_file_html(FOLDER_TARGET, REKURSIF)
    if not files:
        print(f"\n[INFO] Tidak ada file HTML ditemukan di: {Path(FOLDER_TARGET).resolve()}")
        return

    print(f"\n  Folder  : {Path(FOLDER_TARGET).resolve()}")
    print(f"  Rekursif: {'Ya' if REKURSIF else 'Tidak'}")
    print(f"  Kapital : {'Diabaikan' if ABAIKAN_KAPITAL else 'Diperhatikan'}")
    print(f"  Backup  : {'Ya' if BUAT_BACKUP and not DRY_RUN else 'Tidak (dry-run)' if DRY_RUN else 'Tidak'}")
    print(f"\n  Ditemukan {len(files)} file HTML\n")

    # Tampilkan daftar penggantian
    cetak_separator()
    print(f"  {'#':<4} {'CARI':<35} {'GANTI'}")
    cetak_separator()
    for i, (c, g) in enumerate(DAFTAR_PENGGANTIAN, 1):
        cari_trunc  = (c[:32] + "...") if len(c) > 35 else c
        ganti_trunc = (g[:32] + "...") if len(g) > 35 else g
        print(f"  {i:<4} {cari_trunc:<35} {ganti_trunc}")
    cetak_separator()

    # Siapkan folder backup
    backup_dir = None
    if BUAT_BACKUP and not DRY_RUN:
        ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path(f"backup_html_{ts}")
        backup_dir.mkdir(exist_ok=True)
        print(f"\n  Backup disimpan di: {backup_dir}/\n")

    # Proses semua file
    print()
    cetak_separator()
    print(f"  {'FILE HTML':<45} {'PENGGANTIAN'}")
    cetak_separator()

    file_berubah    = 0
    total_semua     = 0
    file_tidak_ubah = 0

    for path in files:
        hasil = proses_file(
            path          = path,
            penggantian   = DAFTAR_PENGGANTIAN,
            abaikan_kapital = ABAIKAN_KAPITAL,
            dry_run       = DRY_RUN,
            backup_dir    = backup_dir,
        )

        nama_pendek = str(path)
        if len(nama_pendek) > 44:
            nama_pendek = "..." + str(path)[-41:]

        if hasil["ada_perubahan"]:
            file_berubah += 1
            total_semua  += hasil["total"]
            print(f"  {nama_pendek:<45} {hasil['total']} penggantian")
            for cari, ganti, jml in hasil["detail"]:
                c = (cari[:28] + "...") if len(cari) > 31 else cari
                g = (ganti[:28] + "...") if len(ganti) > 31 else ganti
                print(f"    {'':2}↳ \"{c}\" → \"{g}\" ({jml}×)")
        else:
            file_tidak_ubah += 1
            print(f"  {nama_pendek:<45} (tidak ada perubahan)")

    # Ringkasan akhir
    print()
    cetak_separator("═")
    status = "PREVIEW" if DRY_RUN else "SELESAI"
    print(f"  {status}")
    cetak_separator()
    print(f"  Total file HTML     : {len(files)}")
    print(f"  File diubah         : {file_berubah}")
    print(f"  File tidak berubah  : {file_tidak_ubah}")
    print(f"  Total penggantian   : {total_semua}")
    if backup_dir:
        print(f"  Backup tersimpan di : {backup_dir}/")
    if DRY_RUN:
        print()
        print("  ► Untuk menerapkan perubahan, set DRY_RUN = False lalu jalankan ulang.")
    cetak_separator("═")
    print()


if __name__ == "__main__":
    main()

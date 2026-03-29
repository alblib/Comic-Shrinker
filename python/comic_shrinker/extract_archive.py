from pathlib import Path
import zipfile, py7zr, rarfile

def extract_archive(archive_path: Path, extract_to: Path) -> None:
    """Handles ZIP, RAR, and 7Z extraction."""
    ext = archive_path.suffix.lower()

    if ext in ('.zip', '.cbz'):
        with zipfile.ZipFile(archive_path, 'r') as z:
            z.extractall(extract_to)
    elif ext in ('.7z', '.cb7'):
        with py7zr.SevenZipFile(archive_path, mode='r') as s:
            s.extractall(path=extract_to)
    elif ext in ('.rar', '.cbr'):
        with rarfile.RarFile(archive_path) as r:
            r.extractall(extract_to)
    else:
        raise ValueError(f"Unsupported archive format: {ext}")

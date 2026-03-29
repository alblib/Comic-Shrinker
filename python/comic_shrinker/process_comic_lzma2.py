import os, tempfile, shutil, zipfile
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Callable, Optional, List, Tuple
from tqdm import tqdm

from .extract_archive import extract_archive
from .shrink_image import shrink_image


# def process_comic_lzma2(input_archive: Path, output_cbz: str, quality: int = 80, max_height: int = 2560):
#     # Using separate dirs for clarity and a clean 'finally' block
#     unarchive_temp_dir = Path(tempfile.mkdtemp())
#     rearchive_temp_dir = Path(tempfile.mkdtemp())
#
#     try:
#         print(f"[*] Extracting: {input_archive.name}")
#         # Your custom extraction function
#         extract_archive(archive_path=input_archive, extract_to=unarchive_temp_dir)
#
#         # 1. Prepare Tasks
#         tasks = []
#         for root, _, files in os.walk(unarchive_temp_dir):
#             for file in files:
#                 if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
#                     old_file_path = Path(root) / file
#
#                     # Calculate relative path to maintain folder structure
#                     rel_path = old_file_path.relative_to(unarchive_temp_dir)
#                     new_file_path = (rearchive_temp_dir / rel_path).with_suffix('.webp')
#
#                     # Ensure the sub-directory exists in the destination
#                     new_file_path.parent.mkdir(parents=True, exist_ok=True)
#
#                     # Pass the full argument set to the shrinker
#                     tasks.append((str(old_file_path), str(new_file_path), quality, max_height))
#
#         # 2. Parallel Execution with tqdm progress bar
#         print(f"[*] Optimizing {len(tasks)} images...")
#         with ProcessPoolExecutor() as executor:
#             # list() forces the generator to evaluate, which tqdm tracks
#             list(tqdm(executor.map(shrink_image_wrapper, tasks), total=len(tasks), desc="Shrinking", unit="pg"))
#
#         # 3. Re-archive with LZMA2
#         print(f"[*] Re-archiving to {output_cbz} (LZMA2)...")
#         # Wrapping the file writing in tqdm for the final zip phase
#         all_files = [Path(r) / f for r, _, fs in os.walk(rearchive_temp_dir) for f in fs]
#
#         with zipfile.ZipFile(output_cbz, 'w', compression=zipfile.ZIP_LZMA) as new_zip:
#             for fp in tqdm(all_files, desc="Compressing", unit="file"):
#                 new_zip.write(fp, fp.relative_to(rearchive_temp_dir))
#
#         print(f"\n[!] Success: {output_cbz}")
#
#     except Exception as e:
#         print(f"\n[X] Critical Failure: {e}")
#
#     finally:
#         # Cleanup
#         for d in [unarchive_temp_dir, rearchive_temp_dir]:
#             if d.exists():
#                 print(f"[*] Cleaning up: {d.name}")
#                 shutil.rmtree(d)


def shrink_image_wrapper(args):
    """
    Small helper to unpack tuple arguments for the actual shrink_image function.
    This is necessary because executor.map only takes one argument.
    """
    # shrink_image(input_path, output_path, quality, max_height)
    return shrink_image(*args)


def process_comic_lzma2(
        input_archive: Path,
        output_cbz: str,
        quality: int = 80,
        max_height: int = 2560,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
) -> None:
    """
    High-performance comic optimizer. Extracts ZIP/RAR/7Z, optimizes images
    to WebP via multiprocessing, and re-archives using LZMA2.

    Args:
        input_archive: Path object pointing to the source file (.cbz, .cbr, .cb7).
        output_cbz: String path for the final optimized file.
        quality: WebP quality setting (0-100). 80 is recommended.
        max_height: Max vertical pixels. Images taller than this are downscaled.
        progress_callback: Optional function(current: int, total: int, status: str).
                           Used to update GUI progress bars in real-time.
    """

    input_archive = Path(input_archive)

    # Initialization of dual-temp strategy to prevent file collision
    unarchive_temp_dir: Path = Path(tempfile.mkdtemp())
    rearchive_temp_dir: Path = Path(tempfile.mkdtemp())

    try:
        # Step 1: Extraction
        if progress_callback:
            progress_callback(0, 100, f"Extracting {input_archive.name}...")

        extract_archive(archive_path=input_archive, extract_to=unarchive_temp_dir)

        # Step 2: Task Mapping
        # We build a list of (input_path, output_path) while maintaining internal folder structure
        tasks: List[Tuple[str, str, int, int]] = []
        for root, _, files in os.walk(unarchive_temp_dir):
            for file in files:
                if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.tiff')):
                    old_fp = Path(root) / file

                    # Mirror the folder structure in the re-archive directory
                    rel_path = old_fp.relative_to(unarchive_temp_dir)
                    new_fp = (rearchive_temp_dir / rel_path).with_suffix('.webp')

                    # Ensure destination subfolders exist (e.g., "Chapter 1/")
                    new_fp.parent.mkdir(parents=True, exist_ok=True)

                    tasks.append((str(old_fp), str(new_fp), quality, max_height))

        total_pages: int = len(tasks)
        if total_pages == 0:
            raise ValueError("No valid images found in archive.")

        # Step 3: Parallel Image Optimization
        # ProcessPoolExecutor bypasses the GIL to use all CPU cores for heavy WebP encoding
        if progress_callback:
            progress_callback(0, total_pages, "Initializing CPU cores...")

        with ProcessPoolExecutor() as executor:
            # We use a dictionary to track futures so we know which image finished
            future_to_page = {executor.submit(shrink_image, *t): t for t in tasks}

            completed_count = 0
            for future in as_completed(future_to_page):
                completed_count += 1
                try:
                    future.result()  # Check for errors during shrink_image execution
                except Exception as e:
                    print(f"Worker Error: {e}")

                # Immediate feedback to GUI after every single page finishes
                if progress_callback:
                    status = f"Processed {completed_count}/{total_pages} pages"
                    progress_callback(completed_count, total_pages, status)

        # Step 4: High-Efficiency Re-archiving
        # Using ZIP_LZMA (LZMA2) for maximum shrink, compatible with Bandizip/ComicGlass
        if progress_callback:
            progress_callback(total_pages, total_pages, "Finalizing Archive (LZMA2)...")

        with zipfile.ZipFile(output_cbz, 'w', compression=zipfile.ZIP_LZMA) as new_zip:
            # Walk the processed directory and pack everything
            for root, _, files in os.walk(rearchive_temp_dir):
                for file in files:
                    fp = Path(root) / file
                    # Save with relative path to keep folders clean inside the ZIP
                    new_zip.write(fp, fp.relative_to(rearchive_temp_dir))

    except Exception as e:
        if progress_callback:
            progress_callback(0, 0, f"Error: {str(e)}")
        raise e  # Pass the error up for logging

    finally:
        # Secure Cleanup: The 'finally' block ensures temp folders are deleted
        # even if the user cancels or the script crashes.
        for d in [unarchive_temp_dir, rearchive_temp_dir]:
            if d.exists():
                shutil.rmtree(d)
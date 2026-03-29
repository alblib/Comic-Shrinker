import sys
import argparse
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from typing import List
from multiprocessing import freeze_support

# Assuming your package structure:
from comic_shrinker.process_comic_lzma2 import process_comic_lzma2


def main():
    # Needed for Windows multiprocessing when compiled to EXE
    freeze_support()

    parser = argparse.ArgumentParser(description="Comic Shrinker: High-Efficiency WebP/LZMA2 Optimizer")
    parser.add_argument("inputs", nargs="*", help="Input archive file(s)")
    parser.add_argument("-o", "--output", help="Output file (single) or folder (multiple)")
    parser.add_argument("-q", "--quality", type=int, default=80, help="WebP Quality (1-100)")

    args = parser.parse_args()

    # --- CLI Mode ---
    if args.inputs:
        input_paths = [Path(p) for p in args.inputs]
        output_arg = Path(args.output) if args.output else None

        # Logic for multiple files
        if len(input_paths) > 1:
            if output_arg and not output_arg.is_dir():
                print("[Error] For multiple inputs, --output must be a directory.")
                sys.exit(1)

            for ip in input_paths:
                target_dir = output_arg if output_arg else ip.parent
                out_file = target_dir / f"{ip.stem}_shrunk.cbz"
                # process_comic_lzma2 will handle its own tqdm bars internally
                process_comic_lzma2(ip, str(out_file), quality=args.quality)

        # Logic for single file
        else:
            ip = input_paths[0]
            if output_arg and output_arg.suffix.lower() in ('.cbz', '.zip'):
                out_file = output_arg
            elif output_arg:
                out_file = output_arg / f"{ip.stem}_shrunk.cbz"
            else:
                out_file = ip.parent / f"{ip.stem}_shrunk.cbz"

            process_comic_lzma2(ip, str(out_file), quality=args.quality)

    # --- GUI Mode ---
    else:
        run_gui_mode(args.quality)


def run_gui_mode(default_quality: int):
    """
    Tkinter GUI with two progress bars: Book-level and Page-level.
    """
    root = tk.Tk()
    root.title("Comic Shrinker")
    root.geometry("550x380")

    input_files: List[Path] = []

    # --- UI Logic ---
    def select_inputs():
        nonlocal input_files
        files = filedialog.askopenfilenames(
            title="Select Comics",
            filetypes=[("Comic Archives", "*.cbz *.cbr *.zip *.7z *.cb7")]
        )
        if files:
            input_files = [Path(f) for f in files]
            lbl_status.config(text=f"Selected: {len(input_files)} file(s)")

    def update_gui_progress(book_idx, total_books, pg_curr, pg_total, status_text):
        """
        Thread-safe callback for the processor.
        Calculates percentage for both Global and Local bars.
        """
        # Global bar (Books)
        global_pc = (book_idx / total_books) * 100
        # Local bar (Pages)
        local_pc = (pg_curr / pg_total * 100) if pg_total > 0 else 0

        root.after(0, lambda: pbar_global.configure(value=global_pc))
        root.after(0, lambda: pbar_local.configure(value=local_pc))
        if status_text:
            root.after(0, lambda: lbl_status.config(text=status_text))

    def start_processing():
        if not input_files:
            messagebox.showwarning("Warning", "Select input files first.")
            return

        # Determine Output Paths
        if len(input_files) > 1:
            out_dir = filedialog.askdirectory(title="Select Output Folder")
            if not out_dir: return
            out_paths = [Path(out_dir) / f"{f.stem}_shrunk.cbz" for f in input_files]
        else:
            out_file = filedialog.asksaveasfilename(
                title="Save Optimized Comic",
                defaultextension=".cbz",
                initialfile=f"{input_files[0].stem}_shrunk.cbz"
            )
            if not out_file: return
            out_paths = [Path(out_file)]

        def worker():
            btn_start.config(state="disabled")
            btn_select.config(state="disabled")
            try:
                total_books = len(input_files)
                for i, (in_p, out_p) in enumerate(zip(input_files, out_paths), 1):
                    # Local callback that injects book index info
                    def local_cb(curr, tot, status):
                        update_gui_progress(i, total_books, curr, tot, status)

                    process_comic_lzma2(
                        in_p,
                        str(out_p),
                        quality=default_quality,
                        progress_callback=local_cb
                    )

                messagebox.showinfo("Success", f"Processed {total_books} archives successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {str(e)}")
            finally:
                root.after(0, lambda: btn_start.config(state="normal"))
                root.after(0, lambda: btn_select.config(state="normal"))
                root.after(0, lambda: lbl_status.config(text="Ready"))

        threading.Thread(target=worker, daemon=True).start()

    # --- UI Layout ---
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill="both", expand=True)

    btn_select = ttk.Button(main_frame, text="1. Select Input Archives", command=select_inputs)
    btn_select.pack(pady=10)

    # Global Progress (Book Count)
    ttk.Label(main_frame, text="Overall Progress (Books):").pack(anchor="w")
    pbar_global = ttk.Progressbar(main_frame, length=450, mode="determinate")
    pbar_global.pack(pady=(0, 15))

    # Local Progress (Page Count)
    ttk.Label(main_frame, text="Current Archive Progress (Pages):").pack(anchor="w")
    pbar_local = ttk.Progressbar(main_frame, length=450, mode="determinate")
    pbar_local.pack(pady=(0, 15))

    lbl_status = ttk.Label(main_frame, text="Ready", wraplength=480, font=("Segoe UI", 9, "italic"))
    lbl_status.pack(pady=10)

    btn_start = ttk.Button(main_frame, text="2. Start Optimization", command=start_processing)
    btn_start.pack(pady=10)

    root.mainloop()


if __name__ == "__main__":
    main()
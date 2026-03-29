import PyInstaller.__main__
import os

# Define the entry point
entry_point = 'main.py'

def run_build():
    # Define the PyInstaller arguments
    params = [
        entry_point,
        '--onefile',             # Create a single EXE
        '--windowed',            # Hides console when GUI runs (standard for tools)
        '--name=ComicShrinker',  # Name of the output file
        '--clean',               # Clean cache before build
        # If you have an icon file, uncomment the line below:
        # '--icon=assets/icon.ico',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=numpy',
    ]

    # Run PyInstaller
    print("--- Starting PyInstaller Build ---")
    PyInstaller.__main__.run(params)

    dist_path = os.path.join(os.getcwd(), 'dist')
    print(f"\n--- Recursive Check of Output: {dist_path} ---")

    if os.path.exists(dist_path):
        # os.walk goes through every subfolder
        for root, dirs, files in os.walk(dist_path):
            for name in files:
                full_path = os.path.join(root, name)
                # Get path relative to 'dist' for cleaner logs
                rel_path = os.path.relpath(full_path, dist_path)
                file_size = os.path.getsize(full_path) / (1024 * 1024)
                print(f"  [FILE] {rel_path} ({file_size:.2f} MB)")
            for name in dirs:
                rel_path = os.path.relpath(os.path.join(root, name), dist_path)
                print(f"  [DIR ] {rel_path}")
    else:
        print("Error: 'dist' folder was not created.")
    print("--- Build Process Finished ---\n")

if __name__ == "__main__":
    run_build()

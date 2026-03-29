import PyInstaller.__main__
import os

# Define the entry point
entry_point = 'main.py'

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
PyInstaller.__main__.run(params)
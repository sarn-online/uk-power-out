"""Expose the repository integration alongside the HA test fixture components."""
from pathlib import Path
import custom_components

ROOT = str(Path(__file__).resolve().parents[2] / 'custom_components')
if ROOT not in custom_components.__path__:
    custom_components.__path__.append(ROOT)

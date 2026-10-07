"""Make the project root importable for tests when pytest is invoked from the project folder."""
import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

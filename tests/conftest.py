import sys
import os

# Add the project root directory to Python's path so pytest can find
# the ingestion module. Without this, pytest looks for modules relative
# to the tests/ folder and can't find anything outside it.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
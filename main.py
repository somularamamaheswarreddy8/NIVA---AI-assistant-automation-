"""
Root launcher for NIVA Universal AI Computer Control System.
Forwards to jarvis/main.py.
"""

import os
import sys

root_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.join(root_dir, "jarvis")
sys.path.insert(0, root_dir)
sys.path.insert(0, project_dir)

from jarvis.main import main

if __name__ == "__main__":
    main()

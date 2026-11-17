"""
Root launcher for NIVA NLU Model Training Pipeline.
Forwards to jarvis/train_nlu.py.
"""

import os
import sys

project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis")
sys.path.insert(0, project_dir)

from jarvis.train_nlu import train

if __name__ == "__main__":
    train()

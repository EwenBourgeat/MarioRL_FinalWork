"""Raccourci : python train_qlearning.py ... = python train.py --algo qlearning ...

(voir python train.py --help)
"""

import sys

from train import main

if __name__ == "__main__":
    sys.exit(main(["--algo", "qlearning", *sys.argv[1:]]))

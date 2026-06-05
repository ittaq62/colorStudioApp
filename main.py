# -*- coding: utf-8 -*-
"""
ColorStudio - entry point pour developpement (lancement depuis le repo).

Apres installation via `pip install -e .`, on peut aussi lancer avec :
    colorstudio
ou :
    python -m colorstudio
"""
import sys

from colorstudio.app import main


if __name__ == "__main__":
    sys.exit(main())

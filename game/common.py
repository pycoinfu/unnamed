"""
This file is a part of the 'Unnamed' source code.
The source code is distributed under the MIT license.
"""

import pathlib
import typing

# Generics

EventInfo = typing.Dict[str, typing.Any]

# Game stuff
WIDTH = 400
HEIGHT = 230

TILE_WIDTH = 16
TILE_HEIGHT = 16

# Paths
ROOT_DIR = pathlib.Path(".")
ASSETS_DIR = ROOT_DIR / "assets"
MAP_DIR = ASSETS_DIR / "maps"

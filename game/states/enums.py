"""
This file is a part of the 'Unnamed' source code.
The source code is distributed under the MIT license.
"""

import enum


class States(enum.Enum):
    """
    Enum for game states
    """

    MAIN_MENU = "main menu"
    LEVEL = "level"


class Dimensions(enum.Enum):
    """
    Enum for dimensions
    """

    PARALLEL_DIMENSION = "dimension_one"
    INVERTED_DIMENSION = "dimension_two"

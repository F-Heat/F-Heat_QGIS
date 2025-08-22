import sys
from pathlib import Path
import pandas as pd
import math

from adjust_files import Buildings_adj


def test_extract_year():
    assert Buildings_adj.extract_year('2023-07-17') == 2023
    assert math.isnan(Buildings_adj.extract_year(None))  # returns nan

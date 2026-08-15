import re
import numpy as np
import pandas as pd
from enum import Enum
from tqdm import tqdm
from collections import Counter
from pdfminer.high_level import extract_pages

from .pdf_model import extract_chars
from .convert_to_dataframe import convert_char_dataframe
from typing import List, Callable, Union


def read_pdf_chars(path_to_pdf: str, verbose: bool = False):
    pages = list(extract_pages(path_to_pdf))
    containers = extract_chars(pages)
    df = convert_char_dataframe(containers)
    return df
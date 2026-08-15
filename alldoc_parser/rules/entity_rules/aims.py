import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy

from graph_parser import Parser, ParserGroup, Text, Rule

from ..list_items_extractor import (
    apply_walker,

    ListItemWalkerOrdered,
    ListItemWalkerUnorderedAlphaLower,
    ListItemWalkerUnorderedAlphaUpper,
    ListItemWalkerUnorderedSym
)


gparser_rules = [
    Rule(
        Text("являются", lemma=True),
        Text("целями", lemma=True)
    )
]
re_rules = [
    {
        "pattern": r"Ц-\d{1,2}",
        "action": "match"
    },
    {
        "pattern": r"Цель[ ]*[–-]",
        "action": "match"
    },
    {
        "pattern": r"Цель[ ]*\d{1,2}(\.\d{1,2}){,4}",
        "action": "match"
    }
]


WALKERS = {
    "Ordered": ListItemWalkerOrdered,
    "UnorderedSymLower": ListItemWalkerUnorderedAlphaLower,
    "UnorderedSymUpper": ListItemWalkerUnorderedAlphaUpper,
    "UnorderedAlpha": ListItemWalkerUnorderedSym,
}


ENTITY_TYPE = "aim"
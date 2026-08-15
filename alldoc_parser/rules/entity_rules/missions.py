import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy

from graph_parser import Parser, ParserGroup, Text, Rule
from pdf2pandas import Paragraph

from ..list_items_extractor import (
    apply_walker,

    ListItemWalkerUnorderedAlphaLower,
    ListItemWalkerUnorderedAlphaUpper,
    ListItemWalkerUnorderedSym
)


WALKERS = {
    "UnorderedSymLower": ListItemWalkerUnorderedAlphaLower,
    "UnorderedSymUpper": ListItemWalkerUnorderedAlphaUpper,
    "UnorderedAlpha": ListItemWalkerUnorderedSym,
}

ENTITY_TYPE = "mission"


class FreeEntityClassifier:
    pass


class AnchorEntityParser:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose
        self.classifier = AnchorEntityClassifier(syntax)

    def __call__(self, df: pd.DataFrame):
        indices = list()
        for i, row in tqdm(df.iterrows(), disable=not self.verbose, total=len(df)):
            is_found = self.classifier(row)
            if is_found:
                indices.append(i)

        entities = list()
        for i in indices:
            body = df.loc[i]["text"]
            sub_sequences = {w: list() for w in WALKERS}
            sub_used_ids = {w: set() for w in WALKERS}
            for walker_name, walker in WALKERS.items():
                sm = walker()
                apply_walker(
                    sm,
                    body,
                    [],
                    sub_sequences[walker_name], 
                    i, 
                    df, 
                    sub_used_ids[walker_name],
                    entity_type=ENTITY_TYPE
                )
            sub_sequences = sorted(sub_sequences.items(), key=lambda x: len(x[1]), reverse=True)
            sequence = sub_sequences[0][1]
            entities.append(sequence)

        return entities


gparser_rules_anchor = [

]
re_rules_title_anchor = [
    {
        "pattern": r"Миссия",
        "action": "match"
    }
]
re_rules_anchor = [

]
class AnchorEntityClassifier:
    def __init__(self, syntax):
        self.syntax = syntax
        self.rparsers_title = list()
        for item in re_rules_title_anchor:
            self.rparsers_title.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))

    def __call__(self, row: pd.Series):
        is_found = False
        for rparser in self.rparsers_title:
            m = rparser(row["text"])
            if (m is not None
                and m.group() == row["text"].strip()
                and (is_bold(row.to_dict()) or is_italic(row.to_dict()))):
                is_found = True
                break
        return is_found
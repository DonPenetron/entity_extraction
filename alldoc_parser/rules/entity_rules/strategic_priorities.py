import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from utils import is_bold, is_italic

from graph_parser import Parser, ParserGroup, Text, Rule


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


ENTITY_TYPE = "strategic_priority"


class FreeEntityParser:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose
        self.classifier = FreeEntityClassifier(syntax, verbose)

    def __call__(self, df: pd.DataFrame):
        indices = list()
        for i, row in tqdm(df.iterrows(), disable=not self.verbose, total=len(df)):
            if self.classifier(row):
                indices.append((i, ENTITY_TYPE, row["text"], "entity"))
        return indices


re_rules_title_free = [

]
re_rules_free = [
    {
        "pattern": r"Стратегический[ ]{1,5}приоритет[ ]{1,5}\d[ ]{,5}[.]",
        "action": "match",
        "font_filter": lambda row: True,
        "entry_filter": lambda m, row: len(row["text"][m.start():].strip()) > 0,
        "ending_filter": lambda row: True,
    }
]

class FreeEntityClassifier:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose

        self.rparsers_title = list()
        for item in re_rules_title_free:
            self.rparsers_title.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"],
                "ending_filter": item["ending_filter"]
            })

        self.rparsers = list()
        for item in re_rules_free:
            self.rparsers.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"],
                "ending_filter": item["ending_filter"]
            })

    def __call__(self, row: pd.Series):
        is_found = False
        for rparser in self.rparsers:
            m = rparser["parser"](row["text"])
            if (m is not None
                and rparser["font_filter"](row)
                and rparser["entry_filter"](m, row)
                and rparser["ending_filter"](row)):
                is_found = True
                break
        return is_found


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
        "pattern": r"Стратегические приоритеты развития",
        "action": "match",
        "font_filter": lambda row: is_bold(row.to_dict()) or is_italic(row.to_dict()),
        "entry_filter": lambda m, row: m.group() == row["text"].strip(),
        "ending_filter": lambda row: True,
    },
    {
        "pattern": r"Стратегические приоритеты",
        "action": "match",
        "font_filter": lambda row: is_bold(row.to_dict()) or is_italic(row.to_dict()),
        "entry_filter": lambda m, row: m.group() == row["text"].strip(),
        "ending_filter": lambda row: True,
    }
]
re_rules_anchor = [

]

class AnchorEntityClassifier:
    def __init__(self, syntax):
        self.syntax = syntax

        self.rparsers_title = list()
        for item in re_rules_title_anchor:
            self.rparsers_title.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"],
                "ending_filter": item["ending_filter"]
            })

        self.rparsers = list()
        for item in re_rules_anchor:
            self.rparsers.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"],
                "ending_filter": item["ending_filter"]
            })

    def __call__(self, row: pd.Series):
        is_found = False
        for rparser in self.rparsers_title:
            m = rparser["parser"](row["text"])
            if (m is not None
                and rparser["font_filter"](row)
                and rparser["entry_filter"](m, row)
                and rparser["ending_filter"](row)):
                is_found = True
                break
        return is_found
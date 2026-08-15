import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from utils import is_bold, is_italic

from graph_parser import Parser, ParserGroup, Text, Rule

from ..list_items_extractor import (
    apply_walker,
    
    ListItemWalker,
    ListItemWalkerOrdered,
    ListItemWalkerUnorderedAlphaLower,
    ListItemWalkerUnorderedAlphaUpper,
    ListItemWalkerUnorderedSym
)

ENTITY_TYPE = "priority"


WALKERS = {
    "Ordered": ListItemWalkerOrdered,
    "UnorderedSymLower": ListItemWalkerUnorderedAlphaLower,
    "UnorderedSymUpper": ListItemWalkerUnorderedAlphaUpper,
    "UnorderedAlpha": ListItemWalkerUnorderedSym,
}


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
        "pattern": r"Приоритет[ ]{1,5}\d((\.\d){1,5}|(\.){,1})[ ]{,5}[«].+[»]",
        "action": "match",
        "font_filter": lambda row: True,
        "entry_filter": lambda m, row: len(row["text"][m.start():].strip()) > 0
    }
]

class FreeEntityClassifier:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose

        self.rparsers = list()
        for item in re_rules_free:
            self.rparsers.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"]
            })

    def __call__(self, row: pd.Series):
        is_found = False
        for rparser in self.rparsers:
            m = rparser["parser"](row["text"])
            if (m is not None
                and rparser["font_filter"](row)
                and rparser["entry_filter"](m, row)):
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
    Rule(
        Text("реализуются", lemma=True),
        Text("следующие", lemma=True),
        Text("приоритеты", lemma=True)
    ),
    Rule(
        Text("реализацией", lemma=True),
        Text("следующих", lemma=True),
        Text("приоритетов", lemma=True)
    ),
    Rule(
        Text("являются", lemma=True),
        Text("приоритетами", lemma=True)
    )
]
re_rules_title_anchor = [

]

class AnchorEntityClassifier:
    def __init__(self, syntax):
        self.syntax = syntax

        gparser_subparsers = list()
        for item in gparser_rules_anchor:
            gparser_subparsers.append(Parser(item, syntax_parser=syntax))
        self.gparser = ParserGroup(*gparser_subparsers, syntax_parser=syntax)

        self.rparsers_title = list()
        for item in re_rules_title_anchor:
            self.rparsers_title.append({
                "parser": eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"),
                "font_filter": item["font_filter"],
                "entry_filter": item["entry_filter"]
            })

    def __call__(self, row: pd.Series):
        is_found = False

        for rparser in self.rparsers_title:
            m = rparser["parser"](row["text"])
            if (m is not None
                and rparser["font_filter"](row)
                and rparser["entry_filter"](m, row)):
                is_found = True
                break

        if not is_found:
            is_found = self.gparser(row["text"]) is not None
            
        return is_found


# class PriorityParser:
#     def __init__(self, syntax, verbose: bool = False):
#         self.verbose = verbose
#         gparser_subparsers_p = list()
#         for item in gparser_rules:
#             gparser_subparsers_p.append(Parser(item, syntax_parser=syntax))
#         self.gparser = ParserGroup(*gparser_subparsers_p, syntax_parser=syntax)

#         self.rparser = list()
#         for item in re_rules:
#             self.rparser.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))

#     def __call__(self, df: pd.DataFrame):
#         indices = list()
#         used_ids = set()
#         for i, row in tqdm(df.iterrows(), disable=not self.verbose, total=len(df)):
#             sequence = list()

#             is_found = False
#             for pattern in self.rparser:
#                 if pattern(row["text"].strip()) is not None:
#                     if i not in used_ids:
#                         used_ids.add(i)
#                         sequence.append((i, row["text"], "entity"))
#                     is_found = True
#                     break
#             if is_found:
#                 indices.append(sequence)
#                 continue

#             if self.gparser(row["text"]) is not None:
#                 semicolon_m = re.search(":", row["text"])
#                 if semicolon_m is not None:
#                     body = row["text"][semicolon_m.start()+1:].strip()
#                     bullets = [x.strip() for x in body.split(";") if len(x.strip()) > 0]
#                 else:
#                     body = row["text"].strip()
#                     bullets = []
#                 if len(bullets) > 0 or row["text"].strip().endswith(":"):
#                     sub_sequences = {w: list() for w in WALKERS}
#                     sub_used_ids = {w: deepcopy(used_ids) for w in WALKERS}
#                     for walker_name, walker in WALKERS.items():
#                         sm = walker()
#                         apply_walker(
#                             sm,
#                             body,
#                             bullets, 
#                             sub_sequences[walker_name], 
#                             i, 
#                             df, 
#                             sub_used_ids[walker_name]
#                         )
#                     sub_sequences = sorted(sub_sequences.items(), key=lambda x: len(x[1]), reverse=True)
#                     sequence = sub_sequences[0][1]
#                 else:
#                     if i not in used_ids:
#                         used_ids.add(i)
#                         sequence.append((i, row["text"], "entity"))
#             if len(sequence) > 0:
#                 indices.append(sequence)
#         return indices
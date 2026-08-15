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
        Text("направлениями", lemma=True),
    )
]
gparser_rules_title = [
    Rule(
        Text("стратегическое", lemma=False),
        Text("направление", lemma=False),
    )
]
re_rules = [

]

WALKERS = {
    "Ordered": ListItemWalkerOrdered,
    "UnorderedSymLower": ListItemWalkerUnorderedAlphaLower,
    "UnorderedSymUpper": ListItemWalkerUnorderedAlphaUpper,
    "UnorderedAlpha": ListItemWalkerUnorderedSym,
}


class DirectionParser:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose
        gparser_subparsers_p = list()
        for item in gparser_rules:
            gparser_subparsers_p.append(Parser(item, syntax_parser=syntax))
        self.gparser = ParserGroup(*gparser_subparsers_p, syntax_parser=syntax)

        gparser_subparsers_p = list()
        for item in gparser_rules_title:
            gparser_subparsers_p.append(Parser(item, syntax_parser=syntax))
        self.gparser_title = ParserGroup(*gparser_subparsers_p, syntax_parser=syntax)

        self.rparser = list()
        for item in re_rules:
            self.rparser.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))

    def __call__(self, df: pd.DataFrame):
        indices = list()
        used_ids = set()
        for i, row in tqdm(df.iterrows(), disable=not self.verbose, total=len(df)):
            sequence = list()

            is_found = False
            for pattern in self.rparser:
                if pattern(row["text"].strip()) is not None:
                    if i not in used_ids:
                        used_ids.add(i)
                        sequence.append((i, row["text"], "entity"))
                    is_found = True
                    break
            if is_found:
                indices.append(sequence)
                continue

            is_found = False
            if "bold" in row["fontname"].lower() and self.gparser_title(row["text"].lower()) is not None:
                sequence.append((i, row["text"], "entity"))
                is_found = True
            if is_found:
                indices.append(sequence)
                continue

            if self.gparser(row["text"]) is not None:
                semicolon_m = re.search(":", row["text"])
                if semicolon_m is not None:
                    body = row["text"][semicolon_m.start()+1:].strip()
                    bullets = [x.strip() for x in body.split(";") if len(x.strip()) > 0]
                else:
                    body = row["text"].strip()
                    bullets = []
                if len(bullets) > 0 or row["text"].strip().endswith(":"):
                    sub_sequences = {w: list() for w in WALKERS}
                    sub_used_ids = {w: deepcopy(used_ids) for w in WALKERS}
                    for walker_name, walker in WALKERS.items():
                        sm = walker()
                        apply_walker(
                            sm, 
                            body,
                            bullets, 
                            sub_sequences[walker_name], 
                            i, 
                            df, 
                            sub_used_ids[walker_name]
                        )
                    sub_sequences = sorted(sub_sequences.items(), key=lambda x: len(x[1]), reverse=True)
                    sequence = sub_sequences[0][1]
                else:
                    if i not in used_ids:
                        used_ids.add(i)
                        sequence.append((i, row["text"], "entity"))
            if len(sequence) > 0:
                indices.append(sequence)
        return indices
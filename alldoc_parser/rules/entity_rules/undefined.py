import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy

from graph_parser import GraphParser, Edge, Or, Node, And

from ..list_items_extractor import (
    apply_walker,

    ListItemWalker,
    ListItemWalkerOrdered,
    ListItemWalkerUnorderedAlpha,
    ListItemWalkerUnorderedSym
)


gparser_rules = [

]
re_rules = [

]
re_rules_italic = [
    {
        "pattern": r"В рамках реализации цели [N№][ ]{,1}\d+",
        "action": "match"
    },
]


WALKERS = {
    "Ordered": ListItemWalkerOrdered,
    "UnorderedSym": ListItemWalkerUnorderedAlpha,
    "UnorderedAlpha": ListItemWalkerUnorderedSym,
}


class Parser:
    def __init__(self, tokenizer, syntax, verbose: bool = False):
        self.verbose = verbose
        gparser_rules_p = list()
        for item in gparser_rules:
            gparser_rules_p.append(
                Or(Edge(Node(next(tokenizer(item["start"]["text"])), is_morph=item["start"]["is_morph"]), 
                    Node(next(tokenizer(item["end"]["text"])), is_morph=item["end"]["is_morph"]))),
            )
        self.gparser = GraphParser(gparser_rules_p, tokenizer, syntax)
        self.rparser = list()
        for item in re_rules:
            self.rparser.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))
        self.rparser_italic = list()
        for item in re_rules_italic:
            self.rparser_italic.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))

    def parse(self, df: pd.DataFrame):
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

            if any([p(row["text"].strip()) for p in self.rparser_italic]) and "italic" in row["fontname"].lower():
                semicolon_m = re.search(":", row["text"])
                if semicolon_m is not None:
                    body = row["text"][semicolon_m.start()+1:].strip()
                    bullets = [x.strip() for x in body.split(";") if len(x.strip()) > 0]
                else:
                    body = row["text"].strip()
                    bullets = []
                if len(bullets) > 0 or row["text"].strip():
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
                    sequence.append((i, row["text"], "entity"))
            if len(sequence) > 0:
                indices.append(sequence)
        return indices
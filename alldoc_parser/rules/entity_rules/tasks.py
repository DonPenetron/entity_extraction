import re
import pandas as pd
from tqdm import tqdm
from copy import deepcopy
from utils import is_bold, is_italic

from pdf2pandas import Paragraph, Document
import regex_parser
from graph_parser import Parser, ParserGroup, Text, Rule

from ..list_items_extractor import (
    apply_walker,

    ListItemWalkerOrdered,
    ListItemWalkerUnorderedAlphaLower,
    ListItemWalkerUnorderedAlphaUpper,
    ListItemWalkerUnorderedSym
)


ENTITY_TYPE = "task"


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

    def __call__(self, document: Document):
        indices = list()
        for i, p in enumerate(tqdm(document.paragraphs, disable=not self.verbose, total=len(document.paragraphs))):
            if self.classifier(p):
                indices.append((i, ENTITY_TYPE, p.text, "entity"))
        return indices
    

re_rules_title_free = [

]
re_rules_free = [
    regex_parser.Pattern(
        [
            regex_parser.Text(r"З-\d{1,2}")
        ],
        position="prefix", entry="partial"
    ),
    regex_parser.Pattern(
        [
            regex_parser.Text(r"Задача \d+\.(\d+\.)*")
        ],
        position="prefix", entry="partial"
    )
]

class FreeEntityClassifier:
    def __init__(self, syntax, verbose: bool = False):
        self.verbose = verbose

        self.rparsers_title = re_rules_title_free
        self.rparsers = re_rules_free

    def __call__(self, p: Paragraph):
        is_found = False

        for rparser in self.rparsers:
            if rparser(p):
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
        Text("включает", lemma=True),
        Text("следующие", lemma=True),
        Text("задачи", lemma=True)
    ),
    Rule(
        Text("решение", lemma=True),
        Text("следующих", lemma=True),
        Text("задач", lemma=True)
    ),
    Rule(
        Text("реализация", lemma=True),
        Text("следующих", lemma=True),
        Text("задач", lemma=True)
    ),
    Rule(
        Text("задачами", lemma=True),
        Text("являются", lemma=True)
    )
]
re_rules_title_anchor = [
    {
        "pattern": r"Основная[ ]{1,5}задача",
        "action": "match",
        "font_filter": lambda row: is_bold(row.to_dict()) or is_italic(row.to_dict()),
        "entry_filter": lambda m, row: m.group() == row["text"].strip(),
        "ending_filter": lambda row: True,
    },
    {
        "pattern": r"Задачи",
        "action": "match",
        "font_filter": lambda row: is_bold(row.to_dict()) or is_italic(row.to_dict()),
        "entry_filter": lambda m, row: len(m.group()) + 1 == len(row["text"].strip()),
        "ending_filter": lambda row: row["text"].strip().endswith(":"),
    }
]
re_rules_anchor = [
    {
        "pattern": r"Задачи[ ]{,5}[,]{,1}[ ]{,5}направленные[ ]{1,5}на",
        "action": "match",
        "font_filter": lambda p: True,
        "entry_filter": lambda m, p: len(p.text[m.start():].strip()) > 0,
        "ending_filter": lambda p: p.text.strip().endswith(":"),
    }
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

    def __call__(self, p: Paragraph, verbose: bool = False):
        is_found = False

        for i, rparser in enumerate(self.rparsers_title):
            m = rparser["parser"](row["text"])
            if verbose and m is not None:
                print("="*10)
                print(f"pattern: {re_rules_title_anchor[i]['pattern']}")
                print(f"font_filter: {rparser['font_filter'](row)}")
                print(f"entry_filter: {rparser['entry_filter'](m, row)}")
                print(f"ending_filter: {rparser['ending_filter'](row)}")
            if (m is not None
                and rparser["font_filter"](row)
                and rparser["entry_filter"](m, row)
                and rparser["ending_filter"](row)):
                is_found = True
                break

        if not is_found:
            for rparser in self.rparsers:
                m = rparser["parser"](row["text"])
                if (m is not None
                    and rparser["font_filter"](row)
                    and rparser["entry_filter"](m, row)
                    and rparser["ending_filter"](row)):
                    is_found = True
                    break

        if not is_found:
            is_found = self.gparser(row["text"]) is not None
        return is_found
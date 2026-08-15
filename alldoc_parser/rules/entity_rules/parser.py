import re
import pandas as pd

from graph_parser import GraphParser, Edge, Or, Node, And

from . import aims


class EntityParser:
    def __init__(self, tokenizer, syntax):

        # aims
        gparser_rules_aims = list()
        for item in aims.gparser_rules:
            gparser_rules_aims.append(
                Or(Edge(Node(next(tokenizer(item["start"]["text"])), is_morph=item["start"]["is_morph"]), 
                    Node(next(tokenizer(item["end"]["text"])), is_morph=item["end"]["is_morph"]))),
            )
        self.gparser_aims = GraphParser(gparser_rules_aims, tokenizer, syntax)
        self.rparser_aims = list()
        for item in aims.re_rules:
            self.rparser_aims.append(eval(f"re.compile(r\"{item['pattern']}\").{item['action']}"))

    def parse(self, df: pd.DataFrame):
        pass
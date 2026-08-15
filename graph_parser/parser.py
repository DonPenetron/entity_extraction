from typing import Union
import networkx as nx
from networkx.algorithms.isomorphism import GraphMatcher
from yargy.tokenizer import MorphTokenizer

from .entities import Rule


class Parser:
    def __init__(self, rule: Rule, syntax_parser):
        self.syntax_parser = syntax_parser
        self.rule = rule
        self.tokenizer = MorphTokenizer()
        self._prepare_rules()

    def _prepare_rules(self):
        rules_G = list()
        for i, text in enumerate(self.rule.texts):
            text_parsed = self.syntax_parser(text)
            sentence = text_parsed.sentences[0]
            nodes, edges = list(), list()
            for j, word in enumerate(sentence.words):
                nx_node = self._syntax_node2nx_node(word, self.rule.rule_beams[i, j])
                nodes.append((word.id, nx_node))
                if word.head != 0:
                    edges.append((word.id, word.head, {"deprel": word.deprel}))
            rule_G = nx.Graph()
            rule_G.add_nodes_from(nodes)
            rule_G.add_edges_from(edges)
            rules_G.append(rule_G)
        self.rules_G = rules_G
    
    def _syntax_node2nx_node(self, syntax_node, node_rule):
        return {
            "id": syntax_node.id,
            "text": syntax_node.text,
            "lemma": syntax_node.lemma,
            "upos": syntax_node.upos,
            "start_char": syntax_node.start_char,
            "end_char": syntax_node.end_char,
            "eq": "lemma" if node_rule.lemma else "text"
        }
    
    def __call__(self, text: str, text_parsed: Union[str, None] = None):
        sentences_G = list()
        for sentence in text_parsed.sentences:
            nodes, edges = list(), list()
            for word in sentence.words:
                node_nx = {
                    "id": word.id,
                    "text": word.text,
                    "lemma": word.lemma,
                    "upos": word.upos,
                }
                nodes.append((word.id, node_nx))
                if word.head != 0:
                    edges.append((word.id, word.head, {"deprel": word.deprel}))
            G = nx.Graph()
            G.add_nodes_from(nodes)
            G.add_edges_from(edges)
            sentences_G.append(G)

        for i, sentence_G in enumerate(sentences_G):
            rule_idx = self._apply_rule_to_graph(sentence_G)
            if rule_idx is not None:
                return self.rule.texts[rule_idx]
            
    def check_rule_tokens_existance(self, text: str):
        text_norm = " ".join([x.normalized for x in self.tokenizer(text)])
        is_found = False
        if all([r.search(text) is not None for r in self.rule.regexes["text"]]):
            is_found = True
        is_found_norm = False
        if all([r.search(text_norm) is not None for r in self.rule.regexes["lemma"]]):
            is_found_norm = True
        return is_found and is_found_norm
        
    def _apply_rule_to_graph(self, sentence_G: nx.Graph):
        def node_match(n_t_attrs, n_p_attrs):
            if n_p_attrs["eq"] == "lemma":
                return n_t_attrs["lemma"] == n_p_attrs["lemma"]
            return n_t_attrs["text"] == n_p_attrs["text"]
        for i, rule_G in enumerate(self.rules_G):
            matcher = GraphMatcher(sentence_G, rule_G, node_match=node_match)
            for mapping in matcher.subgraph_isomorphisms_iter():
                # print(mapping)
                return i
            

class ParserGroup:
    def __init__(self, *parsers: Parser, syntax_parser):
        self.parsers = parsers
        self.syntax_parser = syntax_parser

    def __call__(self, text: str):
        potential_rules = list()
        for p in self.parsers:
            if p.check_rule_tokens_existance(text):
                potential_rules.append(p)
        if len(potential_rules) == 0:
            return
        text_parsed = self.syntax_parser(text)
        for p in potential_rules:
            r = p(text, text_parsed)
            if r is not None:
                return r
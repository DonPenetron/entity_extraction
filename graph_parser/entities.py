import re
import numpy as np
from yargy.tokenizer import MorphTokenizer


tokenizer = MorphTokenizer()


class Token:
    def __init__(self):
        pass


class Text(Token):
    def __init__(self, text: str, lemma: bool = False):
        self.text = text
        self.lemma = lemma


class Or(Token):
    def __init__(self, *tokens: Token):
        self.tokens = tokens

    def __len__(self):
        return len(self.tokens)
    
    def __iter__(self):
        for token in self.tokens:
            yield token


class Rule:
    def __init__(self, *tokens: Token):
        self.tokens = tokens
        self._unsqueeze_tokens()

    def _unsqueeze_tokens(self):

        tokens_set = list()
        for token in self.tokens:
            if isinstance(token, Text):
                tokens_set.append(token)
            elif isinstance(token, Or):
                tokens_set.extend([x for x in token])

        tokens_morph_set = list()
        for item in tokens_set:
            tokens_morph_set.append({
                "text": item.text,
                "lemma": next(tokenizer(item.text)).normalized,
                "eq": "lemma" if item.lemma else "text"
            })

        self.regexes = {"text": list(), "lemma": list()}
        for item in tokens_morph_set:
            self.regexes[item["eq"]].append(item[item["eq"]])
        for k, v in self.regexes.items():
            v_n = list()
            for x in v:
                v_n.append(re.compile(x))
            self.regexes[k] = v_n

        self.rule_beams = np.zeros((1, len(self.tokens)), dtype=object)
        for i, token in enumerate(self.tokens):
            if isinstance(token, Text):
                self.rule_beams[:, i] = token
            elif isinstance(token, Or):
                beam_width = self.rule_beams.shape[0]
                self.rule_beams = np.tile(self.rule_beams, (len(token), 1))
                for j, inner_token in enumerate(token):
                    self.rule_beams[j*beam_width : (j+1)*beam_width, i] = inner_token
        self.texts = list()
        for beam in self.rule_beams:
            self.texts.append(" ".join([x.text for x in beam]))
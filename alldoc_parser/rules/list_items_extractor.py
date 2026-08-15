import re
import pandas as pd
from typing import Union
from statemachine import StateMachine, State


def apply_walker(
        sm,
        body: str,
        bullets: list, 
        sequence: list,
        start_idx: int,
        df: pd.DataFrame,
        used_ids: set,
        entity_type: Union[str, None] = None,
):
    sequence.append((start_idx, entity_type, df.loc[start_idx]["text"], "anchor"))
    for b in bullets:
        sm.current_row = b
        sm.move()
        if sm.current_state.final:
            break
        elif sm.current_state.name == sm.positive_state:
            sequence.append((start_idx, b))
    # print("===" + type(sm).__name__ + "===")
    for k, row_t in df.loc[start_idx+1:].iterrows():
        # print(sequence)
        # print(sm.current_state.final)
        # print(sm.current_state.name)
        if sm.current_state.final:
            break
        sm.current_row = row_t["text"].strip()
        sm.move()
        if sm.current_state.final:
            break
        elif sm.current_state.name == sm.positive_state:
            if k not in used_ids:
                used_ids.add(k)
                sequence.append((k, entity_type, row_t["text"], "entity"))


class ListItemWalker(StateMachine):

    current_row = ""
    counter = None
    symbol = None

    initial = State("Init", initial=True)
    ordered_list_item = State("OLI")
    unordered_list_item = State("ULI")
    final = State("Final", final=True)

    ordered_list_item_parser = re.compile(r"\d+([).]\d+){,4}", re.IGNORECASE)
    unordered_list_item_parser = re.compile("[-+*]", re.IGNORECASE)

    move = (
        initial.to(ordered_list_item, cond="current_row_oli", )
        | initial.to(unordered_list_item, cond="current_row_uli")
        | initial.to(final, cond="current_row_default")

        | ordered_list_item.to.itself(cond="current_row_oli")
        | ordered_list_item.to(final, cond="current_row_not_oli")

        | unordered_list_item.to.itself(cond="current_row_uli")
        | unordered_list_item.to(final, cond="current_row_not_uli")
    )

    def current_row_oli(self):
        if self.ordered_list_item_parser.match(self.current_row) is None:
            return False
        number = self.ordered_list_item_parser.search(self.current_row).group()
        last_number = re.sub("[^0-9]", " ", number.strip()).split()[-1].strip()
        current_row_number = int(last_number)
        if self.counter is not None:
            if current_row_number == self.counter + 1:
                return True
            return False
        return True
    
    def current_row_not_oli(self):
        return not self.current_row_oli()
    
    def current_row_uli(self):
        if self.unordered_list_item_parser.match(self.current_row) is None:
            return False
        current_row_symbol = self.current_row[0]
        if self.symbol is not None:
            if current_row_symbol == self.symbol:
                return True
            return False
        return True
    
    def current_row_not_uli(self):
        return not self.current_row_uli()
    
    def current_row_default(self):
        return self.current_row_not_oli() and self.current_row_not_uli()
    
    def on_enter_ordered_list_item(self):
        if self.counter is None:
            number = self.ordered_list_item_parser.search(self.current_row).group()
            last_number = re.sub("[^0-9]", " ", number.strip()).split()[-1].strip()
            self.counter = int(last_number)
        else:
            self.counter += 1

    def on_enter_unordered_list_item(self):
        if self.symbol is None:
            self.counter = self.current_row[0]


class ListItemWalkerOrdered(StateMachine):

    current_row = ""
    counter = None
    positive_state = "OLI"

    initial = State("Init", initial=True)
    ordered_list_item = State(positive_state)
    final = State("Final", final=True)

    ordered_list_item_parser = re.compile(r"\d+([).]\d+){,4}", re.IGNORECASE)

    move = (
        initial.to(ordered_list_item, cond="current_row_oli")
        | initial.to(final, cond="current_row_not_oli")

        | ordered_list_item.to.itself(cond="current_row_oli")
        | ordered_list_item.to(final, cond="current_row_not_oli")
    )

    def current_row_oli(self):
        if self.ordered_list_item_parser.match(self.current_row) is None:
            return False
        number = self.ordered_list_item_parser.search(self.current_row).group()
        last_number = re.sub("[^0-9]", " ", number.strip()).split()[-1].strip()
        current_row_number = int(last_number)
        if self.counter is not None:
            if current_row_number == self.counter + 1:
                return True
            return False
        return True
    
    def current_row_not_oli(self):
        return not self.current_row_oli()
    
    def on_enter_ordered_list_item(self):
        if self.counter is None:
            number = self.ordered_list_item_parser.search(self.current_row).group()
            last_number = re.sub("[^0-9]", " ", number.strip()).split()[-1].strip()
            self.counter = int(last_number)
        else:
            self.counter += 1


class ListItemWalkerUnorderedSym(StateMachine):

    current_row = ""
    symbol = None
    positive_state = "ULI"

    initial = State("Init", initial=True)
    unordered_list_item = State(positive_state)
    final = State("Final", final=True)

    unordered_list_item_parser = re.compile(r"[\-+*▪]", re.IGNORECASE)

    move = (
        initial.to(unordered_list_item, cond="current_row_uli")
        | initial.to(final, cond="current_row_not_uli")

        | unordered_list_item.to.itself(cond="current_row_uli")
        | unordered_list_item.to(final, cond="current_row_not_uli")
    )
    
    def current_row_uli(self):
        if self.unordered_list_item_parser.match(self.current_row) is None:
            return False
        current_row_symbol = self.current_row[0]
        if self.symbol is not None:
            if current_row_symbol == self.symbol:
                return True
            return False
        return True
    
    def current_row_not_uli(self):
        return not self.current_row_uli()

    def on_enter_unordered_list_item(self):
        if self.symbol is None:
            self.symbol = self.current_row[0]


class ListItemWalkerUnorderedAlphaLower(StateMachine):

    current_row = ""
    positive_state = "ULI"

    initial = State("Init", initial=True)
    unordered_list_item = State(positive_state)
    final = State("Final", final=True)

    unordered_list_item_parser = re.compile("[а-яё]")

    move = (
        initial.to(unordered_list_item, cond="current_row_uli")
        | initial.to(final, cond="current_row_not_uli")

        | unordered_list_item.to.itself(cond="current_row_uli")
        | unordered_list_item.to(final, cond="current_row_not_uli")
    )
    
    def current_row_uli(self):
        if self.unordered_list_item_parser.match(self.current_row) is None:
            return False
        return True
    
    def current_row_not_uli(self):
        return not self.current_row_uli()
    

class ListItemWalkerUnorderedAlphaUpper(StateMachine):

    current_row = ""
    positive_state = "ULI"

    initial = State("Init", initial=True)
    unordered_list_item = State(positive_state)
    final = State("Final", final=True)

    unordered_list_item_parser = re.compile("[А-ЯЁ]")

    move = (
        initial.to(unordered_list_item, cond="current_row_uli")
        | initial.to(final, cond="current_row_not_uli")

        | unordered_list_item.to.itself(cond="current_row_uli")
        | unordered_list_item.to(final, cond="current_row_not_uli")
    )
    
    def current_row_uli(self):
        if self.unordered_list_item_parser.match(self.current_row) is None:
            return False
        return True
    
    def current_row_not_uli(self):
        return not self.current_row_uli()
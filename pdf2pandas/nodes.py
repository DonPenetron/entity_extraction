import re
from dataclasses import dataclass
from pdfminer.layout import (LTTextContainer, LTChar, LTAnno, 
                             LTRect, LTFigure, LTImage, LTPage,
                             LTLine)
from typing import List


def make_newline_printable(s: str):
    return re.sub("\n", "[NEW_LINE]", s)


@dataclass
class Coordinates:
    x_down_left: float
    y_down_left: float
    x_upper_right: float
    y_upper_right: float

    def __repr__(self):
        return f"(({self.x_down_left},{self.y_down_left}),({self.x_upper_right},{self.y_upper_right}))"
    
    def to_dict(self):
        return {
            "x_dl": self.x_down_left, "y_dl": self.y_down_left,
            "x_ur": self.x_upper_right, "y_ur": self.y_upper_right
        }


class Node:
    def __init__(self, x_dl: float, y_dl: float, x_ur: float, y_ur: float, name: str, idx: int, precision: int = 3):
        self.idx = idx
        if x_dl is not None:
            x_dl = round(x_dl, precision)
        if y_dl is not None:
            y_dl = round(y_dl, precision)
        if x_ur is not None:
            x_ur = round(x_ur, precision)
        if y_ur is not None:
            y_ur = round(y_ur, precision)
        self.coordinates = Coordinates(
            x_down_left=x_dl, y_down_left=y_dl,
            x_upper_right=x_ur, y_upper_right=y_ur
        )
        self.node_type = name


class LTCharNode(Node):
    def __init__(self, fontname: str, text: str, *argv):
        super(LTCharNode, self).__init__(*argv)
        self.fontname = fontname
        self.text = text
        self.height = self.coordinates.y_upper_right - self.coordinates.y_down_left
        self.width = self.coordinates.x_upper_right - self.coordinates.x_down_left

    def to_tag(self, level: int):
        return (f"{'\t'*level}<{self.node_type} "
                f"idx={self.idx} "
                f"fontname={self.fontname} "
                f"coordinates={self.coordinates}>"
                f"{make_newline_printable(self.text)}"
                f"</{self.node_type}>")
    
    def __repr__(self):
        return f"{self.node_type} --- {self.text}"
    

class LTAnnoNode(Node):
    def __init__(self, text: str, *argv):
        super(LTAnnoNode, self).__init__(*[None]*4, *argv)
        self.text = text

    def to_tag(self, level: int):
        return (f"{'\t'*level}<{self.node_type} idx={self.idx}>"
                f"{make_newline_printable(self.text)}"
                f"</{self.node_type}>")

    def __repr__(self):
        return f"{self.node_type} --- {self.text}"


class LTRectNode(Node):
    def __init__(self, *argv):
        super(LTRectNode, self).__init__(*argv)

    def to_tag(self, level: int):
        return (f"{'\t'*level}<{self.node_type} idx={self.idx} coordinates={self.coordinates}>"
                f"</{self.node_type}>")
    

class LTContainerNode(Node):
    def __init__(self, children: list, *argv):
        super(LTContainerNode, self).__init__(*argv)
        self.children: List[Node] = children

    def to_tag(self, level: int):
        children_tags = [child.to_tag(level+1) for child in self.children]
        return (f"{'\t'*level}<{self.node_type} "
                f"idx={self.idx} "
                f"coordinates={self.coordinates}>"
                "\n" + "\n".join(children_tags) + "\n"
                f"{'\t'*level}</{self.node_type}>")
    
    def __iter__(self):
        for child in self.children:
            yield child

    def add_children(self, children: List[Node]):
        self.children.extend(children)

    def add_child(self, child: Node):
        self.children.append(child)

    def rewrite_children(self, children: List[Node]):
        self.children = children


class LTCommonContainerNode(LTContainerNode):
    def __init__(self, *argv):
        super(LTCommonContainerNode, self).__init__(*argv)


class LTCharContainerNode(LTContainerNode):
    def __init__(self, *argv):
        super(LTCharContainerNode, self).__init__(*argv)

    def add_children(self, children: List[LTCharNode]):
        assert all([isinstance(x, LTCharNode) for x in children])
        self.children.extend(children)

    def add_child(self, child: LTCharNode):
        assert isinstance(child, LTCharNode)
        self.children.append(child)

    def rewrite_children(self, children: List[LTCharNode]):
        assert all([isinstance(x, LTCharNode) for x in children])
        self.children = children

    def aggregate(self):
        return {
            "idx": self.idx,
            "text": "".join([x.text for x in self.children]),
            "fontname": self.children[0].fontname,
            "height": self.coordinates.y_upper_right - self.coordinates.y_down_left,
            "width": self.coordinates.x_upper_right - self.coordinates.x_down_left,
            "x_down_left": self.coordinates.x_down_left,
            "y_down_left": self.coordinates.y_down_left,
            "x_upper_right": self.coordinates.x_upper_right,
            "y_upper_right": self.coordinates.y_upper_right,
        }
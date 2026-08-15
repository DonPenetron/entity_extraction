import re
import numpy as np
import pandas as pd
from enum import Enum
from tqdm import tqdm
from collections import Counter

from pdfminer.high_level import extract_pages
from pdfminer.layout import (LTTextContainer, LTChar, LTAnno, 
                             LTRect, LTFigure, LTImage, LTPage,
                             LTLine, LTCurve)
from typing import List, Callable, Union

from . import nodes


UNPROCESSED_NODES = (
    LTFigure, LTImage, LTLine, LTRect, LTAnno, LTCurve
)
UNPROCESSED_NODES_SET = {
    "LTFigure", "LTImage", "LTLine", "LTRect", "LTAnno", "LTCurve"
}

    
def convert_2_pdf_model(item, parent: nodes.LTContainerNode, start_idx: int = 1):
    node_counter = start_idx
    char_children: List[LTChar] = list()
    container_children: List[LTTextContainer] = list()
    parent_children: List[nodes.Node] = list()

    for x in item:
        if isinstance(x, LTTextContainer):
            container_children.append(x)
        elif isinstance(x, LTChar):
            char_children.append(x)
        elif isinstance(x, UNPROCESSED_NODES):
            continue
        else:
            print(x)
            print(type(x))
            raise Exception
        
    if len(char_children) > 0 and len(container_children) > 0:
        xs, ys = list(), list()
        for child in char_children:
            xs.append(child.x0)
            xs.append(child.x1)
            ys.append(child.y0)
            ys.append(child.y1)
        container_node = nodes.LTCharContainerNode(
            list(),
            min(xs), min(ys), max(xs), max(ys),
            "LTCharContainerNode",
            node_counter
        )
        node_counter += 1
        for child in char_children:
            text = child.get_text()
            child_node = nodes.LTCharNode(
                child.fontname, text, 
                child.x0, child.y0, child.x1, child.y1,
                "LTCharNode",
                node_counter
            )
            node_counter += 1
            container_node.add_child(child_node)
        parent_children.append(container_node)
    elif len(char_children) > 0:
        assert isinstance(parent, nodes.LTCharContainerNode)
        for child in char_children:
            text = child.get_text()
            child_node = nodes.LTCharNode(
                child.fontname, text, 
                child.x0, child.y0, child.x1, child.y1,
                "LTCharNode",
                node_counter
            )
            node_counter += 1
            parent_children.append(child_node)

    if len(container_children) > 0:
        for child in container_children:
            child_types = set([type(x).__name__ for x in child]) - UNPROCESSED_NODES_SET
            if child_types == {"LTChar"}:
                child_node = nodes.LTCharContainerNode(
                    list(), 
                    child.x0, child.y0, child.x1, child.y1,
                    "LTCharContainerNode",
                    node_counter
                )
                node_counter += 1
                node_counter = convert_2_pdf_model(child, child_node, node_counter)
                parent_children.append(child_node)
            else:
                child_node = nodes.LTCommonContainerNode(
                    list(), 
                    child.x0, child.y0, child.x1, child.y1,
                    "LTCommonContainerNode",
                    node_counter
                )
                node_counter += 1
                node_counter = convert_2_pdf_model(child, child_node, node_counter)
                parent_children.append(child_node)
    
    parent.add_children(parent_children)
    return node_counter


def remove_one_child_nodes(node):
    if hasattr(node, "children"):
        children_pruned = list()
        for child in node.children:
            if remove_one_child_nodes(child):
                children_pruned.extend(child.children)
            else:
                children_pruned.append(child)
        node.children = children_pruned
        if len(node.children) == 1:
            return True
    return False

        
def read_pdf(path_to_pdf: str, verbose: bool = False):
    root_nodes: List[nodes.LTCommonContainerNode] = list()
    for page in tqdm(extract_pages(path_to_pdf), disable=not verbose):
        root_node = nodes.LTCommonContainerNode(list(), None, None, None, None, "root", 0)
        convert_2_pdf_model(page, root_node)

        one_child_node_ids = list()
        search_nodes_in_tree(root_node, is_one_child_container, one_child_node_ids)
        assert len(one_child_node_ids) == len(set(one_child_node_ids))
        remove_nodes_from_tree_soft(root_node, set(one_child_node_ids))
        
        # spire_node_ids = list()
        # search_nodes_in_tree(root_node, is_spire_doc_node, spire_node_ids)
        # assert len(spire_node_ids) == len(set(spire_node_ids))
        # remove_nodes_from_tree_hard(root_node, set(spire_node_ids))

        root_nodes.append(root_node)

    # remove_colontitle_nodes(root_nodes, verbose)
    return root_nodes


def search_nodes_in_tree(node: nodes.LTContainerNode, condition: Callable, result: list):
    assert isinstance(node, nodes.LTContainerNode)
    for child in node:
        if isinstance(child, nodes.LTContainerNode):
            if condition(child):
                result.append(child.idx)
            search_nodes_in_tree(child, condition, result)


def remove_nodes_from_tree_hard(node: nodes.LTContainerNode, nodes_to_remove: set):
    children_n = list()
    for child in node.children:
        if isinstance(child, nodes.LTContainerNode) and child.idx not in nodes_to_remove:
            remove_nodes_from_tree_hard(child, nodes_to_remove)
            children_n.append(child)
        elif isinstance(child, nodes.LTCharNode):
            children_n.append(child)
    node.rewrite_children(children_n)


def remove_nodes_from_tree_soft(node: nodes.LTCommonContainerNode, nodes_to_remove: set):
    children_n = list()
    for child in node.children:
        if isinstance(child, nodes.LTCommonContainerNode):
            if child.idx not in nodes_to_remove:
                remove_nodes_from_tree_soft(child, nodes_to_remove)
                children_n.append(child)
            else:
                children_n.extend(child.children)
        elif isinstance(child, (nodes.LTCharNode, nodes.LTCharContainerNode)):
            children_n.append(child)
    node.rewrite_children(children_n)
    

def is_spire_doc_node(node: nodes.LTContainerNode):
    child_types = set([type(x).__name__ for x in node.children])
    if len(child_types) > 1:
        print(set([type(x).__name__ for x in node.children]))
        raise Exception
    elif len(child_types) == 0:
        print(node)
        raise Exception
    else:
        if isinstance(node.children[0], nodes.LTCharNode):
            if ("".join([x.text for x in node.children])).strip() == "Evaluation Warning: The document was created with Spire.Doc for Python.":
                return True
    return False


def is_one_child_container(node: nodes.LTCommonContainerNode):
    if not isinstance(node, nodes.LTCommonContainerNode):
        return False
    if len(node.children) > 1:
        return False
    elif len(node.children) == 1:
        return True
    

def is_empty_container(node: nodes.LTCommonContainerNode):
    pass


def get_text_blocks(node: nodes.LTContainerNode, result: list):
    char_children: List[nodes.LTCharNode] = list()
    container_children: List[nodes.LTContainerNode] = list()
    for child in node.children:
        if isinstance(child, nodes.LTCharNode):
            char_children.append(child)
        elif isinstance(child, nodes.LTContainerNode):
            container_children.append(child)
    if len(char_children) > 0:
        result.append({
            "parent_idx": node.idx,
            "text": "".join([x.text for x in char_children]),
            "fontname": char_children[0].fontname,
            "size": char_children[0].coordinates.y_upper_right - char_children[0].coordinates.y_down_left,
            "y": node.coordinates.y_down_left,
            "x": node.coordinates.x_down_left,
        })
    for child in container_children:
        get_text_blocks(child, result)


def remove_colontitle_nodes(root_nodes: list, verbose: bool = False):
    text_blocks = list()
    for node in tqdm(root_nodes, disable=not verbose):
        text_block = list()
        get_text_blocks(node, text_block)
        text_blocks.append(text_block)

    fontnames, sizes, deltas = list(), list(), list()
    lines_per_page, deltas_per_page = list(), list()
    for item in text_blocks:
        fontnames.extend([x["fontname"] for x in item])
        lines = sorted(set([x["y"] for x in item]), reverse=True)
        deltas_per_page.append(np.array(lines[1:-1])[:-1] - np.array(lines[1:-1])[1:])
        deltas.extend(np.array(lines[1:-1])[:-1] - np.array(lines[1:-1])[1:])
        lines_per_page.append(lines)
        sizes.extend([x["size"] for x in item])

    fontname_weights = dict()
    for k, v in Counter(fontnames).items():
        fontname_weights[k] = v / len(fontnames)
    sizes_weights = dict()
    for k, v in Counter([round(x, 1) for x in sizes]).items():
        sizes_weights[k] = v / len(sizes)

    statistics = {
        "dominant_fontnames": [k for k, v in fontname_weights.items() if v > .3],
        "dominant_sizes": [k for k, v in sizes_weights.items() if v > .3],
        "threshold_delta": np.quantile(deltas, 0.5) + (np.quantile(deltas, 0.75) - np.quantile(deltas, 0.25)) / 2,
    }


    def bad_header_check(line: dict, statistics: dict):
        checks = dict()
        checks["fontname"] = line["fontname"] not in statistics["dominant_fontnames"]
        checks["size"] = line["size"] not in statistics["dominant_sizes"]
        checks["delta"] = line["delta"] > statistics["threshold_delta"]
        if len(re.sub("[^0-9]+", "", line["text"])) == len(line["text"]) and len(line["text"]) < 4:
            checks["text"] = True
        return np.sum(list(checks.values())) > 1

    def clean_text(s: str):
        s_clean = re.sub(" ", "", s)
        return s_clean


    nodes_to_remove_per_page = list()
    for text_block, lines in zip(text_blocks, lines_per_page):
        first_line_pos, last_line_pos = lines[0], lines[-1]
        first_line_text, last_line_text = list(), list()
        for x in text_block:
            if np.isclose(x["y"], first_line_pos):
                first_line_text.append(x)
            elif np.isclose(x["y"], last_line_pos):
                last_line_text.append(x)
        nodes_to_remove = list()
        for item in first_line_text:
            item_n = {
                "fontname": item["fontname"],
                "size": item["size"],
                "delta": lines[0] - lines[1],
                "text": clean_text(item["text"]),
            }
            if bad_header_check(item_n, statistics):
                nodes_to_remove.append(item["parent_idx"])
        for item in last_line_text:
            item_n = {
                "fontname": item["fontname"],
                "size": item["size"],
                "delta": lines[-2] - lines[-1],
                "text": clean_text(item["text"]),
            }
            if bad_header_check(item_n, statistics):
                nodes_to_remove.append(item["parent_idx"])
        nodes_to_remove_per_page.append(nodes_to_remove)

    for root_node, nodes_to_remove in zip(root_nodes, nodes_to_remove_per_page):
        remove_nodes_from_tree_hard(root_node, nodes_to_remove)


def extract_chars(pages: List[LTPage]):
    container = list()
    for page in pages:
        cur_container = list()
        extract_chars_from_page(page, cur_container)
        container.append(cur_container)
    return container
    

def extract_chars_from_page(item, container: list, start_idx: int = 1):
    node_counter = start_idx
    char_children: List[LTChar] = list()
    container_children: List[LTTextContainer] = list()

    for x in item:
        if isinstance(x, LTTextContainer):
            container_children.append(x)
        elif isinstance(x, LTChar):
            char_children.append(x)
        elif isinstance(x, UNPROCESSED_NODES):
            continue
        else:
            print(x)
            print(type(x))
            raise Exception
        
    for child in char_children:
        text = child.get_text()
        child_node = nodes.LTCharNode(
            child.fontname, text, 
            child.x0, child.y0, child.x1, child.y1,
            "LTCharNode",
            node_counter
        )
        node_counter += 1
        container.append(child_node)

    for child in container_children:
        node_counter = extract_chars_from_page(child, container, node_counter)
    
    return node_counter
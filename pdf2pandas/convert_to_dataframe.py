import os
import re
import numpy as np
import pandas as pd
from tqdm import tqdm
from typing import List, Union
from collections import Counter

from .nodes import (
    LTContainerNode,
    LTCharContainerNode,
    LTCommonContainerNode,
    LTCharNode
)
from .pdf_model import read_pdf
from .data_formats import DATA_TYPES


def extract_row_containers_from_pdf(path_to_pdf: str, doc_name: Union[str, None], verbose: bool = False):
    root_nodes = read_pdf(path_to_pdf=path_to_pdf, verbose=verbose)
    if doc_name is None:
        doc_name = os.path.splitext(os.path.basename(path_to_pdf))[0]
    df = convert_to_dataframe(root_nodes, doc_name)
    row_containers = unite_rows(df, verbose=verbose)
    return row_containers


def convert_to_dataframe(root_nodes: List[LTCommonContainerNode], doc_name: str, verbose: bool = False):
    df = list()
    for i, root_node in enumerate(tqdm(root_nodes, disable=not verbose)):
        ltchar_containers: List[LTCharContainerNode] = list()
        extract_ltchar_containers(root_node, ltchar_containers)
        for container in ltchar_containers:
            x = {**container.aggregate()}
            for k, v in x.items():
                x[k] = DATA_TYPES[k](x[k])
            if len(re.sub("[^A-Za-zА-Яа-яЁё0-9]+", "", x["text"])) == 0:
                continue
            x["page_number"] = i+1
            df.append(x)
    df = pd.DataFrame(df)
    df.loc[:, "doc_name"] = [doc_name]*len(df)
    return df


def extract_ltchar_containers(node: LTContainerNode, result: List[LTCharContainerNode]):
    for child in node.children:
        if isinstance(child, LTCharContainerNode):
            result.append(child)
        elif isinstance(child, LTCommonContainerNode):
            extract_ltchar_containers(child, result)


def unite_rows(df: pd.DataFrame, verbose: bool = False):
    df_sorted = df.sort_values(["page_number", "y_down_left", "x_down_left"], ascending=[True, False, True])
    token_groups = group_tokens(df_sorted)
    df_n = list()
    for group in token_groups:
        fontnames = sorted(Counter([x["fontname"] for x in group]).items(), key=lambda x: x[1], reverse=False)
        fontname = fontnames[0][0]
        item = {
            "text": "".join([x["text"] for x in group]),
            "fontname": fontname,
            "height": abs(group[0]["y_down_left"] - group[-1]["y_upper_right"]),
            "width": abs(group[-1]["x_upper_right"] - group[0]["x_down_left"]),
            "x_down_left": group[0]["x_down_left"],
            "y_down_left": group[0]["y_down_left"],
            "x_upper_right": group[-1]["x_upper_right"],
            "y_upper_right": group[-1]["y_upper_right"],
            "page_number": group[0]["page_number"],
        }
        df_n.append(item)
    df_n = pd.DataFrame(df_n)
    return df_n


def group_tokens(df: pd.DataFrame):
    tokens = list()
    token = list()
    previous_row = None
    for i, (_, row) in enumerate(df.iterrows()):
        if i == 0:
            token.append(row)
            previous_row = row
            continue
        if (np.isclose(row["y_down_left"], previous_row["y_down_left"])
            and row["page_number"] == previous_row["page_number"]):
            token.append(row)
        else:
            if len(token) > 0:
                tokens.append(token)
            token = [row]
        previous_row = row
    if len(token) > 0:
        tokens.append(token)
    return tokens


def get_paragraphs(df: pd.DataFrame):
    stats = compute_p_start_and_red_line(df)
    paragraphs = list()
    paragraph = list()
    for i, row in df.iterrows():
        if round(row["x_down_left"]) >= stats["red_line"]:
            paragraphs.append(pd.DataFrame(paragraph))
            paragraph = [row]
        else:
            paragraph.append(row)
    paragraphs.append(pd.DataFrame(paragraph))
    paragraphs_n = list()
    for paragraph in paragraphs:
        if len(paragraph) == 0:
            continue
        ids = list()
        for item in paragraph["idx"].values:
            ids.extend(item)
        x_down_left = min(paragraph["x_down_left"].values)
        y_down_left = min(paragraph["y_down_left"].values)
        x_upper_right = max(paragraph["x_upper_right"].values)
        y_upper_right = max(paragraph["y_upper_right"].values)
        paragraphs_n.append(pd.Series({
            "idx": ids,
            "text": " ".join(paragraph["text"].values),
            "fontname": paragraph["fontname"].values[0],
            "height": paragraph["height"].values[0],
            "width": paragraph["width"].values[0],
            "x_down_left": x_down_left,
            "y_down_left": y_down_left,
            "x_upper_right": x_upper_right,
            "y_upper_right": y_upper_right,
            "page_number": paragraph["page_number"].values[0],
            "doc_name": paragraph["doc_name"].values[0],
        }))
    return pd.DataFrame(paragraphs_n)


def compute_p_start_and_red_line(df: pd.DataFrame, p_start_th: float = 0.1):
    stats = df["x_down_left"].apply(lambda x: round(x)).value_counts(normalize=True)
    stats = stats.sort_index()
    if len(stats) == 1:
        return {
            "p_start": stats.index[0],
            "red_line": stats.index[0],
            "single_start": True,
        }
    else:
        return {
            "p_start": stats.index[0],
            "red_line": stats.index[1],
            "single_start": False,
        }
    

def convert_char_dataframe(container_list: List[List[LTCharNode]]):
    df = list()
    for i, container in enumerate(container_list):
        for item in container:
            df.append({
                "text": item.text,
                "fontname": item.fontname,
                "height": abs(item.coordinates.y_upper_right - item.coordinates.y_down_left),
                "width": abs(item.coordinates.x_down_left - item.coordinates.x_upper_right),
                "x_down_left": item.coordinates.x_down_left,
                "y_down_left": item.coordinates.y_down_left,
                "x_upper_right": item.coordinates.x_upper_right,
                "y_upper_right": item.coordinates.y_upper_right,
                "page_number": i + 1,
            })
    df = pd.DataFrame(df)
    return df
    

def get_tokens_dataframe(df: pd.DataFrame, atol = None):
    df_sorted = df.sort_values(["page_number", "y_down_left", "x_down_left"], ascending=[True, False, True])
    if atol is None:
        atol = df_sorted["width"].min()
    char_groups = group_chars(df_sorted, atol)
    df_n = list()
    for group in char_groups:
        item = {
            "text": "".join([x["text"] for x in group]),
            "fontname": group[0]["fontname"],
            "height": abs(group[0]["y_down_left"] - group[-1]["y_upper_right"]),
            "width": abs(group[-1]["x_upper_right"] - group[0]["x_down_left"]),
            "x_down_left": group[0]["x_down_left"],
            "y_down_left": group[0]["y_down_left"],
            "x_upper_right": group[-1]["x_upper_right"],
            "y_upper_right": group[-1]["y_upper_right"],
            "page_number": group[0]["page_number"],
        }
        df_n.append(item)
    df_n = pd.DataFrame(df_n)
    return df_n

def group_chars(df: pd.DataFrame, atol: float):
    tokens = list()
    token = list()
    previous_row = None
    for i, (_, row) in enumerate(df.iterrows()):
        if i == 0:
            token.append(row)
            previous_row = row
            continue
        if ((row["fontname"] == previous_row["fontname"])
            and np.isclose(row["x_down_left"], previous_row["x_down_left"] + previous_row["width"], atol=atol)
            and np.isclose(row["y_down_left"], previous_row["y_down_left"], atol=atol)
            and row["page_number"] == previous_row["page_number"]):
            token.append(row)
        else:
            if len(token) > 0:
                tokens.append(token)
            token = [row]
        previous_row = row
    if len(token) > 0:
        tokens.append(token)
    return tokens
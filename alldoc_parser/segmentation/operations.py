import os
import re
import json
import pandas as pd
from tqdm import tqdm
from shapely import Polygon


def merge_with_pdf_model(df: pd.DataFrame, segmentation: list):
    paragraphs = dict()
    empty_paragraphs = list()
    for i, row in tqdm(df.iterrows()):
        row_poly = Polygon([
            (row["x_down_left"], row["y_upper_right"]),
            (row["x_upper_right"], row["y_upper_right"]),
            (row["x_upper_right"], row["y_down_left"]),
            (row["x_down_left"], row["y_down_left"]),
            (row["x_down_left"], row["y_upper_right"]),
        ])
        for seg_idx, seg in enumerate(segmentation):
            if seg["page_number"] != row["page_number"]:
                continue
            lb, rb = seg["left"], seg["left"] + seg["width"]
            ub, bb = seg["page_height"] - seg["top"], seg["page_height"] - (seg["top"] + seg["height"])
            seg_poly = Polygon([(lb, ub), (rb, ub), (rb, bb), (lb, bb), (lb, ub)])
            if seg_poly.contains(row_poly):
                if i in paragraphs:
                    continue
                else:
                    paragraphs[i] = seg_idx
            elif (seg_poly.intersects(row_poly)
                and re.sub("[^A-Za-zА-Яа-я0-9]+", "", row["text"]).strip() in re.sub("[^A-Za-zА-Яа-я0-9]+", "", seg["text"])):
                if i in paragraphs:
                    continue
                else:
                    paragraphs[i] = seg_idx
        
        if i not in paragraphs:
            empty_paragraphs.append(i)

    for i in empty_paragraphs:
        paragraphs[i] = -1

    df["IDX"] = df.index
    paragraph_idx = df["IDX"].apply(lambda x: paragraphs[x])
    df["paragraph_idx"] = paragraph_idx
    df = df.drop("IDX", axis=1)
    df = df[df["paragraph_idx"] != -1]
    df["paragraph_type"] = df["paragraph_idx"].apply(lambda x: segmentation[x]["type"])

    def is_digits_only(s: str):
        return len(re.sub("[0-9]+", "", s.strip())) == 0

    def is_empty(s: str):
        return len(re.sub("[A-Za-zА-Яа-я0-9]+", "", s.strip())) == 0

    mask = (df["paragraph_type"] != "Page footer") | ~(df["text"].apply(is_digits_only) & df["text"].apply(is_empty))
    df = df.loc[mask]

    df_paragraph = list()
    for i, g in df.groupby("paragraph_idx"):
        p = g.sort_values(["y_down_left", "x_down_left"], ascending=[False, True])
        p = {
            "text": " ".join(p["text"].values),
            "fontname": p["fontname"].values[0],
        }
        df_paragraph.append(p)
    df_paragraph = pd.DataFrame(df_paragraph)

    return df_paragraph
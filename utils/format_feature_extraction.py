def is_bold(row: dict):
    return "bold" in row["fontname"].lower()

def is_italic(row: dict):
    return "italic" in row["fontname"].lower()
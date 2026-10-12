#!/usr/bin/env python3
"""Convert RuneLite ItemID.java into a Python module (standard library only)."""

import argparse
import ast
import keyword
from pathlib import Path
import re
from urllib.parse import urlparse
from urllib.request import Request, urlopen

DEFAULT_SOURCE = (
    "https://raw.githubusercontent.com/runelite/runelite/master/"
    "runelite-api/src/main/java/net/runelite/api/ItemID.java"
)


def read_source(source):
    url = urlparse(source)
    if url.scheme in {"http", "https"}:
        if url.netloc == "github.com" and "/blob/" in url.path:
            source = "https://raw.githubusercontent.com" + url.path.replace("/blob/", "/", 1)
        request = Request(source, headers={"User-Agent": "java-to-constants"})
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8-sig")
    return Path(source).read_text(encoding="utf-8-sig")


def convert(java):
    # Remove comments so commented-out declarations are never exported.
    clean = re.sub(r"/\*.*?\*/|//[^\n]*", "", java, flags=re.DOTALL)
    declarations = re.findall(
        r"\bpublic\s+static\s+final\s+int\s+([A-Za-z_$][\w$]*)\s*=\s*([^;]+);",
        clean,
    )
    if not declarations:
        raise ValueError("No public static final int constants found.")

    lines = ["# Generated from RuneLite ItemID.java."]
    # Retain the leading copyright/license notice as Python comments.
    notice = re.match(r"\s*(/\*.*?\*/)", java, flags=re.DOTALL)
    if notice:
        lines.extend("# " + line for line in notice.group(1).splitlines())
    lines.append("")
    seen = set()
    for name, expression in declarations:
        if not name.isidentifier() or keyword.iskeyword(name):
            raise ValueError(f"Invalid Python constant name: {name}")
        if name in seen:
            raise ValueError(f"Duplicate constant: {name}")
        seen.add(name)
        literal = expression.strip()
        if not re.fullmatch(r"[+-]?(?:0|[1-9][0-9_]*)", literal):
            raise ValueError(f"Unsupported integer initializer for {name}: {literal}")
        value = int(literal.replace("_", ""), 10)
        lines.append(f"{name} = {value}")
    python = "\n".join(lines) + "\n"
    ast.parse(python)  # Validate before writing the output file.
    return python, len(declarations)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=DEFAULT_SOURCE,
                        help="Java file path or URL (default: RuneLite ItemID.java)")
    parser.add_argument("-o", "--output", type=Path, default=Path("item_ids.py"))
    args = parser.parse_args()
    try:
        if urlparse(args.source).scheme not in {"http", "https"}:
            if Path(args.source).resolve() == args.output.resolve():
                raise ValueError("Input and output paths must differ.")
        python, count = convert(read_source(args.source))
        args.output.write_text(python, encoding="utf-8")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Wrote {count} constants to {args.output}")


if __name__ == "__main__":
    main()

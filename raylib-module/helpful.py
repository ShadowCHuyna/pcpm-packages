#!/usr/bin/env python3

import re
import sys
import argparse
from pathlib import Path


FUNC_PTR_PATTERN = re.compile(
    r"""
    ^\s*
    (?P<ret_type>.*?)          # return type (lazy)
    \(\s*\*\s*
    (?P<name>[A-Za-z_]\w*)     # function name
    \s*\)
    \s*
    \(
        (?P<params>[^;]*?)     # parameters
    \)
    \s*;
    """,
    re.VERBOSE | re.DOTALL,
)


def remove_comments(code: str) -> str:
    """Remove both // and /* */ comments safely."""
    # Remove block comments first
    code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)
    # Remove line comments
    code = re.sub(r"//.*", "", code)
    return code


def normalize_whitespace(s: str) -> str:
    """Collapse excessive whitespace but preserve internal structure."""
    return re.sub(r"\s+", " ", s).strip()


def extract_function_pointers(code: str):
    """
    Extract function pointer declarations from struct-like C code.
    Returns list of dicts with keys: name, type.
    """
    functions = []

    # Split by semicolon but keep semicolon
    chunks = re.split(r";", code)

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        chunk += ";"  # restore removed semicolon

        match = FUNC_PTR_PATTERN.match(chunk)
        if not match:
            continue  # ignore non-function-pointer fields

        ret_type = normalize_whitespace(match.group("ret_type"))
        name = match.group("name")
        params = normalize_whitespace(match.group("params"))

        # Reconstruct full function pointer type
        full_type = f"{ret_type} (*)({params})"

        functions.append({
            "name": name,
            "type": full_type
        })

    return functions


def generate_output(functions):
    """Generate C initialization lines."""
    lines = []
    for fn in functions:
        line = (
            f'raylib_module.{fn["name"]} = '
            f'({fn["type"]})pll_get(&raylib_lib, "{fn["name"]}");'
        )
        lines.append(line)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate pll_get bindings from C function pointer struct"
    )
    parser.add_argument("input", help="Input C header/source file")
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Error: file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    code = input_path.read_text(encoding="utf-8")

    code = remove_comments(code)

    functions = extract_function_pointers(code)

    if not functions:
        print("Warning: no function pointers found.", file=sys.stderr)

    output = generate_output(functions)

    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


if __name__ == "__main__":
    main()
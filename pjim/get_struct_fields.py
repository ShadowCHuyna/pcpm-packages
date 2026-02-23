import re
from typing import TypedDict, List, NotRequired

class StructField(TypedDict):
    typeName: str
    varName: str
    isArray: bool
    arrayCapacity: NotRequired[int]
    isStruct: bool


# минимальный, но практичный набор
BUILTIN_TYPES = {
    "char",
    "short",
    "int",
    "long",
    "float",
    "double",
    "signed",
    "unsigned",
    "bool",
    "_Bool",
}


FIELD_RE = re.compile(
    r"""
    ^\s*
    (?:
        struct\s+(?P<struct_name>[a-zA-Z_]\w*) |
        (?P<type>[a-zA-Z_]\w*)
    )
    \s+
    (?P<name>[a-zA-Z_]\w*)
    (?:
        \s*\[\s*(?P<array>\d+)\s*\]
    )?
    \s*;
    \s*$
    """,
    re.VERBOSE
)


def get_struct_fields(code: str) -> List[StructField]:
    body_start = code.find('{')
    body_end = code.rfind('}')
    if body_start == -1 or body_end == -1 or body_end <= body_start:
        raise ValueError("Invalid struct code")

    body = code[body_start + 1:body_end]

    fields: List[StructField] = []

    for lineno, line in enumerate(body.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue

        if '*' in line:
            raise ValueError(f"Pointer detected in struct field at line {lineno}: {line}")

        m = FIELD_RE.match(line)
        if not m:
            raise ValueError(f"Unsupported field declaration at line {lineno}: {line}")

        struct_name = m.group("struct_name")
        type_name = struct_name or m.group("type")
        var_name = m.group("name")
        array_cap = m.group("array")

        is_struct = (
            struct_name is not None or
            type_name not in BUILTIN_TYPES
        )

        field: StructField = {
            "typeName": type_name,
            "varName": var_name,
            "isArray": array_cap is not None,
            "isStruct": is_struct,
        }

        if array_cap is not None:
            field["arrayCapacity"] = int(array_cap)

        fields.append(field)

    return fields
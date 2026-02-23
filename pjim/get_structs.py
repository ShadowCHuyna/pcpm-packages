import re
from typing import TypedDict, List

# @TODO добавить полу structName (если есть для генерации в pjim.c имен)
class StructInfo(TypedDict):
    code: str
    startI: int
    endI: int
    useTypedef: bool
    name: str  # имя структуры, учитывая typedef
    


MARKER_RE = re.compile(r'//\s*@PJIM')
STRUCT_START_RE = re.compile(
    r'(typedef\s+)?struct(\s+\w+)?\s*\{',
    re.MULTILINE
)


def _find_matching_brace(code: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(code):
        if code[i] == '{':
            depth += 1
        elif code[i] == '}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    raise ValueError("Unbalanced braces")


def get_structs(code: str) -> List[StructInfo]:
    result: List[StructInfo] = []

    for marker in MARKER_RE.finditer(code):
        search_from = marker.end()
        m = STRUCT_START_RE.search(code, search_from)
        if not m:
            continue

        struct_start = m.start()
        use_typedef = m.group(1) is not None

        brace_open = code.find('{', m.end() - 1)
        brace_close = _find_matching_brace(code, brace_open)

        semi = code.find(';', brace_close)
        if semi == -1:
            continue

        end = semi + 1
        struct_code = code[struct_start:end]

        # вычисляем имя
        if use_typedef:
            # берём всё после '}' до ';'
            name = code[brace_close + 1:semi].strip()
        else:
            # struct X { ... }; — берём имя после struct
            struct_header = code[struct_start:brace_open].strip()
            name = struct_header.split()[-1]

        result.append({
            "code": struct_code,
            "startI": struct_start,
            "endI": end,
            "useTypedef": use_typedef,
            "name": name,
        })

    return result

from typing import List
from .get_struct_fields import StructField
from .get_structs import StructInfo

INTEGER_TYPES = {
    "char",
    "short",
    "int",
    "long",
    "longlong",
    "signed",
    "unsigned",
}

FLOAT_TYPES = {
    "float",
    "double",
}

BOOL_TYPES = {
    "bool",
    "_Bool",
}

def _is_char_array_string(field: StructField) -> bool:
    return (
        field["typeName"] == "char"
        and field["isArray"]
    )

def _emit_scalar(field: StructField, access: str) -> str:
    t = field["typeName"]

    if t in BOOL_TYPES:
        return f"jim_bool(jim, {access});"

    if t in INTEGER_TYPES:
        return f"jim_integer(jim, (long long){access});"

    if t in FLOAT_TYPES:
        return f"jim_float(jim, (double){access}, 6);"

    # структура
    return f"pjim_{t}_serialization(jim, &{access});"


def generate_serialization_fn(
    struct_info: StructInfo,
    fields: List[StructField],
) -> str:
    type_name = struct_info['name']
    fn_name = f"pjim_{type_name}_serialization"

    lines: list[str] = []

    lines.append(f"void {fn_name}(Jim* jim, void* v_data)")        
    lines.append("{")
    
    lines.append(f"    {type_name}* data = ({type_name}*)v_data;")

    lines.append("    jim_object_begin(jim);")

    field_names = {f["varName"] for f in fields}

    for f in fields:
        name = f["varName"]
        lines.append(f'    jim_member_key(jim, "{name}");')

        # ===== char[N] → string =====
        if f["typeName"] == "char" and f["isArray"]:
            lines.append(f"    jim_string(jim, data->{name});")
            continue
        # ============================

        if f["isArray"]:
            cap_name = f"{name}_capacity"
            cap_expr = (
                f"data->{cap_name}"
                if cap_name in field_names
                else str(f["arrayCapacity"])
            )

            lines.append("    jim_array_begin(jim);")
            lines.append(f"    for (size_t i = 0; i < {cap_expr}; ++i) {{")

            access = f"data->{name}[i]"

            if f["isStruct"]:
                lines.append(
                    f"        pjim_{f['typeName']}_serialization(jim, &{access});"
                )
            else:
                lines.append(f"        {_emit_scalar(f, access)}")

            lines.append("    }")
            lines.append("    jim_array_end(jim);")
        else:
            access = f"data->{name}"
            lines.append(f"    {_emit_scalar(f, access)}")

    lines.append("    jim_object_end(jim);")
    lines.append("}")

    return "\n".join(lines)


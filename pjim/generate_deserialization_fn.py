from .get_struct_fields import StructField
from .get_structs import StructInfo

def generate_deserialization_fn(struct_info: StructInfo, fields: list[StructField]) -> str:
    """
    Генерирует C функцию десериализации для структуры с использованием Jimp.
    """
    type_name = struct_info["name"]
    fn_name = f"pjim_{type_name}_deserialization"

    lines = []
    lines.append(f"bool {fn_name}(Jimp *jimp, void* v_data)")
    
    lines.append("{")
    lines.append(f"    {type_name}* data = ({type_name}*)v_data;")

    lines.append("    if (!jimp_object_begin(jimp)) return false;")
    lines.append("    while (jimp_object_member(jimp)) {")
    
    field_names = {f['varName'] for f in fields}

    for i, f in enumerate(fields):
        ef = "} else " if i > 0 else ""

        name = f["varName"]
        lines.append(f'        {ef}if (strcmp(jimp->string, "{name}") == 0) {{')

        # ===== char[] как строки =====
        if f["typeName"] == "char" and f["isArray"]:
            lines.append("            if (!jimp_string(jimp)) return false;")
            lines.append(f"            strcpy(data->{name}, jimp->string);")
        
        # ===== числовые типы =====
        elif not f["isStruct"] and not f["isArray"]:
            t = f["typeName"]
            if t in {"float", "double"}:
                lines.append("            if (!jimp_number(jimp)) return false;")
                lines.append(f"            data->{name} = jimp->number;")
            else:
                lines.append("            if (!jimp_number(jimp)) return false;")
                lines.append(f"            data->{name} = (long long)jimp->number;")

        # ===== массивы простых типов =====
        elif not f["isStruct"] and f["isArray"]:
            cap_name = f"{name}_capacity"
            # cap_expr = cap_name if cap_name in field_names else str(f.get("arrayCapacity", 0))
            lines.append("            if (!jimp_array_begin(jimp)) return false;")
            lines.append(f"            for (size_t i = 0; jimp_array_item(jimp); ++i) {{")
            t = f["typeName"]
            if t in {"float", "double"}:
                lines.append("                if (!jimp_number(jimp)) return false;")
                lines.append(f"                data->{name}[i] = jimp->number;")
            else:
                lines.append("                if (!jimp_number(jimp)) return false;")
                lines.append(f"                data->{name}[i] = (long long)jimp->number;")
            lines.append("            }")
            lines.append("            if (!jimp_array_end(jimp)) return false;")

        # ===== структура =====
        elif f["isStruct"] and not f["isArray"]:
            lines.append(f"            if (!pjim_{f['typeName']}_deserialization(jimp, &data->{name})) return false;")

        # ===== массив структур =====
        elif f["isStruct"] and f["isArray"]:
            cap_name = f"{name}_capacity"
            # cap_expr = cap_name if cap_name in field_names else str(f.get("arrayCapacity", 0))
            lines.append("            if (!jimp_array_begin(jimp)) return false;")
            lines.append(f"            for (size_t i = 0; jimp_array_item(jimp); ++i) {{")
            lines.append(f"                if (!pjim_{f['typeName']}_deserialization(jimp, &data->{name}[i])) return false;")
            lines.append("            }")
            lines.append("            if (!jimp_array_end(jimp)) return false;")

    lines.append("        } else {")
    lines.append("            jimp_unknown_member(jimp);")
    lines.append("            return false;")
    lines.append("        }")
    
    lines.append("    }")
    lines.append("    return jimp_object_end(jimp);")
    lines.append("}")

    return "\n".join(lines)

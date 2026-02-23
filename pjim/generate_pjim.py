from .get_structs import StructInfo
from .get_struct_fields import get_struct_fields
from .generate_serialization_fn import generate_serialization_fn
from .generate_deserialization_fn import generate_deserialization_fn

def generate_pjimh(all_struct_info: list[StructInfo]) -> str:
    code = "#ifndef PJIM_H_\n#define PJIM_H_\n#include <stdbool.h>\n"
    code += "#include \"jim.h\"\n#include \"jimp.h\"\n"

    for si in all_struct_info:
        code += f"void pjim_{si['name']}_serialization(Jim* jim, void* v_data);\n"
        code += f"bool pjim_{si['name']}_deserialization(Jimp *jimp, void* v_data);\n"
        
    code += "#endif\n"

    return code


def generate_pjimc(all_struct_info: list[StructInfo]) -> str:
    code = "#include <string.h>\n#include \"jim.h\"\n#include \"jimp.h\"\n#include \"pjim.h\"\n"

    for si in all_struct_info:
        code += f"typedef struct {si["name"]} {si["name"]};\n"
    
    for si in all_struct_info:
        code += f"struct {si["name"]} {{\n"
        for f in get_struct_fields(si["code"]):
            code += f"\t{f["typeName"]} {f["varName"]}"
            if f["isArray"]:
                code += f"[{f['arrayCapacity']}]"
            code += ";\n"
        code += "};\n"
        
    for si in all_struct_info:
        f = get_struct_fields(si["code"])
        code += generate_serialization_fn(si, f)
        code += "\n"
        code += generate_deserialization_fn(si, f)

    return code
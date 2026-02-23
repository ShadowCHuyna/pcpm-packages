from pathlib import Path
import os
import json
import subprocess

from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, build_sf_libs, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] stb: %(message)s")

defines: list[str] =[
            "STB_C_LEXER_IMPLEMENTATION",
            "STB_DS_IMPLEMENTATION",
            "STB_HERRINGBONE_WANG_TILE_IMPLEMENTATION",
            "STB_IMAGE_RESIZE2_IMPLEMENTATION",
            "STB_LEAKCHECK_IMPLEMENTATION",
            "STB_SPRINTF_IMPLEMENTATION",
            "STB_TRUETYPE_IMPLEMENTATION",
            "STB_CONNECTED_COMPONENTS_IMPLEMENTATION",
            "STB_DXT_IMPLEMENTATION",
            "STB_HEXWAVE_IMPLEMENTATION",
            "STB_IMAGE_WRITE_IMPLEMENTATION",
            "STB_PERLIN_IMPLEMENTATION",
            "STB_TEXTEDIT_IMPLEMENTATION",
            "STB_VOXEL_RENDER_IMPLEMENTATION",
            "STB_DIVIDE_IMPLEMENTATION",
            "STB_EASY_FONT_IMPLEMENTATION",
            "STB_IMAGE_IMPLEMENTATION",
            "STB_INCLUDE_IMPLEMENTATION",
            "STB_RECT_PACK_IMPLEMENTATION",
            "STB_TILEMAP_EDITOR_IMPLEMENTATION",
        ]

def init(root: Path, pkg: Path) -> dict|None:
    if build_sf_libs(list((pkg/"include").rglob("*.[h]")), defines) is None: return None

    add_includes_in_c_cpp_properties(root, "stb")
    logger.info(f"init")
    logger.warning("НЕ ИСПОЛЬЗУЙТЕ `#define STB_*_IMPLEMENTATION` мы все сделали за вас!")

    return {"implement": [i.stem for i in list((pkg/"include").rglob("*.[h]"))]}

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_objs: list[Path]|None = build_sf_libs(list((pkg/"include").rglob("*.[h]")), defines)
    if lib_objs is None: return None

    implement_list: list[str] = args.get("implement", [])
    objs: list[str] = []
    for o in lib_objs:
        if o.stem in implement_list:
            objs.append(str(o)) 



    ba: BuildArgs = {
        "source": [
            f"-I{pkg/"include"}",
        ],
        "link": ["-lm"],
        "objs": objs
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "stb")
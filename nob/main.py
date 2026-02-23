from pathlib import Path

from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, build_sf_libs, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] nob: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    if build_sf_libs([pkg/"include"/"nob.h"], ["NOB_IMPLEMENTATION"]) is None: return None

    add_includes_in_c_cpp_properties(root, "nob")
    logger.info(f"init")
    logger.warning("НЕ ИСПОЛЬЗУЙТЕ `#define NOB_IMPLEMENTATION` мы все сделали за вас!")
    return {"implement": ["nob"]}

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_objs = build_sf_libs([pkg/"include"/"nob.h"], ["NOB_IMPLEMENTATION"])
    if lib_objs is None: return None
    lib_objs =  [str(o) for o in lib_objs]

    implement_list: list[str] = args.get("implement", [])
    if not "nob" in implement_list:  lib_objs = []

    ba: BuildArgs = {
        "source": [
            f"-I{pkg/"include"}",
        ],
        "link": [],
        "objs": lib_objs
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "nob")
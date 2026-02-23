from pathlib import Path
from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, build_sf_libs, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] arena: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    if build_sf_libs([pkg/"include"/"arena.h"], ["ARENA_IMPLEMENTATION"]) is None: return None

    add_includes_in_c_cpp_properties(root, "arena")
    logger.info(f"init")
    logger.warning("НЕ ИСПОЛЬЗУЙТЕ `#define ARENA_IMPLEMENTATION` мы все сделали за вас!")
    return {"implement": ["arena"]}

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_objs = build_sf_libs([pkg/"include"/"arena.h"], ["ARENA_IMPLEMENTATION"])
    if lib_objs is None: return None
    # lib_objs =  [str(o) for o in lib_objs]
    implement_list: list[str] = args.get("implement", [])
    objs: list[str] = []
    for o in lib_objs:
        if o.stem in implement_list:
            objs.append(str(o)) 

    ba: BuildArgs = {
        "source": [
            f"-I{str(pkg/"include")}",
        ],
        "link": [],
        "objs": objs
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "arena")
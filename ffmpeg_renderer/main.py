from pathlib import Path

from pcpm.utils import add_includes_in_c_cpp_properties, build_sf_libs, change_loger_format, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] ffmpeg_renderer: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    if build_sf_libs([pkg/"include"/"ffmpeg_renderer.h"], ["FFMPEG_IMPLEMENTATION"]) is None: return None

    add_includes_in_c_cpp_properties(root, "ffmpeg_renderer")
    logger.info(f"init")
    return {"implement": ["ffmpeg_renderer"]}


def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_objs = build_sf_libs([pkg/"include"/"ffmpeg_renderer.h"], ["FFMPEG_IMPLEMENTATION"])
    if lib_objs is None: return None
    # lib_objs =  [str(o) for o in lib_objs]
    implement_list: list[str] = args.get("implement", [])
    objs: list[str] = []
    for o in lib_objs:
        if o.stem in implement_list:
            objs.append(str(o)) 
    
    ba: BuildArgs = {
        "source": [
            f"-I{pkg/'include'}",
        ],
        "link": [],
        "objs": objs
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "ffmpeg_renderer")
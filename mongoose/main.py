from pathlib import Path

from pcpm.utils import add_includes_in_c_cpp_properties, get_platform, remove_includes_in_c_cpp_properties, change_loger_format, compile
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] mongoose: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    if compile([pkg/"mongoose.c"], [pkg/"mongoose.o"], [f"-I{pkg/'include'}"]) is None: return None

    add_includes_in_c_cpp_properties(root, "mongoose")
    logger.info(f"init")

    return {}

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_objs: list[str] = []
    if not (pkg/"mongoose.o").exists():
        objs = compile([pkg/"mongoose.c"], [pkg/"mongoose.o"], [f"-I{pkg/'include'}"])    
        if objs is None: return None
        lib_objs = [str(o) for o in objs]
    else:
        lib_objs = [str(pkg/"mongoose.o")]
                        
    ba: BuildArgs = {
        "source": [
            f"-I{pkg/'include'}",
        ],
        "link": [],
        "objs": lib_objs
    }
    if get_platform() == "windows":
        ba["link"]+=[
            "-lws2_32"
        ]
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "mongoose")
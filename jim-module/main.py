from pathlib import Path
import shutil
import os
from types import ModuleType

from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, build_sf_libs, remove_includes_in_c_cpp_properties, get_lib, load_config, get_module, get_pkg_args
from pcpm.ds import BuildArgs, Config, BIN_PATH, TMP_SRC_PATH, PKGS_PATH

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] jim-module: %(message)s")

def get_jim_lib_map(pkg: Path)->dict:
    return {
        "dynamic": {
            "x86_64": {
                "windows": f"{pkg}/lib/windows_x86_64/jim.dll"
            }
        }
    }

def get_pll_source() -> list[str]|None:
    module: ModuleType|None = get_module("pll")
    args: dict|None = get_pkg_args("pll")
    if module is None or args is None: return None
    if module.build is None: return None
    ba: BuildArgs|None = module.build(TMP_SRC_PATH, PKGS_PATH/"pll", args)
    if ba is None: return None
    return ba["source"]

def init(root: Path, pkg: Path) -> dict|None:
    # pll_source = get_pll_source()
    # if pll_source is None: 
    #     logger.error("pll_source is None")
    #     return None
    # if build_sf_libs([pkg/"include"/"jim-module.h"], ["JIM_MODULE_IMPLEMENTATION"], pll_source) is None: return None
    
    add_includes_in_c_cpp_properties(root, "jim-module")
    logger.info(f"init")
    logger.warning("НЕ ИСПОЛЬЗУЙТЕ `#define JIM_MODULE_IMPLEMENTATION` мы все сделали за вас!")

    return {"implement": [ "jim-module" ]}


def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    pll_source = get_pll_source()
    if pll_source is None: return None
    if pll_source is None: 
        logger.error("pll_source is None")
        return None
    lib_objs: list[Path]|None = build_sf_libs([pkg/"include"/"jim-module.h"], ["JIM_MODULE_IMPLEMENTATION"], pll_source)
    if lib_objs is None: return None

    implement_list: list[str] = args.get("implement", [])
    objs = []
    for o in lib_objs:
        if o.stem in implement_list:
            objs.append(str(o)) 

    config: Config|None = load_config()
    if config is None: return None
    origin: Path = BIN_PATH
    if "origin" in config: origin = BIN_PATH/config["origin"]
    os.makedirs(origin, exist_ok=True)

    path_to_lib, lib_name = get_lib(get_jim_lib_map(pkg), "dynamic")
    if path_to_lib is None or lib_name is None: return None 
    shutil.copy(path_to_lib/lib_name, origin/lib_name)
    
    
    ba: BuildArgs = {
        "source": [
            f"-I{pkg/'include'}",
        ],
        "link": [],
        "objs": objs
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "jim-module")
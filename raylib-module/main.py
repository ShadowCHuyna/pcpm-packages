from pathlib import Path
import os
import shutil
from types import ModuleType

from pcpm.utils import get_module, get_pkg_args, get_platform, add_includes_in_c_cpp_properties, create_lib_symlink, get_lib, check_lib, get_platform, change_loger_format, load_config, remove_includes_in_c_cpp_properties
from pcpm.ds import PKGS_PATH, TMP_SRC_PATH, BuildArgs, Config, BIN_PATH
from .utils import build_sf_libs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] raylib-module: %(message)s")


def get_lib_map(pkg: Path)->dict:
    return {
        "dynamic": {
            "x86_64": {
                "windows": f"{pkg}/lib/windows_x86_64/raylib.dll",
                "linux": f"{pkg}/lib/linux_x86_64/libraylib.so.5.5.0",
                "darwin": f"{pkg}/lib/darwin_x86_64/libraylib.5.5.0.dylib"
            }
        }
    }

def init(root: Path, pkg: Path) -> dict|None:
    if not check_lib(get_lib_map(pkg)):
        logger.error("пакет не работает на вашем кале идите нахуй")
        return None
    
    add_includes_in_c_cpp_properties(root, "raylib-module")
    logger.info(f"init")

    return {"implement": [ "raylib-module" ]}
        
def get_pll_source() -> list[str]|None:
    module: ModuleType|None = get_module("pll")
    args: dict|None = get_pkg_args("pll")
    if module is None or args is None: return None
    if module.build is None: return None
    ba: BuildArgs|None = module.build(TMP_SRC_PATH, PKGS_PATH/"pll", args)
    if ba is None: return None
    return ba["source"]

def build(src: Path, pkg: Path, args: dict) -> BuildArgs|None:
    pll_source = get_pll_source()
    if pll_source is None: return None
    if pll_source is None: 
        logger.error("pll_source is None")
        return None
    
    lib_objs: list[Path]|None = build_sf_libs([pkg/"include"/"raylib-module.h"], ["RAYLIB_MODULE_IMPLEMENTATION"], pll_source)
    if lib_objs is None: return None

    config: Config|None = load_config()
    if config is None: return None
    origin: Path = BIN_PATH
    if "origin" in config: origin = BIN_PATH/config["origin"]
    os.makedirs(origin, exist_ok=True)
    
    path_to_lib, lib_name = get_lib(get_lib_map(pkg), "dynamic")
    if path_to_lib is None or lib_name is None:
        logger.error("path_to_lib, lib_name не определины ОШИБКА СБОРКИ raylib")
        return None
    shutil.copy(path_to_lib/lib_name, origin/lib_name)
    

    implement_list: list[str] = args.get("implement", [])
    objs = []
    for o in lib_objs:
        if o.stem in implement_list:
            objs.append(str(o)) 

    ba: BuildArgs = {
        "source": [
            f"-I{pkg/'include'}"
        ],
        "link": [
            "-lm"
        ],
        "objs": objs
    }
    if get_platform() == "windows":
        ba["link"]+=[
            "-lgdi32", 
            "-lopengl32", 
            "-lwinmm"
        ]

    return ba

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "raylib")
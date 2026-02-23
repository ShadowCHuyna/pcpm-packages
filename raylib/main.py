from pathlib import Path
import os
import shutil

from pcpm.utils import get_platform, add_includes_in_c_cpp_properties, create_lib_symlink, get_lib, check_lib, get_platform, change_loger_format, load_config, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs, Config, BIN_PATH

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] raylib: %(message)s")


def get_lib_map(pkg: Path)->dict:
    return {
        "static": {
            "x86": {
                "windows": f"{pkg}/lib/windows_x86/libraylib.a",
                "linux": f"{pkg}/lib/linux_x86/libraylib.a"
            },
            "x86_64": {
                "windows": f"{pkg}/lib/windows_x86_64/libraylib.a",
                "linux": f"{pkg}/lib/linux_x86_64/libraylib.a",
                "darwin": f"{pkg}/lib/darwin_x86_64/libraylib.a"
            }
        },
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
    
    add_includes_in_c_cpp_properties(root, "raylib")
    logger.info(f"init")

    return {
        "link": "static"
    }
        
def build(src: Path, pkg: Path, args: dict) -> BuildArgs|None:
    link_type = args.get("link") or "static"

    path_to_lib, lib_name = get_lib(get_lib_map(pkg), link_type)
    if path_to_lib is None or lib_name is None:
        logger.error("path_to_lib, lib_name не определины ОШИБКА СБОРКИ raylib")
        return None
    
    config: Config|None = load_config()
    if config is None: return None
    if "origin" in config and args["link"] == "dynamic":
        os.makedirs(BIN_PATH/config["origin"], exist_ok=True)
        # logger.info(f"src: {path_to_lib/lib_name} dst: {BIN_PATH/config["origin"]/lib_name}")
        shutil.copy(path_to_lib/lib_name, BIN_PATH/config["origin"]/lib_name)

        if get_platform() == "linux":
            create_lib_symlink("libraylib.so", "libraylib.so.550")


    ba: BuildArgs = {
        "source": [
            f"-I{pkg/"include"}",
            f"-L{path_to_lib}"
        ],
        "link": [
            f"-l:{lib_name}",
            "-lm"
        ],
        "objs": []
    }
    if get_platform() == "windows":
        ba["link"]+=[
            "-lraylib", 
            "-lgdi32", 
            "-lopengl32", 
            "-lwinmm"
        ]

    return ba

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "raylib")
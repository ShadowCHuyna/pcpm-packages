from pathlib import Path
import os
import shutil

from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, load_config, remove_includes_in_c_cpp_properties, create_lib_symlink
from pcpm.ds import BuildArgs, Config, BIN_PATH

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] ffi: %(message)s")


def init(root: Path, pkg: Path) -> dict|None:
    add_includes_in_c_cpp_properties(root, "ffi")
    logger.info(f"init")
    return {"link": "static"}


def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_name = ""
    if not "link" in args: return None
    if args["link"] == "static":
        lib_name = "libffi.a"
    else:
        lib_name = "libffi.so.8.2.0"

    config: Config|None = load_config()
    if config is None: return None
    if "origin" in config and args["link"] == "dynamic":
        os.makedirs(BIN_PATH/config["origin"], exist_ok=True)
        shutil.copy(pkg/"lib"/lib_name, BIN_PATH/config["origin"]/lib_name)

        create_lib_symlink("libffi.so.8.2.0", "libffi.so.8")
        create_lib_symlink("libffi.so.8.2.0", "libffi.so")
        

    ba: BuildArgs = {
        "source": [
            f"-I{str(pkg/"include")}",
            f"-L{str(pkg/"lib")}",
        ],
        "link": [
            f"-l:{lib_name}"
        ],
        "objs": []
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "ffi")
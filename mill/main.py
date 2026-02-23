# https://github.com/sustrik/libmill
from pathlib import Path
import os
import shutil

from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, load_config, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs, Config, BIN_PATH

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] mill: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    add_includes_in_c_cpp_properties(root, "mill")
    logger.info("init")
    return {"link": "static"}


def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    lib_name = ""
    if not "link" in args: return None
    if args["link"] == "static":
        lib_name = "libmill.a"
    else:
        lib_name = "libmill.so"

    config: Config|None = load_config()
    if config is None: return None
    if "origin" in config and args["link"] == "dynamic":
        os.makedirs(BIN_PATH/config["origin"], exist_ok=True)
        shutil.copy(pkg/"lib"/lib_name, BIN_PATH/config["origin"]/lib_name)

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
    remove_includes_in_c_cpp_properties(root, "mill")
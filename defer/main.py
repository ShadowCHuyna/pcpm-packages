from pathlib import Path
from pcpm.utils import add_includes_in_c_cpp_properties, change_loger_format, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] defer: %(message)s")


def init(root: Path, pkg: Path) -> dict|None:
    add_includes_in_c_cpp_properties(root, "defer")
    logger.info(f"init")
    return {}

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    ba: BuildArgs = {
        "source": [
            f"-I{str(pkg/'include')}",
        ],
        "link": [],
        "objs": []
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "defer")
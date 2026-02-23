from pathlib import Path
import subprocess
from types import ModuleType
import os

from pcpm.utils import change_loger_format, get_compiler, get_module, get_pkg_args, add_includes_in_c_cpp_properties, remove_includes_in_c_cpp_properties
from pcpm.ds import BuildArgs, PKGS_PATH, TMP_SRC_PATH

from .get_structs import get_structs, StructInfo
from .generate_pjim import generate_pjimh, generate_pjimc

import logging

logger = logging.getLogger(__name__)
change_loger_format(logger, "[%(levelname)s] pjim: %(message)s")

def init(root: Path, pkg: Path) -> dict|None:
    add_includes_in_c_cpp_properties(root, "pjim")
    logger.info(f"init")
    return {}

def generate(src: Path, pkg: Path) -> bool:
    c_files: list[Path] = list(src.rglob("*.[ch]"))
    struct_infos: list[StructInfo] = []

    try:
        for f in c_files:
            with open(f) as fd:
                struct_infos += get_structs(fd.read())
    except:
        logger.error("ошибка при поиске структур")
        return False
    try:
        os.makedirs(pkg/"include", exist_ok=True) 
        with open(pkg/"include"/"pjim.h", "+w") as fd:
            fd.write(generate_pjimh(struct_infos))
    except:
        logger.error("ошибка при генерации `pjim.h`")
        return False
    
    try:
        with open(pkg/"pjim.c", "+w") as fd:
            fd.write(generate_pjimc(struct_infos))
    except:
        logger.error("ошибка при генерации `pjim.c`")
        return False
    
    return True

def get_jim_source() -> list[str]|None:
    module: ModuleType|None = get_module("jim")
    args: dict|None = get_pkg_args("jim")
    if module is None or args is None: return None
    if module.build is None: return None
    ba: BuildArgs|None = module.build(TMP_SRC_PATH, PKGS_PATH/"jim", args)
    if ba is None: return None
    return ba["source"]

def compile(pkg: Path) -> str|None:
    cc: str|None = get_compiler()
    if cc is None: return None
    
    jim_source: list[str]|None = get_jim_source()
    if jim_source is None: return

    cmd = [cc, "-c", str(pkg/"pjim.c"), "-o", str(pkg/"pjim.o"), f"-I{pkg/'include'}"] + jim_source
    try:
        subprocess.run(cmd, text=True)
    except:
        logger.error("ошибка при сборки `pjim.c`")
        return None
    
    return str(PKGS_PATH/"pjim"/"pjim.o")

def build(root: Path, pkg: Path, args: dict) -> BuildArgs|None:
    if not generate(root, pkg): return None
    obj: str|None = compile(pkg)
    if obj is None: return None

    ba: BuildArgs = {
        "source": [f"-I{pkg/'include'}"],
        "link": [],
        "objs": [obj]
    }
    return ba 

def remove(root: Path, pkg: Path, args: dict):
    remove_includes_in_c_cpp_properties(root, "pjim")
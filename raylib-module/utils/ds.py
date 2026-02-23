from typing import TypedDict, Required, NotRequired
from pathlib import Path
from typing import Callable

PKGS_MIRROR = "http://pcpmirror.potatom.ru/packages"

PKGS_PATH = Path("./pkgs") 
ROOT_PATH = Path(".")

SRC_PATH = Path("./src")

BUILD_PATH = Path("./build")
TMP_SRC_PATH = Path(BUILD_PATH/"tmp_src")
OBJS_PATH = Path(BUILD_PATH/"objs")
BIN_PATH = Path(BUILD_PATH/"bin")

BUILD_PATHS = [BUILD_PATH, TMP_SRC_PATH, OBJS_PATH, BIN_PATH]

COMPILE_ARGS = ["-Wall", "-Wextra"]
COMPILERS = ["cc", "gcc", "clang", "mingw", "cl"]

class BuildArgs(TypedDict):
    source: list[str]
    link: list[str]
    objs: list[str]

class Config(TypedDict):
    name: Required[str]
    target_name: Required[str]
    origin: NotRequired[str]                    
    compilation_args: NotRequired[list[str]]    
    compiler: NotRequired[str]                  
    linking_args: NotRequired[list[str]]        
    linker: NotRequired[str]                    
    dependencies: NotRequired[dict]
    workers: NotRequired[int]
    mirrors: NotRequired[list[str]]
    assets: NotRequired[list[str]]

class PackageConfig(TypedDict):
    name: str
    dependencies: NotRequired[dict]


InitFuncType = Callable[[Path, Path], dict|None]
BuildFuncType = Callable[[Path, Path, dict], BuildArgs|None]
RemoveFuncType = Callable[[Path, Path, dict|None], None]
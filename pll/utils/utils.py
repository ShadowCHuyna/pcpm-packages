from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import logging
from types import ModuleType
import urllib.request
import urllib.error
import tarfile
import sys
import importlib
import importlib.util
import platform
import json
import os
import shutil
import subprocess

from .ds import COMPILERS, Config, PKGS_PATH, ROOT_PATH, PackageConfig, BIN_PATH

logger = logging.getLogger(__name__)

def get_answer(msg: str) -> bool:
    answer = input(msg+" [y/n, д/н]: ").strip().lower()
    return answer in ('y', 'yes', 'д', 'да')

def download(url: str, dest: str|Path) -> bool:
    try:
        Path(dest).parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, str(dest))
        return True
    except (urllib.error.URLError, OSError) as e:
        # logger.error(f"ошибка при скачивание url: {str(url)}, dest: {str(dest)}: {e}")
        return False
    
def untar(src: Path|str, dest: Path|str):
    with tarfile.open(src, "r:gz") as tar:
        tar.extractall(path=dest, filter="fully_trusted")

def get_module(p: str) -> ModuleType|None:
    try:
        PKG_DIR = PKGS_PATH / p

        pkg_spec = importlib.util.spec_from_file_location(
            name=p,
            location=PKG_DIR / "__init__.py",
            submodule_search_locations=[str(PKG_DIR)]
        )
        if pkg_spec is None: raise Exception("pkg_spec is None")
        if pkg_spec.loader is None: raise Exception("pkg_spec.loader is None")

        pkg: ModuleType = importlib.util.module_from_spec(pkg_spec)
        sys.modules[p] = pkg
        pkg_spec.loader.exec_module(pkg)

        main_spec = importlib.util.spec_from_file_location(
            name=f"{p}.main",
            location=PKG_DIR / "main.py"
        )
        if main_spec is None: raise Exception("main_spec is None")
        if main_spec.loader is None: raise Exception("main_spec.loader is None")

        main_mod = importlib.util.module_from_spec(main_spec)
        sys.modules[f"{p}.main"] = main_mod
        main_spec.loader.exec_module(main_mod)

        return main_mod
    except Exception as e:
        logger.error(f"Ошибка загрузки модуля!: {e}")
        return None
    
def get_arch() -> str:
    arch = platform.machine().lower()
    arch_map = {
        'amd64': 'x86_64',
        'x86_64': 'x86_64',
        'i386': 'x86',
        'i686': 'x86',
        'armv7l': 'arm',
        'aarch64': 'arm64',
    }
    return arch_map.get(arch, arch)

def get_platform() -> str:
    system = platform.system().lower()
    platform_map = {
        'linux': 'linux',
        'darwin': 'darwin',
        'windows': 'windows'
    }
    return platform_map.get(system, system)

def get_bin_suffix() -> str:
    return ".exe" if get_platform() == "windows" else ""

def check_config(root: Path = Path(".")) -> bool:
    if not os.path.exists(root/"config.json"):
        logger.error(f"'{root/"config.json"}' не найден!")
        return False
    return True
    
def load_config(root: Path = Path(".")) -> Config|None:
    if not check_config(root):
        return None
    
    with open(root/"config.json") as fd:
        return json.loads(fd.read()) 

def write_config(config: Config, pth: Path = ROOT_PATH/"config.json"):
    with open(pth, "+w") as fd:
        fd.write(json.dumps(config, indent=4))

def check_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def get_compiler() -> str|None:
    config: Config|None = load_config()
    if not config is None and "compiler" in config:
        return config["compiler"]
    for cc in COMPILERS:
        if check_cmd(cc): return cc
    logger.error(f"не нашел компилятор! список доступных: {COMPILERS}")
    return None

def get_linker() -> str|None:
    config: Config|None = load_config()
    if not config is None and "linker" in config:
        return config["linker"]
    for cc in COMPILERS:
        if check_cmd(cc): return cc
    logger.error(f"не нашел компилятор! список доступных: {COMPILERS}")
    return None

def get_lib(lib_map: dict, link_type: str) -> tuple[Path, str]|tuple[None, None]:
    """
    lib_map_example = {
        "static": {
            "x86": {
                "windows": "/pth/to/lib.a",
                "linux": "/pth/to/lib.a"
            },
            "x86_64": {
                "windows": "/pth/to/lib.a",
                "linux": "/pth/to/lib.a",
                "darwin": "/pth/to/lib.a"
            }
        },
        "dynamic": {
            "x86_64": {
                "windows": "/pth/to/lib.dll",
                "linux": "/pth/to/lib.so",
                "darwin": "/pth/to/lib.dylib"
            }
        }
    }
    link_type: str - `static`|`dynamic`

    return (pth_to_lib: Path, lib_name: str)
    """
    current_arch = get_arch()
    current_platform = get_platform()

    if (
        lib_map.get(link_type) is None or 
        lib_map[link_type].get(current_arch) is None or 
        lib_map[link_type][current_arch].get(current_platform) is None
    ): 
        return (None,None)
    
    arch_data = lib_map[link_type]
    platform_path = arch_data[current_arch][current_platform]
    
    path = Path(platform_path).parent
    lib_name = Path(platform_path).name
    
    return path, lib_name

def check_lib(lib_map: dict) -> bool:
    current_arch = get_arch()
    current_platform = get_platform()

    for link_type in ['static', 'dynamic']:
        if (
            link_type in lib_map and
            current_arch in lib_map[link_type] and
            current_platform in lib_map[link_type][current_arch]
        ):
            return True
    return False

def add_includes_in_c_cpp_properties(root: Path, pkg_name: str):
    vscode_dir = root / ".vscode"
    config_path = vscode_dir / "c_cpp_properties.json"
    
    vscode_dir.mkdir(exist_ok=True)
    
    default_config = {
        "includePath": [
            "${default}",
            "${workspaceFolder}/src",
            f"${{workspaceFolder}}/pkgs/{pkg_name}/include"
        ]
    }

    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
    else:
        data = {"configurations": []}

    if "configurations" not in data:
        data["configurations"] = []

    include_path = f"${{workspaceFolder}}/pkgs/{pkg_name}/include"
    path_exists = False
    
    for config in data["configurations"]:
        if "includePath" in config:
            if include_path in config["includePath"]:
                path_exists = True
                break
            else:
                config["includePath"].append(include_path)
                path_exists = True
                

    if not path_exists:
        data["configurations"].append(default_config)

    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)

def remove_includes_in_c_cpp_properties(root: Path, pkg_name: str):
    vscode_dir = root / ".vscode"
    config_path = vscode_dir / "c_cpp_properties.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            data = json.load(f)
    else:
        return
    
    if "configurations" not in data: return

    include_path = f"${{workspaceFolder}}/pkgs/{pkg_name}/include"
    for config in data["configurations"]:
        if "includePath" in config:
            if include_path in config["includePath"]:
                i = config["includePath"].index(include_path)
                del config["includePath"][i]
                
    with open(config_path, 'w') as f:
        json.dump(data, f, indent=4)

def change_loger_format(logger: logging.Logger, fmt: str):
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def build_sf_libs(headers: list[Path], defines: list[str]) -> list[Path] | None:
    if len(headers) != len(defines):
        logger.error("headers и defines должны быть одинаковой длины")
        return None

    objs: list[Path] = [h.with_suffix(".o") for h in headers]

    if all(obj.exists() for obj in objs):
        return objs

    share_args = ["-x", "c"]

    personal_args: dict[int, list[str]] = {
        i: [f"-D{defines[i]}"]
        for i in range(len(headers))
    }

    result = compile(
        src_s=headers,
        dst_s=objs,
        share_args=share_args,
        personal_args=personal_args,
    )

    if result is None:
        logger.error("ошибка сборки")
        return None

    return objs

def check_pkg_config(pkg: str) -> bool:
    if not os.path.exists(PKGS_PATH/pkg/"package.json"):
        logger.warning(f"'{PKGS_PATH/pkg/"package.json"}' не найден!")
        return False
    return True

def load_pkg_config(pkg: str) -> PackageConfig|None:
    if not check_pkg_config(pkg):
        return None
    with open(PKGS_PATH/pkg/"package.json") as fd:
        return json.loads(fd.read()) 

def get_pkg_args(pkg: str) -> dict|None:
    config: Config|None = load_config()
    if config is None: return None

    return config["dependencies"][pkg] if "dependencies" in config and pkg in config["dependencies"] else None

def create_lib_symlink(src_name: str, dst_name: str):
    config: Config|None = load_config()
    if config is None: return None

    if not "origin" in config: return
    libs_dir = BIN_PATH / config["origin"]

    target_name = src_name  
    soname = dst_name

    link_path = libs_dir / soname

    if link_path.is_symlink():
        os.unlink(link_path)

    os.symlink(target_name, link_path)

# @TODO compile - хуйня переделать 
def _compile_one(
    c_file: Path,
    dst: Path,
    cc: str,
    args: list[str],
) -> str|None:
    cmd: list[str] = [cc]+args+["-c", str(c_file), "-o", str(dst)]
    
    result = subprocess.run(cmd, text=True)
    if result.returncode != 0:
        logger.error(f"Ошибка сборки {c_file}!")
        return None

    return str(dst)

# @TODO compile - хуйня переделать 
#                                                                                       { 1: ["-Wall"] } - index: args
def compile(src_s: list[Path], dst_s: list[Path], share_args: list[str], personal_args: dict[int, list[str]] = {}) -> list[str]|None:
    config: Config | None = load_config()
    if config is None:
        return None

    cc: str | None = get_compiler()
    if cc is None:
        return None

    obj_files: list[str] = []
    max_workers: int = config["workers"] if "workers" in config else -1
    max_workers = os.cpu_count() or 1 if max_workers <= 0 else min(max_workers, os.cpu_count() or 1) 
    max_workers = min(len(src_s), max_workers)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _compile_one,
                c_file,
                dst_s[i],
                cc,
                share_args+personal_args.get(i, []),
            )
            for i, c_file in enumerate(src_s)
        ]

        for future in as_completed(futures):
            result = future.result()
            if result is None:
                for f in futures:
                    f.cancel()
                return None
            obj_files.append(result)

    return obj_files

def get_config_dir() -> Path | None:
    APP_NAME = "pcpm"
    try:
        if sys.platform.startswith("win"):
            base = os.getenv("APPDATA")
            if not base:
                return None
            path = Path(base) / APP_NAME

        elif sys.platform == "darwin":
            path = Path.home() / "Library" / "Application Support" / APP_NAME

        else:  # Linux и прочие Unix
            base = os.getenv("XDG_CONFIG_HOME")
            if base:
                path = Path(base) / APP_NAME
            else:
                path = Path.home() / ".config" / APP_NAME

        path.mkdir(parents=True, exist_ok=True)
        return path

    except Exception:
        return None
    
def get_template_config() -> Config | None:
    config_dir: Path|None = get_config_dir()
    if config_dir is None: return None
    return load_config(config_dir)
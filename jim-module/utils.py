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

from pcpm.ds import COMPILERS, Config, PKGS_PATH, ROOT_PATH, PackageConfig, BIN_PATH
from pcpm.utils import compile

logger = logging.getLogger(__name__)


def build_sf_libs(headers: list[Path], defines: list[str], share_args: list[str] = []) -> list[Path] | None:
    if len(headers) != len(defines):
        logger.error("headers и defines должны быть одинаковой длины")
        return None

    objs: list[Path] = [h.with_suffix(".o") for h in headers]

    if all(obj.exists() for obj in objs):
        return objs

    share_args += ["-x", "c"]

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


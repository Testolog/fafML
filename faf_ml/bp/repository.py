from os import path
from typing import List, Dict

from requests import get

from .constant import GITHUB_UNIT_URL


def download_file(auth_header, repo_path, file_repo_info: List[Dict[str, str]]):
    done_downloads = []
    for meta_unit in file_repo_info:
        _proto_info = get(meta_unit["url"], headers=auth_header).json()
        for elm in _proto_info:
            if ".bp" in elm["name"]:
                with open(path.join(repo_path, elm["name"]), "w+") as _tmp_file:
                    _content = get(elm["download_url"], headers=auth_header).text
                    done_downloads.append({"name": elm["name"]})
                    _tmp_file.write(_content)


def update_files():
    pass


def check_version():
    pass


def update_meta_data():
    pass


def create_list_to_upload(auth_header):
    all_units_folder = get(path.join(GITHUB_UNIT_URL, "units"), headers=auth_header).json()
    return [{"name": elm["name"], "url": path.join(GITHUB_UNIT_URL, elm["path"])} for elm in all_units_folder]

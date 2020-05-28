import csv
import sys
from os import path, remove, environ

from requests import get

from faf_ml.constant import GITHUB_UNIT_URL, BP_PATH, FAILED_FILE, SUCCESS_FILE


def download_file(auth_header):
    all_units_folder = get(path.join(GITHUB_UNIT_URL, "units"), headers=auth_header).json()
    print(all_units_folder)
    _meta_data = [{"name": elm["name"], "url": path.join(GITHUB_UNIT_URL, elm["path"])} for elm in all_units_folder]
    failed_path = path.join(BP_PATH, FAILED_FILE)
    try:
        done_downloads = []
        for meta_unit in _meta_data:
            _proto_info = get(meta_unit["url"], headers=auth_header).json()
            for elm in _proto_info:
                print(elm)
                if ".bp" in elm["name"]:
                    _tmp_file = open(path.join(BP_PATH, elm["name"]), "w")
                    _content = get(elm["download_url"], headers=auth_header).text
                    done_downloads.append({"name": elm["name"]})
                    _tmp_file.write(_content)
                    _tmp_file.flush()
                    _tmp_file.close()
    except Exception as inst:
        with open(failed_path, "w") as f:
            f.write("\n".join(inst.args))
        raise inst

    else:
        with open(path.join(BP_PATH, SUCCESS_FILE), "w") as f:
            writer = csv.writer(f)
            writer.writerows(done_downloads)
            if path.exists(failed_path):
                remove(failed_path)


# todo
def update_files():
    pass


if __name__ == '__main__':
    user_auth = {"Authorization": "token " + sys.argv[1] if len(sys.argv) >= 2 else environ["GIT_READ_TOKEN"]}
    print(user_auth)
    download_file(user_auth)

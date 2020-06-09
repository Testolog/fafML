import argparse
import json
import os
from pathlib import Path

from faf_ml.bp.constant import FAILED_FILE, SUCCESS_FILE, BP_EXTENSIONS
from faf_ml.bp.reader import read_file
from faf_ml.bp.repository import download_file, create_list_to_upload
from faf_ml.constant import BP_RAW_PATH, BP_JSON_PATH


# todo
# 1.append base conditional to check what is going on
# 2.append sqllite for tracking changes between version in local repo
# 3.use sqllite as used batch job processing.

def create_structure():
    Path(raw_location).mkdir(parents=True, exist_ok=True)
    Path(json_location).mkdir(parents=True, exist_ok=True)


def create_repo(git_token):
    user_auth = {"Authorization": "token " + git_token}
    meta_info = create_list_to_upload(user_auth)
    download_file(user_auth, raw_location, meta_info)
    Path(success_raw_path).touch()
    if os.path.exists(failed_raw_path):
        os.remove(failed_raw_path)


def convert_to_json():
    result_block = {}
    files = [os.path.join(root, _file) for root, dirs, files in os.walk(raw_location) for _file in files if
             BP_EXTENSIONS in _file]
    for path in files:
        print(path)
        content = read_file(path)
        json.dump([_.parsed for _ in content],
                  open(os.path.join(json_location, os.path.splitext(os.path.basename(path))[0]) + ".json", "w+"),
                  indent=2)
    return result_block


parser = argparse.ArgumentParser(description='Create local repository for bp processing')
parser.add_argument("-r", "--repository", dest="location_repo", action='store', help="location of repo")
parser.add_argument("-t", "--git_token", dest="git_token", action="store", required=False)
arg = parser.parse_args()
raw_location = os.path.join(arg.location_repo, BP_RAW_PATH)
json_location = os.path.join(arg.location_repo, BP_JSON_PATH)
failed_raw_path = os.path.join(raw_location, FAILED_FILE)
success_raw_path = os.path.join(raw_location, SUCCESS_FILE)

if arg.git_token:
    token = arg.git_token
elif "GIT_READ_TOKEN" in os.environ:
    token = os.environ["GIT_READ_TOKEN"]
else:
    raise Exception("hello")
create_structure()
try:
    if os.path.exists(failed_raw_path):
        create_repo(token)
except Exception as inst:
    with open(failed_raw_path, "w+") as f:
        f.write("\n".join(inst.args))
    raise inst
else:
    Path(success_raw_path).touch()
convert_to_json()

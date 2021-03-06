import argparse
import os
import re
from pathlib import Path

from faf_ml.bp.constant import BP_EXTENSIONS
from faf_ml.bp.reader import read_file
from faf_ml.bp.repository import download_file, create_list_to_upload
from faf_ml.constant import BP_RAW_PATH, BP_JSON_PATH, GLOBAL_NAME_UNIT, STOP_FILE_NAMING
from faf_ml.faf.tree_build import *
# todo
# 1.append base conditional to check what is going on
# 2.append sqllite for tracking changes between version in local repo
# 3.use sqllite as used batch job processing.
from faf_ml.flow_utils import dump_flag

parser = argparse.ArgumentParser(description='Create local repository for bp processing')
parser.add_argument("-r", "--repository", dest="location_repo", action='store', help="location of repo")
parser.add_argument("-t", "--git_token", dest="git_token", action="store", required=False)
arg = parser.parse_args()

raw_location = os.path.join(arg.location_repo, BP_RAW_PATH)
json_location = os.path.join(arg.location_repo, BP_JSON_PATH)


def create_structure():
    Path(raw_location).mkdir(parents=True, exist_ok=True)
    Path(json_location).mkdir(parents=True, exist_ok=True)


@dump_flag(process_location=raw_location)
def create_repo(git_token):
    user_auth = {"Authorization": "token " + git_token}
    meta_info = create_list_to_upload(user_auth)
    download_file(user_auth, raw_location, meta_info)


@dump_flag(process_location=json_location)
def convert_to_json():
    files = [os.path.join(root, _file) for root, dirs, files in os.walk(raw_location) for _file in files if
             BP_EXTENSIONS in _file]
    for path in files:
        content = read_file(path)
        for b in [_.parsed for _ in content]:
            bl = []
            if GLOBAL_NAME_UNIT in b:
                bl.append(b[GLOBAL_NAME_UNIT])
            else:
                print(b)
            json.dump(bl,
                      open(os.path.join(json_location, os.path.splitext(os.path.basename(path))[0]) + ".json", "w+"),
                      indent=2)


def read_json(file_path="../../data/test"):
    data = []
    for root, _, files in os.walk(file_path):
        for _file in files:
            with open(os.path.join(root, _file), 'r') as f:
                unit_id = re.findall(STOP_FILE_NAMING, os.path.basename(os.path.join(root, _file)))[0]
                data.append((unit_id, json.load(f)))
    return data


if arg.git_token:
    token = arg.git_token
elif "GIT_READ_TOKEN" in os.environ:
    token = os.environ["GIT_READ_TOKEN"]
else:
    raise Exception("hello")

# todo
create_structure()
create_repo()
convert_to_json()
all_units: List[DataFrame] = []
for _id, content in read_json(json_location):
    for data in content:
        lvl_df = build_multiple_lvl_df(data, _id, PROCESS_COLUMN)
        all_units.append(lvl_df)
df = zip_units_dfs(all_units)

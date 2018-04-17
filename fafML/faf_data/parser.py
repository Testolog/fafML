import requests
import pandas as pd
import re
from urllib.parse import urlparse

try:
    from BeautifulSoup import BeautifulSoup
except ImportError:
    from bs4 import BeautifulSoup

SEARCHED_INFO_CLM = ["category_name", "race_name", "unit_id", "unit_name"]
SITE_DB = "http://direct.faforever.com/faf/unitsDB"
GIT_RAW = "https://raw.githubusercontent.com"
FILTER_COLUMNS = ['D', '{', '0', 'U', '1', '3']
COLOR_TO_RACE = {
    "#C8F7C5": "aeon",
    "#ADB6C4": "uef",
    "#F1A9A0": "cybran",
    "#FDE3A7": "seraphim"
}


class FAFParsers:

    def __parse_base_information(self, call_back):
        """
        :param all:
        :param call_back:
        :type call_back:List
        :return:
        """
        get = requests.get(SITE_DB).content
        soup = BeautifulSoup(get, "lxml")
        unit_list__categories = soup.find("div", {"class": "unitlistCategories"})
        category = unit_list__categories.find_all("details")
        for table in category:
            category_name = table.find("summary", {"class": "categoryName"}).get_text()
            rows = table.find_all("div", {"class": "unitlistArmyRow"})
            for row in rows:
                cels = row.find_all("div", {"class": "classicStyle"})
                for cel in cels:
                    color = re.findall("#\w+", cel["style"].strip())
                    main = cel.find("div", {"class": "unitMainDiv"})
                    if not main:
                        continue
                    _id = main['id']
                    name = main.find_next('div', {"class": "unit"}) \
                        .find_next('div', {"class", "unitName"}) \
                        .find("span", {"class": "unitHotLink"}) \
                        .get_text()
                    if color:
                        call_back.append(
                            [str(category_name).strip().lower(), COLOR_TO_RACE[color[0]], str(_id).strip(),
                             str(name).strip().lower()])
                    else:
                        print([str(category_name).strip(), str(name).strip()])

    def __parse_advance_information(self, unit_id, call_back):
        get = requests.get(SITE_DB + "/", params=(("id", unit_id),))
        unit_soup = BeautifulSoup(get.content, "lxml")
        base_search_query = unit_soup.find("div", {"class": "comparisonBoard"}) \
            .find_all_next("div", {"class": "boardLane"})
        sheets = base_search_query
        heal = unit_soup.find("div", {"class": "comparisonBoard"}) \
            .find_next("div", {"class": "boardLane"}) \
            .find("div", {"class": "healthBar"})
        heal, regen = heal.get_text().split("+")
        call_back.append([unit_id, "base", "heal", heal.strip()])
        call_back.append([unit_id, "base", "regen", regen.strip()])
        for sheet in sheets:
            sections = sheet.find_all("div", {"class": "sheetSection"})
            for section in sections:
                if "unitBlueprints" in section.attrs["class"]:
                    continue
                base_section_info = section.find("div", {"class": "smallTitle"})
                if not base_section_info:
                    continue
                title = base_section_info.get_text().strip()
                if title in ["Wreckage", "Weapons", "Enhancements", "Veterancy"]:
                    continue
                columns = section.find("div", {"class": base_section_info.find_next("div")['class'][0].strip()}) \
                    .find_all("div")
                if "Abilities" in title:
                    column_value = [re.sub("[\[\]]", "", column.get_text().strip()).strip() for column in columns]
                    call_back.append([unit_id, title.strip(), title.strip(), column_value])
                else:
                    for column in columns:
                        column_name = column['class'][0]
                        column_value = column.get_text().strip()
                        call_back.append(
                            [unit_id, title.strip().lower(), column_name.strip().lower(), column_value.strip().lower()])

    def __parrse_advance_from_blueprint(self, unit_id, call_back):
        get = requests.get(SITE_DB + "/", params=(("id", unit_id),))
        unit_soup = BeautifulSoup(get.content, "lxml")
        link_to_bp = unit_soup.find("a", {'class': "blueprintLink"})['href'].strip()
        raw_path = urlparse(link_to_bp).path.replace("blob/", "")
        get = requests.get(GIT_RAW + raw_path)
        # unit_soup = BeautifulSoup(get.content, "lxml")
        get.content

    def __check_rolls(self):
        pass

    def parse(self) -> pd.DataFrame:
        faf_base_info = []
        faf_unit_info = []
        self.__parse_base_information(faf_base_info)
        df_base = pd.DataFrame(faf_base_info, columns=SEARCHED_INFO_CLM)
        df_base = df_base.reset_index(drop=True).set_index("unit_id")
        # self.__parrse_advance_from_blueprint(df_base.sample(2).index, faf_unit_info)
        [self.__parse_advance_information(_id, faf_unit_info) for _id in df_base.index]
        df_unit = pd.DataFrame(faf_unit_info, columns=["unit_id", "title", "key", "value"])
        df_unit = df_unit.drop_duplicates(["unit_id", "key"])
        df_unit = df_unit.pivot(index="unit_id", columns="key", values="value")
        # df_unit.info()
        # df_unit['name_weapon'] = df_unit['name']
        # del df_unit['name']
        return pd.merge(df_base, df_unit, right_index=True, left_index=True)
        # return df_base


if __name__ == '__main__':
    parser = FAFParsers()
    import sys, os

    path_out = sys.argv[1]
    if os.path.exists(path_out):
        path_out = os.path.join(path_out, 'faf_db.csv')
    df = parser.parse()
    df['id_unit'] = df.index
    df = df.reset_index(drop=True)
    df.sort_values(by=['race']).to_csv(path_out)

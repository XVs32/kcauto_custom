SLEEP_MODIFIER = 0
LOOP_BREAK_SECONDS = 20

MIN_JST_OFFSET = -20
MAX_JST_OFFSET = 20
MIN_PORT = 0
MAX_PORT = 65535
MAX_FLEET_PRESETS = 15

AUTO_PRESET = 0

OTHER_FLEET_ID = 999

MAX_RESOURCE = 350000

PASSIVE_TIME_INTERVAL = 180
OVERNIGHT_TIME_INTERVAL = 600

# game window dimensions
GAME_W = 1200
GAME_H = 720

CONTEXT_SORTIE = 1
CONTEXT_EXPEDITION = 2
CONTEXT_PVP = 3
CONTEXT_FACTORY = 4
CONTEXT_REPAIR = 5

CONTEXT_AUTO_EXPEDITION = 6
CONTEXT_AUTO_SORTIE = 7
CONTEXT_AUTO_PVP = 8

# chrome hook url targets
DEFAULT_CHROME_DEV_PORT = 9222
DEFAULT_POI_API_PORT = 9223
API_URL = "https://play.games.dmm.com/game/kancolle"
POI_URL_POSTFIX = "resources/app.asar/index.html"

# similarity presets
EXACT = 0.994
FLEET_ID_ICON = 0.99
NEAR_EXACT = 0.95
VISUAL_DAMAGE = 0.95
DEFAULT = 0.8

# click padding presets
PAGE_NAV = (10, 8, -10, -8)

# external urls
WCTF_DB_URL = (
    "https://raw.githubusercontent.com/TeamFleet/WhoCallsTheFleet/master"
    "/app-db/ships.nedb"
)
WCTF_SUFFIX_URL = (
    "https://raw.githubusercontent.com/TeamFleet/WhoCallsTheFleet/master"
    "/app-db/ship_namesuffix.nedb"
)

# config_path
COMBAT_CONFIG = "data/config/combat/"

EMPTY_EQUIPMENT_API = {
    "api_id": -1,
    "api_sortno": -1,
    "api_name": "空装備",
    "api_type": [-1, -1, -1, -1, -1],
    "api_taik": -1,
    "api_souk": -1,
    "api_houg": -1,
    "api_raig": -1,
    "api_soku": -1,
    "api_baku": -1,
    "api_tyku": -1,
    "api_tais": -1,
    "api_atap": -1,
    "api_houm": -1,
    "api_raim": -1,
    "api_houk": -1,
    "api_raik": -1,
    "api_bakk": -1,
    "api_saku": -1,
    "api_sakb": -1,
    "api_luck": -1,
    "api_leng": -1,
    "api_rare": -1,
    "api_broken": [-1, -1, -1, -1],
    "api_usebull": "-1",
    "api_version": 2,
}
TEMP_EQUIPMENT_API = {
    "api_id": 0,
    "api_sortno": 0,
    "api_name": "仮設装備",
    "api_type": [-1, -1, -1, -1, -1],
    "api_taik": -1,
    "api_souk": -1,
    "api_houg": -1,
    "api_raig": -1,
    "api_soku": -1,
    "api_baku": -1,
    "api_tyku": -1,
    "api_tais": -1,
    "api_atap": -1,
    "api_houm": -1,
    "api_raim": -1,
    "api_houk": -1,
    "api_raik": -1,
    "api_bakk": -1,
    "api_saku": -1,
    "api_sakb": -1,
    "api_luck": -1,
    "api_leng": -1,
    "api_rare": -1,
    "api_broken": [-1, -1, -1, -1],
    "api_usebull": "-1",
    "api_version": 2,
}

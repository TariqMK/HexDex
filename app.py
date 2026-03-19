import os
import json
import struct
import time
import requests
from flask import Flask, jsonify, request, render_template

app = Flask(__name__)

POKEAPI_BASE  = "https://pokeapi.co/api/v2"
CACHE_DIR     = "cache"
CACHE_FILE    = os.path.join(CACHE_DIR, "pokeapi_cache.json")
IMAGE_DIR     = os.path.join(CACHE_DIR, "images")
NOTES_FILE    = os.path.join(CACHE_DIR, "notes.json")

os.makedirs(IMAGE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Notes and tags (keyed by filename - one record per variant file)
# ---------------------------------------------------------------------------

def load_notes():
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_notes(notes):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2)

# ---------------------------------------------------------------------------
# PokéAPI cache layer
# ---------------------------------------------------------------------------

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f)

def cache_image(url: str, filename: str) -> str:
    """Download image to cache/images/ if not already present.
    Returns a local /cached-image/<filename> URL, or the original on failure."""
    if not url:
        return url
    local_path = os.path.join(IMAGE_DIR, filename)
    if not os.path.exists(local_path):
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"Image cache failed for {url}: {e}")
            return url
    return f"/cached-image/{filename}"

def fetch_pokemon_data(species_id, cache):
    key = str(species_id)
    if key in cache:
        return cache[key]

    try:
        # Main pokemon endpoint (types, sprites, abilities, stats, moves)
        r1 = requests.get(f"{POKEAPI_BASE}/pokemon/{species_id}", timeout=10)
        r1.raise_for_status()
        poke = r1.json()

        # Species endpoint (flavour text, genus, gender rate)
        r2 = requests.get(f"{POKEAPI_BASE}/pokemon-species/{species_id}", timeout=10)
        r2.raise_for_status()
        species = r2.json()

        # Pick English flavour text
        flavour = ""
        for entry in species.get("flavor_text_entries", []):
            if entry["language"]["name"] == "en":
                flavour = entry["flavor_text"].replace("\n", " ").replace("\f", " ")
                break

        # Pick English genus
        genus = ""
        for g in species.get("genera", []):
            if g["language"]["name"] == "en":
                genus = g["genus"]
                break

        raw_sprite_hd = (
            poke["sprites"]["other"]["official-artwork"]["front_default"]
            or poke["sprites"]["front_default"]
        )
        raw_sprite_shiny = (
            poke["sprites"]["other"]["official-artwork"].get("front_shiny")
            or poke["sprites"]["front_shiny"]
        )

        # Cache images locally
        sprite_hd    = cache_image(raw_sprite_hd,    f"{species_id}_hd.png")
        sprite_shiny = cache_image(raw_sprite_shiny, f"{species_id}_shiny.png")

        data = {
            "id": species_id,
            "name": poke["name"],
            "types": [t["type"]["name"] for t in poke["types"]],
            "sprite_hd":       sprite_hd,
            "sprite_shiny_hd": sprite_shiny,
            "abilities": [
                {"name": a["ability"]["name"], "hidden": a["is_hidden"]}
                for a in poke["abilities"]
            ],
            "base_stats": {s["stat"]["name"]: s["base_stat"] for s in poke["stats"]},
            "height": poke["height"],
            "weight": poke["weight"],
            "flavour_text": flavour,
            "genus": genus,
            "base_experience": poke["base_experience"],
            "growth_rate": species.get("growth_rate", {}).get("name", "medium-fast"),
        }

        cache[key] = data
        save_cache(cache)
        time.sleep(0.2)  # be polite to PokéAPI
        return data

    except Exception as e:
        print(f"PokéAPI error for species {species_id}: {e}")
        return None

def fetch_move_data(move_id: int, cache: dict) -> dict | None:
    """Fetch name, type, damage class, power, accuracy, PP for a move by ID."""
    if move_id == 0:
        return None
    key = f"move:{move_id}"
    if key in cache:
        return cache[key]

    try:
        r = requests.get(f"{POKEAPI_BASE}/move/{move_id}", timeout=10)
        r.raise_for_status()
        m = r.json()

        # English name
        name = m["name"]  # fallback: slug
        for n in m.get("names", []):
            if n["language"]["name"] == "en":
                name = n["name"]
                break

        # English flavour text (pick shortest / most recent)
        effect = ""
        for e in m.get("flavor_text_entries", []):
            if e["language"]["name"] == "en":
                effect = e["flavor_text"].replace("\n", " ").replace("\f", " ")
                break

        data = {
            "id":           move_id,
            "name":         name,
            "type":         m["type"]["name"],
            "damage_class": m["damage_class"]["name"],   # physical / special / status
            "power":        m.get("power"),               # None for status moves
            "accuracy":     m.get("accuracy"),
            "pp":           m.get("pp"),
        }

        cache[key] = data
        save_cache(cache)
        time.sleep(0.15)
        return data

    except Exception as e:
        print(f"PokéAPI move error for id {move_id}: {e}")
        return None

def fetch_ability_data(ability_name: str, cache: dict) -> dict | None:
    """Fetch English description for an ability. Cached under ability:<name>."""
    key = f"ability:{ability_name}"
    if key in cache:
        return cache[key]
    try:
        r = requests.get(f"{POKEAPI_BASE}/ability/{ability_name}", timeout=10)
        r.raise_for_status()
        a = r.json()

        # English display name
        display_name = ability_name
        for n in a.get("names", []):
            if n["language"]["name"] == "en":
                display_name = n["name"]
                break

        # English effect (short effect preferred, falls back to full)
        effect = ""
        for e in a.get("effect_entries", []):
            if e["language"]["name"] == "en":
                effect = e.get("short_effect") or e.get("effect") or ""
                break

        data = {"name": display_name, "effect": effect}
        cache[key] = data
        save_cache(cache)
        time.sleep(0.15)
        return data
    except Exception as e:
        print(f"PokéAPI ability error for {ability_name}: {e}")
        return None


# ---------------------------------------------------------------------------
# Item ID translation tables for Gen 2 and Gen 3
# ---------------------------------------------------------------------------
# Gen 4-7 item IDs match PokéAPI directly. Gen 2-3 use different internal
# numbering, so we map them to PokéAPI item slugs (name-based lookup).
# Only holdable items are included — key items, TMs, balls are excluded.
# Sources: Bulbapedia item index lists cross-referenced with PokéAPI slugs.

# Gen 2 (Gold/Silver/Crystal) internal item ID -> PokéAPI slug
GEN2_ITEM_SLUGS = {
    # Vitamins / battle items
    26: "hp-up", 27: "protein", 28: "iron", 29: "carbos", 30: "calcium",
    31: "rare-candy", 32: "pp-up", 33: "zinc", 34: "pp-max",
    # In-battle stat boosters
    36: "guard-spec", 37: "dire-hit", 38: "x-attack", 39: "x-defend",
    40: "x-speed", 41: "x-accuracy", 42: "x-sp-atk",
    # Held items (the ones that matter most for Gen2)
    178: "brightpowder",   179: "lucky-punch",  180: "metal-powder",
    181: "stick",          182: "heart-scale",
    196: "kings-rock",     197: "silver-powder",
    198: "amulet-coin",    199: "cleanse-tag",
    211: "soul-dew",       212: "deep-sea-tooth", 213: "deep-sea-scale",
    214: "smoke-ball",     215: "everstone",
    216: "focus-band",     217: "lucky-egg",    218: "scope-lens",
    219: "metal-coat",     220: "leftovers",    221: "dragon-scale",
    222: "light-ball",     223: "soft-sand",    224: "hard-stone",
    225: "miracle-seed",   226: "blackglasses", 227: "black-belt",
    228: "magnet",         229: "mystic-water", 230: "sharp-beak",
    231: "poison-barb",    232: "nevermeltice", 233: "spell-tag",
    234: "twistedspoon",   235: "charcoal",     236: "dragon-fang",
    237: "silk-scarf",     238: "up-grade",     239: "shell-bell",
    240: "sea-incense",    241: "lax-incense",  242: "lucky-punch",
    243: "metal-powder",   244: "thick-club",   245: "stick",
    # Berries (Gen2 berries map to their Gen3+ equivalents)
    197: "oran-berry",     198: "sitrus-berry",
    # Common consumable held items
    246: "scope-lens",     247: "metal-coat",   248: "leftovers",
    249: "dragon-scale",   250: "light-ball",
}

# Gen 3 (RS/E/FR/LG) internal item ID -> PokéAPI slug
GEN3_ITEM_SLUGS = {
    # Vitamins
    17: "hp-up", 18: "protein", 19: "iron", 20: "carbos", 21: "calcium",
    22: "rare-candy", 23: "pp-up", 24: "zinc", 25: "pp-max",
    # In-battle items
    26: "guard-spec", 27: "dire-hit", 28: "x-attack", 29: "x-defend",
    30: "x-speed", 31: "x-accuracy", 32: "x-sp-atk",
    # Key held items by Gen3 internal ID (from Bulbapedia Gen III index list)
    178: "kings-rock",     179: "silverpowder",  180: "amulet-coin",
    181: "cleanse-tag",    182: "soul-dew",       183: "deep-sea-tooth",
    184: "deep-sea-scale", 185: "smoke-ball",     186: "everstone",
    187: "focus-band",     188: "lucky-egg",      189: "scope-lens",
    190: "metal-coat",     191: "leftovers",      192: "dragon-scale",
    193: "light-ball",     194: "soft-sand",      195: "hard-stone",
    196: "miracle-seed",   197: "blackglasses",   198: "black-belt",
    199: "magnet",         200: "mystic-water",   201: "sharp-beak",
    202: "poison-barb",    203: "nevermeltice",   204: "spell-tag",
    205: "twistedspoon",   206: "charcoal",       207: "dragon-fang",
    208: "silk-scarf",     209: "up-grade",       210: "shell-bell",
    211: "sea-incense",    212: "lax-incense",    213: "lucky-punch",
    214: "metal-powder",   215: "thick-club",     216: "stick",
    # Berries (Gen3 has many berries; common held ones)
    133: "oran-berry",     134: "sitrus-berry",   135: "leppa-berry",
    136: "lum-berry",      137: "rawst-berry",    138: "aspear-berry",
    139: "persim-berry",   140: "chesto-berry",   141: "pecha-berry",
    142: "cheri-berry",    143: "figy-berry",     144: "wiki-berry",
    145: "mago-berry",     146: "aguav-berry",    147: "iapapa-berry",
    148: "razz-berry",     149: "bluk-berry",     150: "nanab-berry",
    151: "wepear-berry",   152: "pinap-berry",    153: "pomeg-berry",
    154: "kelpsy-berry",   155: "qualot-berry",   156: "hondew-berry",
    157: "grepa-berry",    158: "tamato-berry",   159: "cornn-berry",
    160: "magost-berry",   161: "rabuta-berry",   162: "nomel-berry",
    163: "spelon-berry",   164: "pamtre-berry",   165: "watmel-berry",
    166: "durin-berry",    167: "belue-berry",    168: "liechi-berry",
    169: "ganlon-berry",   170: "salac-berry",    171: "petaya-berry",
    172: "apicot-berry",   173: "lansat-berry",   174: "starf-berry",
    175: "enigma-berry",
}

def translate_item_id(item_id: int, generation: int):
    """Translate a Gen2/3 internal item ID to a PokéAPI-compatible identifier.
    Returns the item_id unchanged for Gen4+ (direct PokéAPI match).
    Returns a slug string for Gen2/3, or None if unknown."""
    if generation <= 1 or item_id == 0:
        return None
    if generation == 2:
        return GEN2_ITEM_SLUGS.get(item_id, None)
    if generation == 3:
        return GEN3_ITEM_SLUGS.get(item_id, None)
    # Gen 4-7: IDs match PokéAPI directly
    return item_id

def fetch_item_data(item_id, cache: dict) -> dict | None:
    """Fetch English name and description for a held item.
    item_id can be an int (Gen4+ direct PokéAPI ID) or a slug string (Gen2/3).
    Cached under item:{item_id}. Returns None for item_id 0 or None."""
    if not item_id:
        return None
    key = f"item:{item_id}"
    if key in cache:
        return cache[key]
    try:
        r = requests.get(f"{POKEAPI_BASE}/item/{item_id}", timeout=10)
        r.raise_for_status()
        it = r.json()

        name = it.get("name", "")
        for n in it.get("names", []):
            if n["language"]["name"] == "en":
                name = n["name"]
                break

        effect = ""
        for e in it.get("effect_entries", []):
            if e["language"]["name"] == "en":
                effect = e.get("short_effect") or e.get("effect") or ""
                break
        # Fallback to flavour text if no effect entry
        if not effect:
            for ft in it.get("flavor_text_entries", []):
                if ft["language"]["name"] == "en":
                    effect = ft.get("text", "").replace("\n", " ").replace("\f", " ")
                    break

        data = {"name": name, "effect": effect}
        cache[key] = data
        save_cache(cache)
        time.sleep(0.15)
        return data
    except Exception as e:
        print(f"PokéAPI item error for id {item_id}: {e}")
        return None

def enrich_moves(move_ids: list, cache: dict) -> list:
    """Return list of move dicts for the four move slots (skipping 0s and invalid IDs)."""
    MAX_VALID_MOVE = 826
    result = []
    for mid in move_ids:
        if mid == 0 or mid > MAX_VALID_MOVE:
            result.append(None)
        else:
            result.append(fetch_move_data(mid, cache))
    return result

def fetch_evo_chain(species_id: int, cache: dict) -> list:
    """Return evolution chain as ordered list of dicts: [{id, name, min_level, trigger}].
    Cached under evo:<species_id>."""
    key = f"evo:{species_id}"
    if key in cache:
        return cache[key]

    try:
        # Get species to find evo chain URL
        r1 = requests.get(f"{POKEAPI_BASE}/pokemon-species/{species_id}", timeout=10)
        r1.raise_for_status()
        chain_url = r1.json()["evolution_chain"]["url"]

        r2 = requests.get(chain_url, timeout=10)
        r2.raise_for_status()
        chain_data = r2.json()["chain"]

        def parse_chain(node, result):
            sid = int(node["species"]["url"].rstrip("/").split("/")[-1])
            name = node["species"]["name"]
            # Get evolution details for how this stage is reached
            details = node.get("evolution_details", [])
            trigger = None
            min_level = None
            item = None
            if details:
                d = details[0]
                trigger = d.get("trigger", {}).get("name")
                min_level = d.get("min_level")
                if d.get("item"): item = d["item"]["name"]
                if d.get("held_item"): item = d["held_item"]["name"]
            result.append({"id": sid, "name": name, "min_level": min_level,
                           "trigger": trigger, "item": item})
            for child in node.get("evolves_to", []):
                parse_chain(child, result)
            return result

        chain = parse_chain(chain_data, [])

        # Cache the HD sprite for each evo chain member so they work offline.
        # Uses the same naming as fetch_pokemon_data: {id}_hd.png
        for member in chain:
            sid = member["id"]
            img_path = os.path.join(IMAGE_DIR, f"{sid}_hd.png")
            if not os.path.exists(img_path):
                sprite_url = f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{sid}.png"
                cache_image(sprite_url, f"{sid}_hd.png")

        cache[key] = chain
        save_cache(cache)
        time.sleep(0.15)
        return chain

    except Exception as e:
        print(f"Evo chain error for {species_id}: {e}")
        return []

# ---------------------------------------------------------------------------
# Gen 1 & 2 shared utilities
# ---------------------------------------------------------------------------

# Gen 1/2 character encoding (0x50 = terminator, 0x7F = space)
GEN12_CHAR_MAP = {
    0x50: None, 0x7F: ' ',
    0x80:'A',0x81:'B',0x82:'C',0x83:'D',0x84:'E',0x85:'F',0x86:'G',0x87:'H',
    0x88:'I',0x89:'J',0x8A:'K',0x8B:'L',0x8C:'M',0x8D:'N',0x8E:'O',0x8F:'P',
    0x90:'Q',0x91:'R',0x92:'S',0x93:'T',0x94:'U',0x95:'V',0x96:'W',0x97:'X',
    0x98:'Y',0x99:'Z',
    0xA0:'a',0xA1:'b',0xA2:'c',0xA3:'d',0xA4:'e',0xA5:'f',0xA6:'g',0xA7:'h',
    0xA8:'i',0xA9:'j',0xAA:'k',0xAB:'l',0xAC:'m',0xAD:'n',0xAE:'o',0xAF:'p',
    0xB0:'q',0xB1:'r',0xB2:'s',0xB3:'t',0xB4:'u',0xB5:'v',0xB6:'w',0xB7:'x',
    0xB8:'y',0xB9:'z',
    0xF6:'0',0xF7:'1',0xF8:'2',0xF9:'3',0xFA:'4',
    0xFB:'5',0xFC:'6',0xFD:'7',0xFE:'8',0xFF:'9',
}

def decode_gen12_string(data: bytes) -> str:
    result = []
    for b in data:
        if b == 0x50:
            break
        ch = GEN12_CHAR_MAP.get(b)
        if ch:
            result.append(ch)
    return ''.join(result).strip()

# Gen 1 internal species index -> national dex number
GEN1_SPECIES_MAP = {
    0x99:1,0x09:2,0x9A:3,0xB0:4,0xB2:5,0xB4:6,0xB1:7,0xB3:8,0x1C:9,
    0x7B:10,0x7C:11,0x7D:12,0x70:13,0x71:14,0x72:15,0x24:16,0x96:17,
    0x97:18,0xA5:19,0xA6:20,0x05:21,0x23:22,0x6C:23,0x2D:24,0x54:25,
    0x55:26,0x60:27,0x61:28,0x0F:29,0xA8:30,0x10:31,0x03:32,0xA7:33,
    0x07:34,0x04:35,0x8E:36,0x52:37,0x53:38,0x64:39,0x65:40,0x6B:41,
    0x82:42,0xB9:43,0xBA:44,0xBB:45,0x6D:46,0x2E:47,0x41:48,0x77:49,
    0x3B:50,0x76:51,0x4D:52,0x90:53,0x2F:54,0x80:55,0x39:56,0x75:57,
    0x21:58,0x14:59,0x47:60,0x6E:61,0x6F:62,0x94:63,0x26:64,0x95:65,
    0x6A:66,0x29:67,0x7E:68,0xBC:69,0xBD:70,0xBE:71,0x18:72,0x9B:73,
    0xA9:74,0x27:75,0x31:76,0xA3:77,0xA4:78,0x25:79,0x08:80,0xAD:81,
    0x36:82,0x40:83,0x46:84,0x74:85,0x3A:86,0x78:87,0x0D:88,0x88:89,
    0x17:90,0x8B:91,0x19:92,0x93:93,0x0E:94,0x22:95,0x30:96,0x81:97,
    0x4E:98,0x8A:99,0x06:100,0x8D:101,0x0C:102,0x0A:103,0x11:104,0x91:105,
    0x2B:106,0x2C:107,0x0B:108,0x37:109,0x8F:110,0x12:111,0x01:112,
    0x28:113,0x1E:114,0x02:115,0x5C:116,0x5D:117,0x9D:118,0x9E:119,
    0x1B:120,0x98:121,0x2A:122,0x1A:123,0x48:124,0x35:125,0x33:126,
    0x1D:127,0x3C:128,0x85:129,0x16:130,0x13:131,0x4C:132,0x69:133,
    0x68:134,0x67:135,0x66:136,0xAA:137,0x62:138,0x63:139,0x5A:140,
    0x5B:141,0xAB:142,0x84:143,0x4A:144,0x4B:145,0x49:146,0x58:147,
    0x59:148,0x42:149,0x83:150,0x15:151,
}

def dv_shiny(dv_word: int) -> bool:
    """A Gen 1/2 pokemon is shiny if Def=Spd=Spc=10 and Atk in {2,3,6,7,10,11,14,15}."""
    atk  = (dv_word >> 12) & 0xF
    def_ = (dv_word >>  8) & 0xF
    spd  = (dv_word >>  4) & 0xF
    spc  = (dv_word >>  0) & 0xF
    return def_ == 10 and spd == 10 and spc == 10 and atk in (2,3,6,7,10,11,14,15)

def dv_hp(dv_word: int) -> int:
    """Derive HP DV from other DVs."""
    atk  = (dv_word >> 12) & 0xF
    def_ = (dv_word >>  8) & 0xF
    spd  = (dv_word >>  4) & 0xF
    spc  = (dv_word >>  0) & 0xF
    return ((atk & 1) << 3) | ((def_ & 1) << 2) | ((spd & 1) << 1) | (spc & 1)

# ---------------------------------------------------------------------------
# Gen 1 parser (.pk1 — 55 bytes from PKHeX export)
# PKHeX layout: 33 bytes box data, then 11 bytes OT name, 11 bytes nickname
# ---------------------------------------------------------------------------

def parse_pk1(data: bytes) -> dict:
    """Parse a PKHeX-exported .pk1 file.
    Confirmed layout from real Blue/Red file (69 bytes):
      0x00: list-count prefix byte (0x01), skip
      0x01: species internal index (needs GEN1_SPECIES_MAP lookup)
      0x06: level
      0x0B-0x0E: moves (4 x 1 byte)
      0x0F-0x10: OT ID (big-endian)
      0x11-0x13: EXP (3 bytes big-endian)
      0x14-0x1D: Stat EXP (5 x 2 bytes big-endian: HP,ATK,DEF,SPD,SPC)
      0x1E-0x1F: DV word (big-endian: Atk[15:12] Def[11:8] Spd[7:4] Spc[3:0])
      0x20-0x23: PP 1-4 (lower 6 bits = current PP)
      0x2F-0x38: OT name (up to 10 bytes, 0x50 terminated)
      0x3A-0x44: Nickname (up to 11 bytes, 0x50 terminated)
    """
    if len(data) < 33:
        return None

    species_internal = data[0x01]
    species = GEN1_SPECIES_MAP.get(species_internal)
    if not species:
        return None

    level    = data[0x06]
    moves    = [data[0x0B], data[0x0C], data[0x0D], data[0x0E]]
    ot_id    = struct.unpack_from('>H', data, 0x0F)[0]
    exp      = (data[0x11] << 16) | (data[0x12] << 8) | data[0x13]
    pp       = [data[0x20] & 0x3F, data[0x21] & 0x3F,
                data[0x22] & 0x3F, data[0x23] & 0x3F]
    dv_word  = struct.unpack_from('>H', data, 0x1E)[0]
    atk_dv   = (dv_word >> 12) & 0xF
    def_dv   = (dv_word >>  8) & 0xF
    spd_dv   = (dv_word >>  4) & 0xF
    spc_dv   = (dv_word >>  0) & 0xF
    hp_dv    = dv_hp(dv_word)
    shiny    = dv_shiny(dv_word)

    ot_name  = decode_gen12_string(data[0x2F:0x3A]) if len(data) > 0x2F else ""
    nickname = decode_gen12_string(data[0x3A:0x45]) if len(data) > 0x3A else ""

    return {
        "filename": "",
        "generation": 1,
        "origin_game": "Red / Blue / Yellow",
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "ot_sid": 0,
        "level": level,
        "nature": None,
        "shiny": shiny,
        "is_egg": False,
        "experience": exp,
        "friendship": 0,
        "moves": moves,
        "pp": pp,
        "ivs": {
            "hp": hp_dv, "attack": atk_dv, "defense": def_dv,
            "speed": spd_dv, "sp_atk": spc_dv, "sp_def": spc_dv
        },
        "evs": {"hp": 0, "attack": 0, "defense": 0, "speed": 0, "sp_atk": 0, "sp_def": 0},
    }

# ---------------------------------------------------------------------------
# Gen 2 parser (.pk2 — 54 bytes from PKHeX export)
# PKHeX layout: 32 bytes box data, then 11 bytes OT name, 11 bytes nickname
# ---------------------------------------------------------------------------

def parse_pk2(data: bytes) -> dict:
    """Parse a PKHeX-exported .pk2 file. Two formats detected by file size:

    PARTY format (73 bytes) — confirmed from real Gold Gyarados:
      0x00: list-count prefix (0x01), skip
      0x01: species (national dex)
      0x02: held item
      0x03-0x06: moves (4 x 1 byte)
      0x07-0x08: OT ID (big-endian)
      0x09-0x0B: EXP (3 bytes big-endian)
      0x18-0x19: DV word (big-endian)
      0x1C: friendship
      0x1D: level
      0x33-0x3D: OT name (11 bytes, 0x50 terminated)
      0x3E-0x48: Nickname (11 bytes, 0x50 terminated)

    BOX format (55 bytes) — confirmed from real Silver Sudowoodo:
      0x00-0x0A: OT name (11 bytes, 0x50 terminated)
      0x0B-0x15: Nickname (11 bytes, 0x50 terminated)
      0x16: padding (0x00)
      0x17: species (national dex)
      0x18: held item
      0x19-0x1C: moves (4 x 1 byte)
      0x1D-0x1E: OT ID (big-endian)
      0x1F-0x21: EXP (3 bytes big-endian)
      0x22-0x2B: Stat EXP (5 x 2 bytes)
      0x2C-0x2D: DV word (big-endian)
      0x2E-0x31: PP (4 bytes, lower 6 bits)
      0x32: friendship
      0x36 (last byte): level (PKHeX appends this)
    """
    if len(data) < 34:
        return None

    if len(data) >= 70:
        # PARTY format
        species_byte = data[0x01]
        is_egg_g2 = (species_byte == 0xFD)  # 0xFD = Gen2 egg marker
        species    = data[0x03] if is_egg_g2 else species_byte
        held_item  = data[0x02]
        moves      = [0,0,0,0] if is_egg_g2 else [data[0x03], data[0x04], data[0x05], data[0x06]]
        ot_id      = struct.unpack_from('>H', data, 0x07)[0]
        exp        = (data[0x09] << 16) | (data[0x0A] << 8) | data[0x0B]
        dv_word    = struct.unpack_from('>H', data, 0x18)[0]
        friendship = data[0x1C]
        level      = 1 if is_egg_g2 else data[0x1D]
        pp         = [data[0x1A] & 0x3F, data[0x1B] & 0x3F,
                      data[0x1C] & 0x3F, data[0x1D] & 0x3F]
        ot_name    = decode_gen12_string(data[0x33:0x3E]) if len(data) > 0x33 else ""
        nickname   = "Egg" if is_egg_g2 else decode_gen12_string(data[0x3E:0x49]) if len(data) > 0x3E else ""
    else:
        # BOX format — no known egg format for Gen2 box, treat normally
        is_egg_g2  = False
        species    = data[0x17]
        held_item  = data[0x18]
        moves      = [data[0x19], data[0x1A], data[0x1B], data[0x1C]]
        ot_id      = struct.unpack_from('>H', data, 0x1D)[0]
        exp        = (data[0x1F] << 16) | (data[0x20] << 8) | data[0x21]
        dv_word    = struct.unpack_from('>H', data, 0x2C)[0]
        friendship = data[0x32]
        level      = data[-1]  # PKHeX appends level as last byte
        pp         = [data[0x2E] & 0x3F, data[0x2F] & 0x3F,
                      data[0x30] & 0x3F, data[0x31] & 0x3F]
        ot_name    = decode_gen12_string(data[0x00:0x0B])
        nickname   = decode_gen12_string(data[0x0B:0x16])

    if species == 0 or species > 251:
        return None

    atk_dv  = (dv_word >> 12) & 0xF
    def_dv  = (dv_word >>  8) & 0xF
    spd_dv  = (dv_word >>  4) & 0xF
    spc_dv  = (dv_word >>  0) & 0xF
    hp_dv   = dv_hp(dv_word)
    shiny   = dv_shiny(dv_word)

    return {
        "filename": "",
        "generation": 2,
        "origin_game": "Gold / Silver / Crystal",
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "ot_sid": 0,
        "level": level,
        "nature": None,
        "shiny": shiny,
        "is_egg": is_egg_g2,
        "experience": exp,
        "friendship": friendship,
        "moves": moves,
        "pp": pp,
        "ivs": {
            "hp": hp_dv, "attack": atk_dv, "defense": def_dv,
            "speed": spd_dv, "sp_atk": spc_dv, "sp_def": spc_dv
        },
        "evs": {"hp": 0, "attack": 0, "defense": 0, "speed": 0, "sp_atk": 0, "sp_def": 0},
        "held_item_id": held_item,
    }

# ---------------------------------------------------------------------------
# Gen 7 parser (.pk7 — 232 bytes, pre-decrypted PKHeX export)
# ---------------------------------------------------------------------------
# Identical format to pk6. Same offsets for all fields.
# Only difference: species range 1-809, and different origin game IDs.
# Sun=30, Moon=31, Ultra Sun=32, Ultra Moon=33
# Confirmed from real Sun, Moon, Ultra Sun, Ultra Moon files.

def parse_pk7(raw: bytes) -> dict:
    if len(raw) < 232:
        return None

    pv         = struct.unpack_from('<I', raw, 0)[0]
    species    = struct.unpack_from('<H', raw, 8)[0]
    if species == 0 or species > 809:
        return None

    held_item  = struct.unpack_from('<H', raw, 10)[0]
    ot_id      = struct.unpack_from('<H', raw, 12)[0]
    ot_sid     = struct.unpack_from('<H', raw, 14)[0]
    exp        = struct.unpack_from('<I', raw, 16)[0]
    friendship = raw[20]
    nature_id  = raw[28]
    nature     = NATURES_GEN3[nature_id % 25]

    ev_hp  = raw[30]; ev_atk = raw[31]; ev_def = raw[32]
    ev_spd = raw[33]; ev_spa = raw[34]; ev_spd2= raw[35]

    nickname   = decode_gen5_string(raw[64:], 12)
    moves      = struct.unpack_from('<4H', raw, 90)
    pp         = struct.unpack_from('<4B', raw, 98)

    iv_raw     = struct.unpack_from('<I', raw, 116)[0]
    iv_hp      = (iv_raw >> 0)  & 0x1F
    iv_atk     = (iv_raw >> 5)  & 0x1F
    iv_def     = (iv_raw >> 10) & 0x1F
    iv_spd     = (iv_raw >> 15) & 0x1F
    iv_spa     = (iv_raw >> 20) & 0x1F
    iv_spd2    = (iv_raw >> 25) & 0x1F
    is_egg     = bool((iv_raw >> 30) & 1)

    ot_name    = decode_gen5_string(raw[176:], 12)
    level      = raw[221]

    GEN7_GAMES = {
        # Gen 7 games
        30: 'Sun', 31: 'Moon',
        32: 'Ultra Sun', 33: 'Ultra Moon',
        # Gen 6 games — Pokémon transferred via Pokémon Bank retain their origin
        24: 'X', 25: 'Y',
        26: 'Alpha Sapphire', 27: 'Omega Ruby',
    }
    origin_game = GEN7_GAMES.get(raw[223], f'Unknown (0x{raw[223]:02X})')
    shiny       = ((ot_id ^ ot_sid ^ (pv >> 16) ^ (pv & 0xFFFF)) < 8)

    return {
        "filename": "",
        "generation": 7,
        "origin_game": origin_game,
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "level": level,
        "nature": nature,
        "shiny": shiny,
        "is_egg": is_egg,
        "experience": exp,
        "friendship": friendship,
        "moves": list(moves),
        "pp": list(pp),
        "ivs": {
            "hp": iv_hp, "attack": iv_atk, "defense": iv_def,
            "speed": iv_spd, "sp_atk": iv_spa, "sp_def": iv_spd2
        },
        "evs": {
            "hp": ev_hp, "attack": ev_atk, "defense": ev_def,
            "speed": ev_spd, "sp_atk": ev_spa, "sp_def": ev_spd2
        },
        "held_item_id": held_item,
    }


# ---------------------------------------------------------------------------
# Gen 6 parser (.pk6 — 232 bytes, pre-decrypted PKHeX export)
# ---------------------------------------------------------------------------
# Confirmed offsets from real X, Y, Omega Ruby, Alpha Sapphire files.
# PKHeX exports already decrypted — read fixed offsets directly.
# File is always 232 bytes (single format, no party/box split).
# Gen6 uses standard UTF-16LE strings (null 0x0000 terminated).
# Species range: 1–721.

def parse_pk6(raw: bytes) -> dict:
    if len(raw) < 232:
        return None

    pv         = struct.unpack_from('<I', raw, 0)[0]
    species    = struct.unpack_from('<H', raw, 8)[0]
    if species == 0 or species > 721:
        return None

    held_item  = struct.unpack_from('<H', raw, 10)[0]
    ot_id      = struct.unpack_from('<H', raw, 12)[0]
    ot_sid     = struct.unpack_from('<H', raw, 14)[0]
    exp        = struct.unpack_from('<I', raw, 16)[0]
    friendship = raw[20]
    nature_id  = raw[28]
    nature     = NATURES_GEN3[nature_id % 25]

    ev_hp  = raw[30]; ev_atk = raw[31]; ev_def = raw[32]
    ev_spd = raw[33]; ev_spa = raw[34]; ev_spd2= raw[35]

    nickname   = decode_gen5_string(raw[64:], 12)
    moves      = struct.unpack_from('<4H', raw, 90)
    pp         = struct.unpack_from('<4B', raw, 98)

    iv_raw     = struct.unpack_from('<I', raw, 116)[0]
    iv_hp      = (iv_raw >> 0)  & 0x1F
    iv_atk     = (iv_raw >> 5)  & 0x1F
    iv_def     = (iv_raw >> 10) & 0x1F
    iv_spd     = (iv_raw >> 15) & 0x1F
    iv_spa     = (iv_raw >> 20) & 0x1F
    iv_spd2    = (iv_raw >> 25) & 0x1F
    is_egg     = bool((iv_raw >> 30) & 1)

    ot_name    = decode_gen5_string(raw[176:], 12)
    level      = raw[221]

    GEN6_GAMES = {
        24: 'X', 25: 'Y',
        26: 'Alpha Sapphire', 27: 'Omega Ruby',
    }
    origin_game = GEN6_GAMES.get(raw[223], f'Unknown (0x{raw[223]:02X})')
    shiny       = ((ot_id ^ ot_sid ^ (pv >> 16) ^ (pv & 0xFFFF)) < 8)

    return {
        "filename": "",
        "generation": 6,
        "origin_game": origin_game,
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "level": level,
        "nature": nature,
        "shiny": shiny,
        "is_egg": is_egg,
        "experience": exp,
        "friendship": friendship,
        "moves": list(moves),
        "pp": list(pp),
        "ivs": {
            "hp": iv_hp, "attack": iv_atk, "defense": iv_def,
            "speed": iv_spd, "sp_atk": iv_spa, "sp_def": iv_spd2
        },
        "evs": {
            "hp": ev_hp, "attack": ev_atk, "defense": ev_def,
            "speed": ev_spd, "sp_atk": ev_spa, "sp_def": ev_spd2
        },
        "held_item_id": held_item,
    }


# ---------------------------------------------------------------------------
# Gen 3 parser (.pk3 — 100 bytes, unencrypted from PKHeX export)
# ---------------------------------------------------------------------------

NATURES_GEN3 = [
    "Hardy","Lonely","Brave","Adamant","Naughty",
    "Bold","Docile","Relaxed","Impish","Lax",
    "Timid","Hasty","Serious","Jolly","Naive",
    "Modest","Mild","Quiet","Bashful","Rash",
    "Calm","Gentle","Sassy","Careful","Quirky"
]

def decode_gen3_string(data):
    GEN3_CHAR_MAP = {
        0xBB: 'A', 0xBC: 'B', 0xBD: 'C', 0xBE: 'D', 0xBF: 'E',
        0xC0: 'F', 0xC1: 'G', 0xC2: 'H', 0xC3: 'I', 0xC4: 'J',
        0xC5: 'K', 0xC6: 'L', 0xC7: 'M', 0xC8: 'N', 0xC9: 'O',
        0xCA: 'P', 0xCB: 'Q', 0xCC: 'R', 0xCD: 'S', 0xCE: 'T',
        0xCF: 'U', 0xD0: 'V', 0xD1: 'W', 0xD2: 'X', 0xD3: 'Y',
        0xD4: 'Z', 0xD5: 'a', 0xD6: 'b', 0xD7: 'c', 0xD8: 'd',
        0xD9: 'e', 0xDA: 'f', 0xDB: 'g', 0xDC: 'h', 0xDD: 'i',
        0xDE: 'j', 0xDF: 'k', 0xE0: 'l', 0xE1: 'm', 0xE2: 'n',
        0xE3: 'o', 0xE4: 'p', 0xE5: 'q', 0xE6: 'r', 0xE7: 's',
        0xE8: 't', 0xE9: 'u', 0xEA: 'v', 0xEB: 'w', 0xEC: 'x',
        0xED: 'y', 0xEE: 'z', 0x00: ' ', 0xF0: '0', 0xF1: '1',
        0xF2: '2', 0xF3: '3', 0xF4: '4', 0xF5: '5', 0xF6: '6',
        0xF7: '7', 0xF8: '8', 0xF9: '9', 0xAB: '!', 0xAC: '?',
        0xFF: None  # terminator
    }
    result = []
    for byte in data:
        if byte == 0xFF:
            break
        ch = GEN3_CHAR_MAP.get(byte)
        if ch:
            result.append(ch)
    return ''.join(result).strip()

def parse_pk3(data: bytes) -> dict:
    """Parse a PKHeX-exported .pk3 file.
    PKHeX exports substructures already decrypted and unshuffled in canonical order:
      Bytes 32-43: Sub A — species, item, exp, friendship
      Bytes 44-55: Sub B — moves, PP
      Bytes 56-67: Sub C — EVs
      Bytes 68-79: Sub D — IVs, ribbons, origin info
      Bytes 80-99: Battle stats (level, status, current HP etc.)
    """
    if len(data) < 100:
        return None

    pv     = struct.unpack_from('<I', data, 0)[0]
    ot_id  = struct.unpack_from('<H', data, 4)[0]
    ot_sid = struct.unpack_from('<H', data, 6)[0]

    # Sub A
    species   = struct.unpack_from('<H', data, 32)[0]
    if species == 0 or species > 493:
        return None
    item_held  = struct.unpack_from('<H', data, 34)[0]
    exp        = struct.unpack_from('<I', data, 36)[0]
    friendship = data[41]

    # Sub B
    moves = struct.unpack_from('<4H', data, 44)
    pp    = struct.unpack_from('<4B', data, 52)

    # Sub C — EVs
    ev_hp   = data[56]; ev_atk = data[57]; ev_def  = data[58]
    ev_spd  = data[59]; ev_spa = data[60]; ev_spd2 = data[61]

    # Sub D — IVs at byte 0x48 (72), confirmed from real file
    iv_raw  = struct.unpack_from('<I', data, 72)[0]
    iv_hp   = (iv_raw >> 0)  & 0x1F
    iv_atk  = (iv_raw >> 5)  & 0x1F
    iv_def  = (iv_raw >> 10) & 0x1F
    iv_spd  = (iv_raw >> 15) & 0x1F
    iv_spa  = (iv_raw >> 20) & 0x1F
    iv_spd2 = (iv_raw >> 25) & 0x1F
    is_egg  = bool((iv_raw >> 30) & 1)

    # Origin word at byte 0x46 (70): bits 0-6 = met location, bits 7-10 = game ID
    # Confirmed from real file: word=0x2205, bits 7-10 = 4 = FireRed
    origin_word    = struct.unpack_from('<H', data, 0x46)[0]
    origin_game_id = (origin_word >> 7) & 0xF
    GEN3_GAMES = {
        1: "Sapphire", 2: "Ruby",      3: "Emerald",
        4: "FireRed",  5: "LeafGreen",
        15: "Colosseum", 16: "XD",
    }
    origin_game = GEN3_GAMES.get(origin_game_id, f"Unknown (id={origin_game_id})")

    nature = NATURES_GEN3[pv % 25]
    shiny  = ((ot_id ^ ot_sid ^ (pv >> 16) ^ (pv & 0xFFFF)) < 8)

    nickname  = decode_gen3_string(data[8:18])
    ot_name   = decode_gen3_string(data[20:27])
    level_raw = data[84] if len(data) > 84 else 0

    return {
        "filename": "",
        "generation": 3,
        "origin_game": origin_game,
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "level": level_raw,
        "nature": nature,
        "shiny": shiny,
        "is_egg": is_egg,
        "experience": exp,
        "friendship": friendship,
        "moves": list(moves),
        "pp": list(pp),
        "ivs": {
            "hp": iv_hp, "attack": iv_atk, "defense": iv_def,
            "speed": iv_spd, "sp_atk": iv_spa, "sp_def": iv_spd2
        },
        "evs": {
            "hp": ev_hp, "attack": ev_atk, "defense": ev_def,
            "speed": ev_spd, "sp_atk": ev_spa, "sp_def": ev_spd2
        },
        "held_item_id": item_held,
    }

# ---------------------------------------------------------------------------
# Gen 4 parser (.pk4 — 236 bytes, encrypted data block from PKHeX export)
# ---------------------------------------------------------------------------

NATURES_GEN4 = NATURES_GEN3  # same list

def decode_gen4_string(data: bytes, max_len: int) -> str:
    """Gen4 uses a custom 2-byte encoding. A=0x012B, a=0x0145, 0xFFFF=terminator."""
    GEN4_CHARS = {}
    for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        GEN4_CHARS[0x012B + i] = c
    for i, c in enumerate('abcdefghijklmnopqrstuvwxyz'):
        GEN4_CHARS[0x0145 + i] = c
    GEN4_CHARS[0x0121] = ' '
    chars = []
    for i in range(0, max_len * 2, 2):
        if i + 1 >= len(data): break
        code = struct.unpack_from('<H', data, i)[0]
        if code == 0xFFFF: break
        ch = GEN4_CHARS.get(code, '')
        if ch: chars.append(ch)
    return ''.join(chars).strip()

def decode_gen5_string(data: bytes, max_len: int) -> str:
    """Gen5 uses standard UTF-16LE, terminated by 0xFFFF."""
    chars = []
    for i in range(0, max_len * 2, 2):
        if i + 1 >= len(data): break
        code = struct.unpack_from('<H', data, i)[0]
        if code == 0xFFFF: break
        if code != 0:
            try: chars.append(chr(code))
            except: pass
    return ''.join(chars).strip()

def level_from_exp(exp: int, growth: str = 'slow') -> int:
    """Derive level from EXP. Defaults to Slow (most legendaries).
    Growth rate is fetched from PokéAPI species data when available."""
    for lv in range(1, 100):
        if growth == 'slow':
            nxt = int(5 * (lv + 1) ** 3 / 4)
        elif growth == 'fast':
            nxt = int(4 * (lv + 1) ** 3 / 5)
        elif growth == 'medium-slow':
            n = lv + 1
            nxt = max(0, int(6*n**3/5 - 15*n**2 + 100*n - 140))
        else:  # medium-fast default
            nxt = (lv + 1) ** 3
        if exp < nxt:
            return lv
    return 100

NATURES_GEN4 = NATURES_GEN3  # same list

def parse_pk4(raw: bytes) -> dict:
    """Parse a PKHeX-exported .pk4 file.

    PKHeX exports .pk4 files already decrypted and unshuffled — same as .pk3.
    NO decryption is needed. Read fixed offsets directly.

    Two formats detected by file size:
    BOX format (136 bytes) — confirmed from real Pearl Palkia file:
      0-3:   PID
      6-7:   checksum (unused — file already decrypted)
      Block A (8-39):
        8:   species (uint16)
        10:  held item (uint16)
        12:  OT ID (uint16)
        14:  OT SID (uint16)
        16:  EXP (uint32)
        20:  friendship (uint8)
        22:  ability index (uint8)
      Block B (40-71):
        40:  moves 1-4 (4 × uint16)
        48:  PP 1-4 (4 × uint8)
      Block C (72-103):
        72:  nickname (11 × uint16, Gen4 encoding, 0xFFFF terminated)
      Block D (104-135):
        104: OT name (7 × uint16, Gen4 encoding, 0xFFFF terminated)
        128: IV word (packed uint32)
      Level: derived from EXP (no battle stats block in box format)

    PARTY format (236 bytes):
      Same layout as box, plus battle stats block (bytes 136-235):
        140: level (uint8)
    """
    if len(raw) < 136:
        return None

    pv         = struct.unpack_from('<I', raw, 0)[0]
    species    = struct.unpack_from('<H', raw, 8)[0]
    if species == 0 or species > 493:
        return None

    held_item  = struct.unpack_from('<H', raw, 10)[0]
    ot_id      = struct.unpack_from('<H', raw, 12)[0]
    ot_sid     = struct.unpack_from('<H', raw, 14)[0]
    exp        = struct.unpack_from('<I', raw, 16)[0]
    friendship = raw[20]
    ability_idx= raw[22]

    moves      = struct.unpack_from('<4H', raw, 40)
    pp         = struct.unpack_from('<4B', raw, 48)

    nickname   = decode_gen5_string(raw[72:], 11)
    ot_name    = decode_gen5_string(raw[104:], 7)

    # EVs at bytes 30-35 (confirmed from Porygon/Platinum, Chatot/Diamond, Palkia/Pearl)
    ev_hp  = raw[30]; ev_atk = raw[31]; ev_def = raw[32]
    ev_spd = raw[33]; ev_spa = raw[34]; ev_spd2= raw[35]

    iv_raw     = struct.unpack_from('<I', raw, 128)[0]
    iv_hp      = (iv_raw >> 0)  & 0x1F
    iv_atk     = (iv_raw >> 5)  & 0x1F
    iv_def     = (iv_raw >> 10) & 0x1F
    iv_spd     = (iv_raw >> 15) & 0x1F
    iv_spa     = (iv_raw >> 20) & 0x1F
    iv_spd2    = (iv_raw >> 25) & 0x1F
    is_egg     = bool((iv_raw >> 30) & 1)

    nature     = NATURES_GEN4[pv % 25]
    shiny      = ((ot_id ^ ot_sid ^ (pv >> 16) ^ (pv & 0xFFFF)) < 8)

    # Level: use battle stats block if party format, otherwise derive from EXP
    if len(raw) >= 236:
        level = raw[140]
        level_from_exp_flag = False
    else:
        level = level_from_exp(exp, 'medium-fast')  # corrected after API fetch
        level_from_exp_flag = True

    # Origin game at byte 95 (confirmed across Platinum, Diamond, Pearl files)
    GEN4_GAMES = {
        1:'Sapphire', 2:'Ruby', 3:'Emerald', 4:'FireRed', 5:'LeafGreen',
        7:'HeartGold', 8:'SoulSilver', 10:'Diamond', 11:'Pearl', 12:'Platinum',
        15:'Colosseum', 16:'XD',
    }
    origin_game = GEN4_GAMES.get(raw[95], f'Unknown (0x{raw[95]:02X})')

    return {
        "filename": "",
        "generation": 4,
        "origin_game": origin_game,
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "level": level,
        "level_from_exp": level_from_exp_flag,
        "nature": nature,
        "shiny": shiny,
        "is_egg": is_egg,
        "experience": exp,
        "friendship": friendship,
        "ability_index": ability_idx,
        "moves": list(moves),
        "pp": list(pp),
        "ivs": {
            "hp": iv_hp, "attack": iv_atk, "defense": iv_def,
            "speed": iv_spd, "sp_atk": iv_spa, "sp_def": iv_spd2
        },
        "evs": {
            "hp": ev_hp, "attack": ev_atk, "defense": ev_def,
            "speed": ev_spd, "sp_atk": ev_spa, "sp_def": ev_spd2
        },
        "held_item_id": held_item,
    }


# ---------------------------------------------------------------------------
# Gen 5 parser (.pk5 — 220 bytes, same encryption as Gen 4)
# ---------------------------------------------------------------------------
# Gen 5 uses identical LCRNG decryption and block shuffle as Gen 4.
# Key differences from Gen 4:
#   - File is 220 bytes (battle stats block is 84 bytes, not 100)
#   - Species up to 649
#   - Nature stored explicitly at Block A offset 0x14 (abs 28), not derived from PV
#   - Different game origin IDs
#   - Nickname/OT string offsets slightly different in Block C

def parse_pk5(raw: bytes) -> dict:
    """Parse a PKHeX-exported .pk5 file.

    Like .pk4, PKHeX exports .pk5 already decrypted and unshuffled.
    Same block layout as pk4 with one key difference:
    Nature is stored explicitly at Block A byte 20 (abs offset 28),
    not derived from PID % 25.
    Species range: 1-649.

    File sizes: 136 bytes (box) or 220 bytes (party, includes battle stats).
    """
    if len(raw) < 136:
        return None

    pv         = struct.unpack_from('<I', raw, 0)[0]
    species    = struct.unpack_from('<H', raw, 8)[0]
    if species == 0 or species > 649:
        return None

    held_item  = struct.unpack_from('<H', raw, 10)[0]
    ot_id      = struct.unpack_from('<H', raw, 12)[0]
    ot_sid     = struct.unpack_from('<H', raw, 14)[0]
    exp        = struct.unpack_from('<I', raw, 16)[0]
    friendship = raw[20]
    ability_idx= raw[22]
    nature_id  = raw[28]
    nature     = NATURES_GEN3[nature_id % 25]

    moves      = struct.unpack_from('<4H', raw, 40)
    pp         = struct.unpack_from('<4B', raw, 48)

    nickname   = decode_gen4_string(raw[72:], 11)
    ot_name    = decode_gen4_string(raw[104:], 7)

    iv_raw     = struct.unpack_from('<I', raw, 128)[0]
    iv_hp      = (iv_raw >> 0)  & 0x1F
    iv_atk     = (iv_raw >> 5)  & 0x1F
    iv_def     = (iv_raw >> 10) & 0x1F
    iv_spd     = (iv_raw >> 15) & 0x1F
    iv_spa     = (iv_raw >> 20) & 0x1F
    iv_spd2    = (iv_raw >> 25) & 0x1F
    is_egg     = bool((iv_raw >> 30) & 1)

    shiny      = ((ot_id ^ ot_sid ^ (pv >> 16) ^ (pv & 0xFFFF)) < 8)

    # Battle stats block is zeroed in PKHeX pk5 exports — always derive from EXP
    # Growth rate corrected post-API fetch in scan_directory
    level = level_from_exp(exp, 'medium-fast')

    # EVs at same offsets as Gen 4 (same block layout)
    ev_hp  = raw[30]; ev_atk = raw[31]; ev_def = raw[32]
    ev_spd = raw[33]; ev_spa = raw[34]; ev_spd2= raw[35]

    # Origin game at byte 95 — same as Gen 4 (unverified for Gen 5, assumed same)
    GEN5_GAMES = {
        20:'White', 21:'Black', 22:'White 2', 23:'Black 2',
        7:'HeartGold', 8:'SoulSilver', 10:'Diamond', 11:'Pearl', 12:'Platinum',
    }
    origin_game = GEN5_GAMES.get(raw[95], f'Unknown (0x{raw[95]:02X})')

    return {
        "filename": "",
        "generation": 5,
        "origin_game": origin_game,
        "species_id": species,
        "nickname": nickname,
        "ot_name": ot_name,
        "ot_id": ot_id,
        "level": level,
        "level_from_exp": True,
        "nature": nature,
        "shiny": shiny,
        "is_egg": is_egg,
        "experience": exp,
        "friendship": friendship,
        "ability_index": ability_idx,
        "moves": list(moves),
        "pp": list(pp),
        "ivs": {
            "hp": iv_hp, "attack": iv_atk, "defense": iv_def,
            "speed": iv_spd, "sp_atk": iv_spa, "sp_def": iv_spd2
        },
        "evs": {
            "hp": ev_hp, "attack": ev_atk, "defense": ev_def,
            "speed": ev_spd, "sp_atk": ev_spa, "sp_def": ev_spd2
        },
        "held_item_id": held_item,
    }


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------

def scan_directory(directory: str, recursive: bool = False):
    cache = load_cache()
    notes = load_notes()
    results = []
    errors = []

    VALID_EXTS = {'.pk1', '.pk2', '.pk3', '.pk4', '.pk5', '.pk6', '.pk7'}

    # Collect all files to scan — flat or recursive
    all_files = []
    if recursive:
        for root, dirs, files in os.walk(directory):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in VALID_EXTS:
                    all_files.append((fname, os.path.join(root, fname)))
    else:
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            if os.path.isdir(fpath):
                continue
            ext = os.path.splitext(fname)[1].lower()
            if ext in VALID_EXTS:
                all_files.append((fname, fpath))

    for fname, fpath in all_files:

        try:
            ext = os.path.splitext(fname)[1].lower()
            with open(fpath, 'rb') as f:
                raw = f.read()

            if ext == '.pk1':
                poke = parse_pk1(raw)
            elif ext == '.pk2':
                poke = parse_pk2(raw)
            elif ext == '.pk3':
                poke = parse_pk3(raw)
            elif ext == '.pk4':
                poke = parse_pk4(raw)
            elif ext == '.pk5':
                poke = parse_pk5(raw)
            elif ext == '.pk6':
                poke = parse_pk6(raw)
            elif ext == '.pk7':
                poke = parse_pk7(raw)
            else:
                continue

            if poke is None:
                errors.append({"file": fname, "reason": "Parse returned null (invalid or empty slot)"})
                continue

            poke["filename"] = fname

            # Enrich species from PokéAPI
            api_data = fetch_pokemon_data(poke["species_id"], cache)
            poke["api"] = api_data or None

            # For Gen 4/5 box format, level was derived from EXP using a default
            # growth rate. Now that we have the real growth rate from PokéAPI,
            # recalculate with the correct value.
            if poke.get("level_from_exp") and api_data:
                growth = api_data.get("growth_rate", "medium-fast")
                poke["level"] = level_from_exp(poke["experience"], growth)

            # Enrich ability descriptions, attach to species entry, persist to cache
            if api_data:
                species_key = str(poke["species_id"])
                needs_save = False
                for ab in api_data.get("abilities", []):
                    if "description" not in ab:
                        ab["description"] = (fetch_ability_data(ab["name"], cache) or {}).get("effect", "")
                        needs_save = True
                    else:
                        fetch_ability_data(ab["name"], cache)  # keep ability cache warm
                if needs_save:
                    cache[species_key] = api_data
                    save_cache(cache)

            # Enrich moves from PokéAPI (cached per move ID)
            poke["moves_data"] = enrich_moves(poke.get("moves", []), cache)

            # Enrich held item — translate Gen2/3 IDs to PokéAPI slugs first
            raw_item_id = poke.get("held_item_id", 0)
            translated = translate_item_id(raw_item_id, poke.get("generation", 4))
            poke["held_item"] = fetch_item_data(translated, cache) if translated else None

            # Enrich evolution chain (cached per species)
            poke["evo_chain"] = fetch_evo_chain(poke["species_id"], cache)

            # Attach notes/tags for this specific file
            note_data = notes.get(fname, {})
            poke["note"]      = note_data.get("note", "")
            poke["tags"]      = note_data.get("tags", [])
            poke["favourite"] = note_data.get("favourite", False)

            results.append(poke)

        except Exception as e:
            errors.append({"file": fname, "reason": str(e)})

    return results, errors

# ---------------------------------------------------------------------------
# Flask routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cached-image/<filename>")
def cached_image(filename):
    from flask import send_from_directory
    return send_from_directory(IMAGE_DIR, filename)

@app.route("/api/browse")
def browse_directory():
    """Open a native OS folder picker dialog via tkinter and return the chosen path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', True)
        chosen = filedialog.askdirectory(title="Select your Pokémon folder")
        root.destroy()
        if chosen:
            # tkinter on Windows sometimes wraps paths with spaces in {curly braces}
            chosen = chosen.strip('{}')
            return jsonify({"dir": chosen})
        return jsonify({"dir": None})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

LAST_DIR_FILE = os.path.join(CACHE_DIR, "last_dir.txt")

@app.route("/api/last-dir")
def get_last_dir():
    """Return the last successfully scanned directory."""
    if os.path.exists(LAST_DIR_FILE):
        with open(LAST_DIR_FILE, "r", encoding="utf-8") as f:
            return jsonify({"dir": f.read().strip()})
    return jsonify({"dir": None})

@app.route("/api/last-dir", methods=["POST"])
def set_last_dir():
    """Save the last scanned directory."""
    body = request.get_json(silent=True) or {}
    d = body.get("dir", "").strip()
    if d:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(LAST_DIR_FILE, "w", encoding="utf-8") as f:
            f.write(d)
    return jsonify({"ok": True})

@app.route("/api/scan", methods=["POST"])
def api_scan():
    body = request.get_json(silent=True) or {}
    directory = body.get("dir", "").strip()
    recursive = bool(body.get("recursive", False))
    if not directory:
        return jsonify({"error": "No directory provided"}), 400
    directory = directory.replace("/", os.sep)
    if not os.path.isdir(directory):
        return jsonify({"error": f"Directory not found: {directory}"}), 404

    pokemon, errors = scan_directory(directory, recursive)
    return jsonify({"pokemon": pokemon, "errors": errors, "count": len(pokemon)})

@app.route("/api/cache-info")
def cache_info():
    """Return stats about the local cache."""
    json_size = os.path.getsize(CACHE_FILE) if os.path.exists(CACHE_FILE) else 0
    images = os.listdir(IMAGE_DIR) if os.path.exists(IMAGE_DIR) else []
    img_size = sum(os.path.getsize(os.path.join(IMAGE_DIR, f)) for f in images)
    return jsonify({
        "json_kb":    round(json_size / 1024, 1),
        "images":     len(images),
        "images_kb":  round(img_size / 1024, 1),
    })

@app.route("/api/clear-cache", methods=["POST"])
def clear_cache():
    import shutil
    if os.path.exists(CACHE_DIR):
        shutil.rmtree(CACHE_DIR)
    os.makedirs(IMAGE_DIR, exist_ok=True)
    return jsonify({"ok": True})

@app.route("/api/notes", methods=["POST"])
def save_note():
    """Save note and tags for a specific pokemon file (variant)."""
    body = request.get_json()
    filename = body.get("filename", "").strip()
    if not filename:
        return jsonify({"error": "filename required"}), 400
    notes = load_notes()
    notes[filename] = {
        "note":      body.get("note", ""),
        "tags":      body.get("tags", []),
        "favourite": body.get("favourite", False),
    }
    save_notes(notes)
    return jsonify({"ok": True})

@app.route("/api/notes/<filename>")
def get_note(filename):
    notes = load_notes()
    return jsonify(notes.get(filename, {"note": "", "tags": []}))

@app.route("/api/export-csv", methods=["POST"])
def export_csv():
    """Export full collection as CSV, letting user choose save location via tkinter dialog."""
    import csv
    from datetime import date
    body = request.get_json(silent=True) or {}
    pokemon = body.get("pokemon", [])
    if not pokemon:
        return jsonify({"error": "No pokemon data provided"}), 400

    # Ask user where to save
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', True)
        today = date.today().strftime("%Y-%m-%d")
        out_path = filedialog.asksaveasfilename(
            title="Save Pokédex export",
            initialfile=f"{today}-pokedex_export.csv",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        root.destroy()
    except Exception as e:
        return jsonify({"error": f"Save dialog failed: {e}"}), 500

    if not out_path:
        return jsonify({"cancelled": True})

    notes = load_notes()
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Filename", "Species", "Dex#", "Nickname", "Generation",
            "Level", "Nature", "Shiny", "OT", "OT_ID",
            "Type1", "Type2",
            "HP_Base", "Atk_Base", "Def_Base", "SpAtk_Base", "SpDef_Base", "Spd_Base",
            "HP_IV", "Atk_IV", "Def_IV", "SpAtk_IV", "SpDef_IV", "Spd_IV",
            "HP_EV", "Atk_EV", "Def_EV", "SpAtk_EV", "SpDef_EV", "Spd_EV",
            "Move1", "Move2", "Move3", "Move4",
            "Held Item", "Note", "Tags", "Favourite"
        ])
        for p in pokemon:
            api   = p.get("api") or {}
            types = api.get("types", [])
            base  = api.get("base_stats", {})
            ivs   = p.get("ivs", {})
            evs   = p.get("evs", {})
            moves = [(m["name"] if m else "") for m in (p.get("moves_data") or [])]
            while len(moves) < 4: moves.append("")
            held  = (p.get("held_item") or {}).get("name", "")
            nd    = notes.get(p.get("filename", ""), {})
            writer.writerow([
                p.get("filename",""), api.get("name", f'#{p["species_id"]}'), p.get("species_id",""),
                p.get("nickname",""), p.get("generation",""),
                p.get("level",""), p.get("nature",""), p.get("shiny", False),
                p.get("ot_name",""), p.get("ot_id",""),
                types[0] if len(types)>0 else "", types[1] if len(types)>1 else "",
                base.get("hp",""), base.get("attack",""), base.get("defense",""),
                base.get("special-attack",""), base.get("special-defense",""), base.get("speed",""),
                ivs.get("hp",""), ivs.get("attack",""), ivs.get("defense",""),
                ivs.get("sp_atk",""), ivs.get("sp_def",""), ivs.get("speed",""),
                evs.get("hp",""), evs.get("attack",""), evs.get("defense",""),
                evs.get("sp_atk",""), evs.get("sp_def",""), evs.get("speed",""),
                moves[0], moves[1], moves[2], moves[3],
                held,
                nd.get("note",""), "|".join(nd.get("tags",[])), nd.get("favourite", False)
            ])

    return jsonify({"ok": True, "path": out_path})

if __name__ == "__main__":
    print("Pokédex running at http://localhost:5000")
    app.run(debug=True, port=5000)

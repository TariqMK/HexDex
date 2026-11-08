"""Tests for the .pk1-.pk7 file parsers, using small synthetic files built to PKHeX's layouts."""
import os
import struct
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app  # noqa: E402


def pack_ivs(hp, atk, de, spe, spa, spd, egg=False):
    """Pack six IVs into the 32-bit word used by Gen 3-7 files."""
    word = hp | atk << 5 | de << 10 | spe << 15 | spa << 20 | spd << 25
    return word | (1 << 30 if egg else 0)


def utf16_name(text, length_chars, terminator=0xFFFF, trash=""):
    """Encode a UTF-16LE name, its terminator, then optional leftover 'trash' characters."""
    codes = [ord(c) for c in text] + [terminator] + [ord(c) for c in trash]
    codes += [0] * (length_chars - len(codes))
    return struct.pack(f"<{length_chars}H", *codes[:length_chars])


def gen4_name(text, length_chars):
    """Encode a name in the Gen 4 character set (letters only)."""
    codes = [(0x012B + ord(c) - 65) if c.isupper() else (0x0145 + ord(c) - 97) for c in text]
    codes += [0xFFFF] + [0] * (length_chars - len(codes) - 1)
    return struct.pack(f"<{length_chars}H", *codes)


class Gen4Tests(unittest.TestCase):
    def build(self, size=236):
        raw = bytearray(size)
        struct.pack_into("<I", raw, 0x00, 0x12345678)
        struct.pack_into("<H", raw, 0x08, 248)          # Tyranitar
        struct.pack_into("<I", raw, 0x10, 1_250_000)    # EXP
        raw[0x18:0x1E] = bytes([33, 68, 84, 128, 98, 51])  # EVs
        struct.pack_into("<I", raw, 0x38, pack_ivs(31, 30, 29, 28, 27, 26))
        raw[0x48:0x48 + 22] = gen4_name("Tyra", 11)
        raw[0x5F] = 7                                   # HeartGold
        raw[0x68:0x68 + 16] = gen4_name("Ash", 8)
        # Block D after the OT name: met location, Pokerus and ball.
        # The old parser read IVs from here.
        struct.pack_into("<H", raw, 0x80, 0x00B4)
        raw[0x82] = 0x00
        raw[0x83] = 0x04
        if size >= 236:
            raw[0x8C] = 55
        return bytes(raw)

    def test_ivs_come_from_block_b(self):
        poke = app.parse_pk4(self.build())
        self.assertEqual(poke["ivs"], {"hp": 31, "attack": 30, "defense": 29,
                                       "speed": 28, "sp_atk": 27, "sp_def": 26})
        self.assertFalse(poke["is_egg"])

    def test_egg_flag_comes_from_iv_word(self):
        raw = bytearray(self.build())
        struct.pack_into("<I", raw, 0x38, pack_ivs(1, 2, 3, 4, 5, 6, egg=True))
        self.assertTrue(app.parse_pk4(bytes(raw))["is_egg"])

    def test_existing_fields_unchanged(self):
        poke = app.parse_pk4(self.build())
        self.assertEqual(poke["species_id"], 248)
        self.assertEqual(poke["level"], 55)
        self.assertEqual(poke["nickname"], "Tyra")
        self.assertEqual(poke["ot_name"], "Ash")
        self.assertEqual(poke["origin_game"], "HeartGold")
        self.assertEqual(poke["evs"]["attack"], 68)


class Gen5Tests(unittest.TestCase):
    def build(self):
        raw = bytearray(220)
        struct.pack_into("<I", raw, 0x00, 0x0BADF00D)
        struct.pack_into("<H", raw, 0x08, 570)          # Zorua
        struct.pack_into("<I", raw, 0x10, 125_000)      # Lv 50 on the medium-slow curve
        raw[0x18:0x1E] = bytes([4, 252, 0, 252, 0, 0])  # EVs
        raw[0x1E:0x24] = bytes([10, 20, 30, 40, 50, 60])  # contest stats, not EVs
        struct.pack_into("<I", raw, 0x38, pack_ivs(31, 31, 31, 31, 31, 31))
        raw[0x41] = 15                                  # Modest
        raw[0x48:0x48 + 22] = utf16_name("Zorua", 11)
        raw[0x5F] = 21                                  # Black
        raw[0x68:0x68 + 16] = utf16_name("Ash", 8)
        return bytes(raw)

    def test_nature_comes_from_0x41(self):
        self.assertEqual(app.parse_pk5(self.build())["nature"], "Modest")

    def test_evs_come_from_0x18(self):
        evs = app.parse_pk5(self.build())["evs"]
        self.assertEqual(evs, {"hp": 4, "attack": 252, "defense": 0,
                               "speed": 252, "sp_atk": 0, "sp_def": 0})

    def test_ivs_come_from_block_b(self):
        self.assertEqual(set(app.parse_pk5(self.build())["ivs"].values()), {31})

    def test_names_are_utf16(self):
        poke = app.parse_pk5(self.build())
        self.assertEqual(poke["nickname"], "Zorua")
        self.assertEqual(poke["ot_name"], "Ash")


class Gen67Tests(unittest.TestCase):
    def build(self, parser_size, met_level=5, female_ot=True, exp=125_000, nickname=("Bob", "")):
        raw = bytearray(parser_size)
        struct.pack_into("<H", raw, 0x08, 6)            # Charizard
        struct.pack_into("<I", raw, 0x10, exp)
        raw[0x1C] = 3                                   # Adamant
        raw[0x40:0x40 + 24] = utf16_name(nickname[0], 12, terminator=0x0000, trash=nickname[1])
        struct.pack_into("<I", raw, 0x74, pack_ivs(1, 2, 3, 4, 5, 6))
        raw[0xB0:0xB0 + 24] = utf16_name("Ash", 12, terminator=0x0000)
        raw[0xDD] = (0x80 if female_ot else 0) | met_level
        raw[0xDF] = 24                                  # X
        if parser_size >= 260:
            raw[0xEC] = 50
        return bytes(raw)

    def test_party_level_comes_from_battle_stats(self):
        for parse in (app.parse_pk6, app.parse_pk7):
            self.assertEqual(parse(self.build(260))["level"], 50)

    def test_box_level_is_not_met_level(self):
        # Met at Lv 5 by a female trainer: the old parser showed 133 (0x80 | 5).
        for parse in (app.parse_pk6, app.parse_pk7):
            poke = parse(self.build(232))
            self.assertTrue(poke["level_from_exp"])
            self.assertEqual(poke["level"], 50)       # 125,000 EXP on the default curve

    def test_nickname_stops_at_terminator(self):
        # Leftover characters after the 0x0000 terminator must not be shown.
        for parse in (app.parse_pk6, app.parse_pk7):
            self.assertEqual(parse(self.build(232, nickname=("Bob", "izard")))["nickname"], "Bob")


class Gen2Tests(unittest.TestCase):
    def build_party_list(self, level=40):
        """PKHeX .pk2 list format: count, species, 0xFF, 48-byte party struct, OT, nickname."""
        core = bytearray(48)
        core[0x00] = 130                                # Gyarados
        core[0x01] = 0x12                               # held item
        core[0x02:0x06] = bytes([44, 55, 82, 63])       # moves
        struct.pack_into(">H", core, 0x06, 12345)       # OT ID
        core[0x08:0x0B] = (64_000).to_bytes(3, "big")   # EXP
        struct.pack_into(">H", core, 0x15, 0xAAAA)      # DVs (shiny pattern)
        core[0x17:0x1B] = bytes([25, 15, 5, 10])        # PP
        core[0x1B] = 200                                # friendship
        core[0x1F] = level
        ot = bytes([0x80, 0x92, 0x87, 0x50]) + bytes(7)          # "ASH"
        nick = bytes([0x86, 0x98, 0x80, 0x50]) + bytes(7)        # "GYA"
        return bytes([0x01, 130, 0xFF]) + bytes(core) + ot + nick

    def test_party_list_fields(self):
        poke = app.parse_pk2(self.build_party_list())
        self.assertEqual(poke["species_id"], 130)
        self.assertEqual(poke["level"], 40)
        self.assertEqual(poke["moves"], [44, 55, 82, 63])
        self.assertEqual(poke["ot_id"], 12345)
        self.assertEqual(poke["experience"], 64_000)
        self.assertEqual(poke["friendship"], 200)
        self.assertEqual(poke["held_item_id"], 0x12)
        self.assertEqual(poke["pp"], [25, 15, 5, 10])
        self.assertTrue(poke["shiny"])
        self.assertEqual(poke["ot_name"], "ASH")
        self.assertEqual(poke["nickname"], "GYA")


class Gen2ItemTests(unittest.TestCase):
    """Gen 2 item IDs follow PKHeX's text_ItemsG2_en list."""

    def test_ids_map_to_the_right_pokeapi_items(self):
        self.assertEqual(app.translate_item_id(3, 2), "bright-powder")
        self.assertEqual(app.translate_item_id(105, 2), "stick")
        self.assertEqual(app.translate_item_id(146, 2), "leftovers")
        self.assertEqual(app.translate_item_id(172, 2), "up-grade")

    def test_tms_are_not_items(self):
        # 197 and 198 are TM06 and TM07, not Oran and Sitrus Berry.
        self.assertIsNone(app.translate_item_id(197, 2))
        self.assertIsNone(app.translate_item_id(198, 2))

    def test_gen2_only_items_use_their_own_name_without_network(self):
        # The starters' Berry (173) has no PokeAPI entry; it must resolve locally.
        item = app.resolve_held_item(173, 2, cache={})
        self.assertEqual(item["name"], "Berry")
        self.assertIn("10 HP", item["effect"])
        self.assertEqual(app.resolve_held_item(174, 2, cache={})["name"], "Gold Berry")

    def test_no_item(self):
        self.assertIsNone(app.resolve_held_item(0, 2, cache={}))


class OriginalGameItemTests(unittest.TestCase):
    """Held items show the name and description from the file's own game, not today's games."""

    def cache_with(self, slug, flavor):
        return {f"item:{slug}": {"name": "Modern Name", "effect": "Modern effect.", "flavor": flavor}}

    def test_names_use_each_generations_spelling(self):
        cache = {**self.cache_with("bright-powder", {}), **self.cache_with("stick", {})}
        self.assertEqual(app.resolve_held_item(3, 2, cache)["name"], "BrightPowder")
        self.assertEqual(app.resolve_held_item(105, 2, cache)["name"], "Stick")
        self.assertEqual(app.resolve_held_item(179, 3, cache)["name"], "BrightPowder")
        self.assertEqual(app.resolve_held_item(213, 4, cache)["name"], "BrightPowder")
        self.assertEqual(app.resolve_held_item(259, 4, cache)["name"], "Stick")   # "Leek" since Gen 8

    def test_description_comes_from_the_origin_game(self):
        flavor = {"firered-leafgreen": "FRLG text", "platinum": "Pt text",
                  "heartgold-soulsilver": "HGSS text", "sword-shield": "SwSh text"}
        cache = self.cache_with("bright-powder", flavor)
        self.assertEqual(app.resolve_held_item(179, 3, cache, "FireRed")["effect"], "FRLG text")
        self.assertEqual(app.resolve_held_item(213, 4, cache, "HeartGold")["effect"], "HGSS text")
        # A Gen 4 file that came from a Gen 3 game uses a Gen 4 description.
        self.assertEqual(app.resolve_held_item(213, 4, cache, "FireRed")["effect"], "Pt text")
        # No Gen 2 descriptions exist, so the earliest available one is used.
        self.assertEqual(app.resolve_held_item(3, 2, cache)["effect"], "FRLG text")

    def test_falls_back_to_modern_effect_without_old_text(self):
        cache = self.cache_with("bright-powder", {"sword-shield": "SwSh text"})
        self.assertEqual(app.resolve_held_item(213, 4, cache, "Platinum")["effect"], "Modern effect.")

    def test_gen4_orb_ids(self):
        self.assertEqual(app.translate_item_id(112, 4), "griseous-orb")
        self.assertIsNone(app.translate_item_id(113, 4))   # Tea, not an item a Pokémon holds
        self.assertEqual(app.translate_item_id(135, 4), "adamant-orb")


class GenderTests(unittest.TestCase):
    def test_gb_gender_one_in_eight_female(self):
        # PKHeX: female when Attack DV <= gender value >> 4. For 1-in-8 female that is DV 0-1.
        self.assertEqual(app.gb_gender(1, 1), "female")
        self.assertEqual(app.gb_gender(2, 1), "male")

    def test_gb_gender_other_ratios(self):
        self.assertEqual(app.gb_gender(3, 2), "female")
        self.assertEqual(app.gb_gender(4, 2), "male")
        self.assertEqual(app.gb_gender(7, 4), "female")
        self.assertEqual(app.gb_gender(8, 4), "male")
        self.assertEqual(app.gb_gender(11, 6), "female")
        self.assertEqual(app.gb_gender(12, 6), "male")


class LevelFromExpTests(unittest.TestCase):
    # PokeAPI growth-rate names: "slow-then-very-fast" is Erratic, "fast-then-very-slow" is Fluctuating.
    def test_erratic(self):
        self.assertEqual(app.level_from_exp(600_000, "slow-then-very-fast"), 100)
        self.assertEqual(app.level_from_exp(125_000, "slow-then-very-fast"), 50)
        self.assertEqual(app.level_from_exp(124_999, "slow-then-very-fast"), 49)

    def test_fluctuating(self):
        self.assertEqual(app.level_from_exp(1_640_000, "fast-then-very-slow"), 100)
        self.assertEqual(app.level_from_exp(142_500, "fast-then-very-slow"), 50)
        self.assertEqual(app.level_from_exp(142_499, "fast-then-very-slow"), 49)

    def test_existing_curves_unchanged(self):
        self.assertEqual(app.level_from_exp(125_000, "medium"), 50)
        self.assertEqual(app.level_from_exp(1_250_000, "slow"), 100)
        self.assertEqual(app.level_from_exp(800_000, "fast"), 100)
        self.assertEqual(app.level_from_exp(1_059_860, "medium-slow"), 100)


REAL_FILES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Meta", "test-pokemon")
PARSERS = {".pk1": app.parse_pk1, ".pk2": app.parse_pk2, ".pk3": app.parse_pk3, ".pk4": app.parse_pk4,
           ".pk5": app.parse_pk5, ".pk6": app.parse_pk6, ".pk7": app.parse_pk7}


@unittest.skipUnless(os.path.isdir(REAL_FILES_DIR), "Meta/test-pokemon not present (private, local only)")
class RealFileTests(unittest.TestCase):
    """Sanity checks on real PKHeX exports kept in the git-ignored Meta/test-pokemon folder."""

    def test_every_file_parses_to_sane_values(self):
        checked = 0
        for root, _dirs, files in os.walk(REAL_FILES_DIR):
            for name in files:
                parse = PARSERS.get(os.path.splitext(name)[1].lower())
                if not parse:
                    continue
                with open(os.path.join(root, name), "rb") as f:
                    poke = parse(f.read())
                with self.subTest(file=name):
                    self.assertIsNotNone(poke, "parser rejected the file")
                    iv_max = 15 if poke["generation"] <= 2 else 31
                    self.assertTrue(1 <= poke["level"] <= 100, f"level {poke['level']}")
                    self.assertTrue(all(0 <= v <= iv_max for v in poke["ivs"].values()), poke["ivs"])
                    if poke["generation"] >= 3:
                        self.assertIn(poke["nature"], app.NATURES_GEN3)
                        self.assertLessEqual(sum(poke["evs"].values()), 510 + 255, poke["evs"])
                    for field in ("nickname", "ot_name"):
                        self.assertTrue(poke[field].isprintable(), f"{field} {poke[field]!r}")
                    print(f"  {name}: Gen {poke['generation']} #{poke['species_id']} Lv {poke['level']} "
                          f"{poke['nature'] or '-'} IVs {list(poke['ivs'].values())} "
                          f"nick {poke['nickname']!r} OT {poke['ot_name']!r}")
                checked += 1
        self.assertGreater(checked, 0, "no .pk1-.pk7 files found")


if __name__ == "__main__":
    unittest.main()

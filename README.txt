HexDex — Personal Collection Viewer
=====================================
A local desktop app that scans a folder of PKHeX-exported Pokémon files and
displays them as a searchable, filterable collection viewer with full stats,
moves, evolution chains, notes, tags, favourites, held items, gender, and
Serebii links. Opens in its own native desktop window via pywebview (Qt
backend). All API data and artwork is cached locally for offline use after
the first scan.

Can also run as a plain Flask server for browser access — useful for viewing
on other devices (e.g. iPhone) on the same WiFi network.


FILE STRUCTURE
--------------
HexDex/
├── launch.py               # Desktop launcher — opens native pywebview window
├── app.py                  # Flask backend: parsers, API routes, caching
├── requirements.txt        # Python dependencies
├── start.bat               # Windows one-click launcher (double-click to run)
├── diagnose.py             # Hex-dump debug tool for .pk1 through .pk7 files
├── venv/                   # Python virtual environment (you create this once)
├── templates/
│   └── index.html          # Entire frontend: HTML + CSS + JS in a single file
└── cache/                  # Auto-created on first scan
    ├── pokeapi_cache.json  # All PokéAPI data: species, moves, abilities,
    │                       #   evo chains, items, gender rates — cached here
    ├── notes.json          # YOUR DATA: notes, tags, favourites — back this up!
    ├── last_dir.txt        # Last scanned folder path (restored on next launch)
    └── images/             # Cached HD official artwork PNGs
                            #   {id}_hd.png     e.g. 6_hd.png    (normal)
                            #   {id}_shiny.png  e.g. 6_shiny.png (shiny)

How the pieces fit together:
  start.bat    → calls venv Python directly, runs launch.py
  launch.py    → starts Flask (app.py) in background thread, opens pywebview window
  app.py       → serves frontend, parses .pk files, fetches/caches PokéAPI data
  index.html   → entire UI rendered inside the pywebview window (or browser)
  cache/       → all PokéAPI data lives here; fully offline after first scan


REQUIREMENTS
------------
- Python 3.10 or higher (3.12 recommended)
- pip packages: flask, requests, pywebview[qt]
- tkinter — bundled with standard Python on Windows; powers folder/save dialogs
- No .NET Framework required — the Qt backend is used instead of WinForms
- Internet on first scan only — all data cached locally afterwards


INSTALLATION
------------
IMPORTANT: If you have multiple Python projects/venvs on your machine, always
use the full path to install packages to avoid installing into the wrong venv:

1. Place all files and the templates/ folder in one directory.
2. Create a virtual environment:
       python -m venv venv
3. Install dependencies using the full venv path (safest):
       venv\Scripts\python.exe -m pip install flask requests pywebview[qt]
4. Double-click start.bat or run:
       venv\Scripts\python.exe launch.py

Do NOT use plain `pip install` or `python` if another venv is already active
in your terminal — it will install into the wrong environment.

NOTE: Use pywebview[qt] specifically — not plain pywebview. The default
Windows backend (WinForms) requires .NET Framework and pythonnet which causes
"Failed to resolve Python.Runtime.dll" errors on other machines. The Qt
backend has no such dependency and is fully portable.


RUNNING THE APP
---------------
Two ways to run:

  1. DESKTOP WINDOW (default):
     Double-click start.bat, or run:
         venv\Scripts\python.exe launch.py
     Opens HexDex in its own native desktop window via pywebview (Qt backend).

  2. BROWSER MODE:
     Run:
         venv\Scripts\python.exe app.py
     Then open http://localhost:5000 in any browser.
     Also accessible from other devices on the same WiFi network:
         http://YOUR-PC-IP:5000
     (Find your PC's local IP in Settings → Network)
     Useful for iPhone/iPad access without any extra setup.

Port default: 5000. To change, update the PORT constant in launch.py and the
port= argument in app.py consistently.


USAGE
-----
1. The app opens showing your last used folder (auto-restored).
2. Enter your Pokémon folder path:
   a) Click "Browse…" for a native folder picker dialog, or
   b) Paste the full path directly (e.g. D:\OneDrive\My Pokemon)
3. Tick "Subfolders" if you want to scan recursively into subdirectories.
4. Click SCAN.
5. On first scan, PokéAPI data and HD artwork are fetched and cached.
   Subsequent scans load instantly from cache.
6. Click any card to open the detail panel on the right.
7. Press Escape or click ✕ to close the panel.

Filter bar (left to right):
  - Name / nickname text search
  - Type dropdown (all 18 types)
  - Generation filter (Gen 1–7)
  - Sort by: Dex #, Level, Name, Shiny first
  - ⭐ Favourites
  - ✨ Shinies
  - 🌟 Legendaries (includes mythicals, all gens)
  - 🥚 Eggs
  - 🏷 Tags — dropdown of all tags in your collection. Select multiple to
    filter by all simultaneously (AND logic). Active tags shown as removable
    chips. Typing in the tag input shows autocomplete suggestions from your
    existing tags, narrowing as you type. Enter selects if only one match
    remains. Arrow keys navigate suggestions.
  - Subfolders checkbox — scan recursively into subdirectories

Selection mode: click the Select button in the header to enter selection mode.
Click cards to select them (teal outline + checkmark). A floating bar appears
at the bottom — type a tag and click APPLY to add it to all selected Pokémon
at once. Click Done to exit selection mode.

CSV Export: click ⬇ CSV in the header. A native Save As dialog opens,
pre-filled with today's date (e.g. 2026-03-21-hexdex_export.csv).
Export is instant — uses data already in memory. Includes: all stats, IVs,
EVs, moves, held item, gender, notes, tags, favourites.


SUPPORTED FILE FORMATS
----------------------
All files exported from PKHeX as individual slot files. PKHeX pre-decrypts
all formats on export — no decryption needed by this app.

  .pk1  Gen 1 — Red, Blue, Yellow
        Species 1–151. No natures, no abilities, no held items.
        DVs (4-bit, max 15) shown as IVs. Shiny derived from DVs.
        Gender derived from ATK DV + species gender rate (PokéAPI).
        File size: 69 bytes (same format for party and box).

  .pk2  Gen 2 — Gold, Silver, Crystal
        Species 1–251. No natures, no abilities. DVs same as Gen 1.
        Held items supported (translated via Gen 2 item ID table).
        Shiny derived from DVs. Gender derived from ATK DV.
        Egg detection: species byte 0xFD = egg marker; actual hatch
        species stored at byte 0x03.
        Two sizes: 73 bytes (party), 55 bytes (box).

  .pk3  Gen 3 — FireRed, LeafGreen, Ruby, Sapphire, Emerald, Colosseum, XD
        Species 1–386. Full natures, abilities, IVs, EVs, held items.
        Gender derived from PID (not stored explicitly in Gen 3).
        Held items translated via Gen 3 item ID table.
        Egg detection: IV word bit 30.
        File size: 100 bytes.

  .pk4  Gen 4 — Diamond, Pearl, Platinum, HeartGold, SoulSilver
        Species 1–493. Full feature set.
        Gender stored explicitly at byte 0x1D bits 1-2.
        OT name uses Gen 4 custom encoding (A=0x012B), not UTF-16LE.
        Two sizes: 136 bytes (box), 236 bytes (party).
        Level derived from EXP in box format.

  .pk5  Gen 5 — Black, White, Black 2, White 2
        Species 1–649. Same block layout as Gen 4.
        Nature stored explicitly (not PID-derived).
        Gender stored explicitly at byte 0x1D bits 1-2.
        OT name uses UTF-16LE (unlike Gen 4).
        Level always derived from EXP (battle stats block zeroed).

  .pk6  Gen 6 — X, Y, Omega Ruby, Alpha Sapphire
        Species 1–721. Level stored explicitly at byte 221.
        Gender stored explicitly at byte 0x1D bits 1-2.
        Origin game at byte 223: X=24, Y=25, AS=26, OR=27.
        File size: 232 bytes.

  .pk7  Gen 7 — Sun, Moon, Ultra Sun, Ultra Moon
        Species 1–809. Identical layout to pk6.
        Gender stored explicitly at byte 0x1D bits 1-2.
        Origin game at byte 223: Sun=30, Moon=31, US=32, UM=33.
        Also recognises Gen 6 game IDs for Pokémon transferred via
        Pokémon Bank that retain their original game of origin.
        File size: 232 bytes.


FEATURES
--------
Grid view:
  - Responsive card grid, auto-fills available width
  - Shiny cards: animated slow golden diagonal shimmer sweep effect
  - Favourites: gold ⭐ in top-right corner
  - Generation badge (top-left, colour-coded with white text):
      G1=red, G2=blue, G3=green, G4=purple, G5=amber, G6=rose, G7=teal
  - Egg cards: shown as 🥚 Egg (Species) with hatch species in the name
  - Variant count badge (red pip) when multiple saves of same species/gen
  - Yellow dot when a card has notes or tags

Detail panel (click any card):
  - HD official artwork; shiny version shown for shiny Pokémon
  - ✨ SHINY badge where applicable
  - ⭐ Favourite toggle (top-right of artwork)
  - Name, nickname (if different), Dex #, generation, origin game
  - "more info ↗" — opens Serebii.net page for that Pokémon in the correct
    generation. Discrete teal colour, opens in new browser tab.
  - "open folder ↗" — opens the scanned Pokémon folder in file explorer
  - Type badges, genus, Pokédex flavour text
  - Variant tabs — switch between multiple saves of the same Pokémon
  - Meta grid:
      Level · Nature (hover → stat change tooltip)
      OT · OT ID · Height · Weight
      Gender (♂ blue / ♀ pink) — hidden for genderless species
      Held Item (hover → item description tooltip) — shown only if holding
  - Evolution chain with sprites, arrows, level/item labels
  - Stats: BASE + bar + ACTUAL calculated stat + IV/DV + EV columns
    Gen 1/2: column labelled "DV (max 15)"; no nature modifier applied
  - Moves: name, type badge, damage class, power, accuracy, PP
    Hover any move → tooltip with effect description
  - Abilities: name + hover tooltip with description (Gen 3+ only)
  - Egg panel: simplified — shows 🥚, hatch species, shiny badge if
    applicable. Stats/moves/abilities hidden. Notes and tags still work.
  - Notes: free-text field, saved per variant file
  - Tags: chip-style with autocomplete dropdown. Add with Enter or comma,
    remove with ✕. Existing tags suggested as you type.
  - SAVE button commits notes + tags + favourite


GENDER NOTES
------------
Gen 4-7: Gender read directly from byte 0x1D bits 1-2 in the file.
  0 = male, 1 = female, 2 = genderless. Always accurate.

Gen 3: Gender not stored in file. Derived from PID & 0xFF vs species
  gender threshold (from PokéAPI gender_rate). Same algorithm the game uses —
  fully accurate, not an approximation.

Gen 1/2: Gender not stored in file. Derived from ATK DV vs species gender
  threshold. Same algorithm the game uses. Requires gender_rate from PokéAPI
  cache — shows blank until species is cached.

Genderless species (Registeel, Magnemite etc) show nothing in the gender cell.


EGG SUPPORT
-----------
Gen 2: Eggs identified by species byte 0xFD (internal egg marker).
  Actual hatch species at byte 0x03. Level set to 1.

Gen 3-7: Eggs identified by IV word bit 30. Species is already the
  hatch species. Shiny eggs detected and shown with ✨ SHINY EGG badge.

Egg detail panel shows simplified view: hatch species name, shiny badge
if applicable, gen and origin. Stats/moves/abilities hidden. Notes/tags work.


SEREBII LINKS
-------------
Each detail panel includes a discrete "more info ↗" link to Serebii.net,
pointing to the correct generation's Pokédex page:
  Gen 1: serebii.net/pokedex/NNN.shtml
  Gen 2: serebii.net/pokedex-gs/NNN.shtml
  Gen 3: serebii.net/pokedex-rs/NNN.shtml
  Gen 4: serebii.net/pokedex-dp/NNN.shtml
  Gen 5: serebii.net/pokedex-bw/NNN.shtml
  Gen 6: serebii.net/pokedex-xy/NNN.shtml
  Gen 7: serebii.net/pokedex-sm/NNN.shtml
Opens in a new browser tab. Requires internet.


CACHING
-------
After first scan, the app runs fully offline. All data in cache/:

  pokeapi_cache.json  Keys:
      "6"              → species data (name, types, stats, abilities,
                         sprites, genus, flavour text, growth rate,
                         gender_rate)
      "move:53"        → move data (name, type, power, accuracy, PP,
                         effect description)
      "evo:6"          → evolution chain data
      "ability:blaze"  → ability name and effect description
      "item:234"       → held item name and description (Gen 4-7)
      "item:leftovers" → Gen 2/3 items cached by slug

  notes.json  Keyed by filename:
      "006-CHARIZARD-G3-FR-L40.pk3" → {note, tags, favourite}

  images/  PNG files — downloaded once, served locally forever
      6_hd.png, 6_shiny.png — species artwork
      Also downloaded for evolution chain members

IMPORTANT: notes.json is the only file you cannot recover if lost.
Back it up before clearing the cache. Everything else rebuilds on next scan.

To force a full data refresh: delete pokeapi_cache.json and images/,
then scan. Do NOT delete notes.json.

Cache rebuild required if upgrading from an older version that predates:
  - gender_rate field → delete pokeapi_cache.json
  - move effect descriptions → delete pokeapi_cache.json
  - held item descriptions → delete pokeapi_cache.json


ITEM ID TRANSLATION (Gen 2 & 3)
---------------------------------
Gen 4-7 item IDs match PokéAPI directly. Gen 2 and Gen 3 use different
internal numbering, so the app translates them via built-in lookup tables
(GEN2_ITEM_SLUGS and GEN3_ITEM_SLUGS in app.py) before querying PokéAPI.
Covers all holdable items: type-enhancers, Leftovers, Lucky Egg, Scope Lens,
Metal Coat, berries, and more. Items not in the table show nothing rather than
showing a wrong item name.

LIMITATION: The Gen 2 item ID table is harder to fully verify without real
files with known held items. If a Gen 2 Pokémon holding an item shows nothing,
the ID is missing from the table. If it shows the wrong name, the mapping is
incorrect. Send the .pk2 file for diagnosis. Gen 3 is more thoroughly verified.
Gen 4-7 always correct.


PORTABLE EXE (WINDOWS)
-----------------------
HexDex can be packaged as a portable Windows exe using PyInstaller:

  venv\Scripts\python.exe -m pip install pyinstaller
  venv\Scripts\python.exe -m PyInstaller --onedir --windowed --name HexDex ^
      --add-data "templates;templates" --icon icon.ico launch.py

Output is in dist/HexDex/ — contains HexDex.exe and an _internal/ folder
that must travel with the exe. Zip the entire dist/HexDex/ folder to share.

The cache/ folder is created automatically next to HexDex.exe on first run.
No Python installation required on the target machine.
No .NET Framework required — the Qt backend handles the window natively.

To rebuild after code changes:
  venv\Scripts\python.exe -m PyInstaller HexDex.spec

Build artefacts (build/ folder and HexDex.spec) in the project root can be
deleted after a successful build. HexDex.spec is worth keeping for rebuilds.

To set a custom icon: create icon.ico (multi-size recommended: 16/32/48/256px)
and add --icon icon.ico to the PyInstaller command above.

IMPORTANT: Always use pywebview[qt] (not plain pywebview) before building.
The default WinForms backend bundles pythonnet which causes DLL resolution
errors on other machines. Qt has no such dependency.


KNOWN PITFALLS
--------------
1. Flask runs single-threaded. Never fire two API calls simultaneously.

2. PKHeX exports all formats already decrypted. Do NOT apply XOR decryption.

3. Windows venv conflicts: if another venv is active in your terminal, plain
   `pip` and `python` commands go to the wrong environment. Always use the
   full path: venv\Scripts\python.exe -m pip install <packages>

4. pywebview blob downloads (a.click()) are silently blocked by the Qt
   backend. CSV export uses a tkinter Save As dialog and writes to disk.

5. The ext variable must be recalculated inside the parse loop — not reused
   from the file-collection loop (fixed, documented for future reference).

6. Gen 6 and Gen 7 have identical file layouts. Generation is determined by
   file extension (.pk6 vs .pk7), not by content.

7. Gen 7 files retain the original origin game byte for Pokémon transferred
   from Gen 6 via Pokémon Bank. Gen 7 game table includes Gen 6 IDs.

8. Gen 4 OT names use a custom encoding (A=0x012B), NOT UTF-16LE.
   Using the wrong decoder produces garbled trainer names.

9. Gen 2 eggs use species byte 0xFD as an egg marker — the parser must
   allow this value through and read the actual species from byte 0x03.

10. PyInstaller --onefile breaks pywebview and Flask template loading.
    Always use --onedir.

11. notes.json corruption: parallel save requests (e.g. bulk tagging large
    selections rapidly) can corrupt notes.json. Bulk tag saves are now
    sequential to prevent this, but if corruption occurs the app recovers
    gracefully and logs a warning rather than crashing.

12. Do NOT install plain pywebview on Windows — always use pywebview[qt].
    The WinForms backend (default on Windows) pulls in pythonnet which causes
    "Failed to resolve Python.Runtime.dll" on machines where it wasn't built.


TECHNICAL NOTES
---------------
pywebview backend: Qt (via pywebview[qt])
  - No .NET Framework dependency
  - No pythonnet dependency
  - Fully portable — works on any Windows 10/11 machine out of the box
  - Previous WinForms backend was the default but caused DLL resolution
    failures when distributing the PyInstaller exe to other machines

Gender storage by generation:
  Gen 1/2: not stored — derived from ATK DV + PokéAPI gender_rate
  Gen 3:   not stored — derived from PID & 0xFF + PokéAPI gender_rate
  Gen 4-7: byte 0x1D bits 1-2: 0=male, 1=female, 2=genderless

Confirmed offsets — Gen 6 (.pk6) and Gen 7 (.pk7), 232 bytes, identical:
  0:   PID (uint32)              8:   species (uint16)
  10:  held item (uint16)        12:  OT ID (uint16)
  14:  OT SID (uint16)           16:  EXP (uint32)
  20:  friendship (uint8)        28:  nature (uint8)
  29:  byte 0x1D gender bits     30-35: EVs (6 × uint8)
  64:  nickname (12 × UTF-16LE) 90:  moves (4 × uint16)
  98:  PP (4 × uint8)            116: IV word (packed uint32)
  176: OT name (12 × UTF-16LE)  221: level (uint8)
  223: origin game (uint8)

Gen 7 origin IDs: Sun=30, Moon=31, Ultra Sun=32, Ultra Moon=33
Gen 6 origin IDs: X=24, Y=25, Alpha Sapphire=26, Omega Ruby=27
Gen 5 origin IDs (byte 95): White=20, Black=21, White 2=22, Black 2=23
Gen 4 origin IDs (byte 95): Diamond=10, Pearl=11, Platinum=12, HG=7, SS=8

API routes:
  POST /api/scan          {dir, recursive} → {pokemon, errors, count}
  POST /api/export-csv    {pokemon}        → {ok, path} (tkinter save dialog)
  POST /api/open-folder   {dir}            → opens folder in file explorer
  POST /api/notes         {filename, note, tags, favourite}
  GET  /api/notes/<file>  → {note, tags, favourite}
  GET  /api/browse        → opens tkinter folder picker, returns {dir}
  GET  /api/last-dir      → {dir}
  POST /api/last-dir      {dir}
  GET  /cached-image/<f>  → serves PNG from cache/images/
  GET  /api/cache-info    → {json_kb, images, images_kb}
  POST /api/clear-cache   → wipes cache/


DEBUGGING
---------
Hex-dump any .pk file with field annotations:
    python diagnose.py "C:\path\to\pokemon.pk3"

Use when: origin shows "Unknown", species is wrong, names are garbled,
or adding support for a new format.

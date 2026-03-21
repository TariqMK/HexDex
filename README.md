_Disclaimer:_

_This is an unofficial fan project.
Pokémon and related properties are owned by Nintendo / Game Freak / The Pokémon Company.
No copyrighted assets are distributed with this project._

_In addition, this project was coded with the help of AI by an Engineer who works in IT but is not a Software Developer. The application works perfectly as tested and all files are open-sourced within this repository. While AI can make mistakes, the author believes that it has helped to create a functioning program that has harmless, read-only access to your files and is intended to provide an enjoyable playing experience of the official mainline games (please support the official releases!). Any provided binaries have been compiled directly from the source._ 

---

# HexDex

A personal Pokémon collection frontend for PKHeX users. View your Pokémon in a clean, easy interface.

HexDex is a portable application which scans a folder of PKHeX-exported `.pk` files and turns them into a beautiful, searchable desktop app complete with HD artwork, full stats, move descriptions, evolution chains, held items, gender, and direct links to Serebii.

<img width="2331" height="1915" alt="image" src="https://github.com/user-attachments/assets/7bcaf786-2e98-4a59-b9a8-f91c4c9417d8" />

HexDex gives you a proper way to browse, organise, and reflect on what you've caught across every generation. Think Pokémon Home but free, selfhosted, open-source and youre forever.

Everything runs locally; after the first scan it works fully offline.

---

## Features

### Supported Gens

The following generations of Pokémon are fully supported by HexDex (including eggs and shinies).

- Gen 1: (Red, Blue & Yellow)
- Gen 2: (Gold, Silver & Crystal)
- Gen 3: (Ruby, Sapphire & Emerald)
- Gen 4: (Diamond, Pearl & Platinum)
- Gen 5: (Black, White, Black 2 & White 2)
- Gen 6: (X, Y, Omega Ruby & Alpha Sapphire)
- Gen 7: (Sun, Moon, Ultra Sun, Ultra Moon)

Pokémon visible in HexDex show a wide range of useful data such as their:

<img width="2331" height="1915" alt="image" src="https://github.com/user-attachments/assets/29e4f76c-092d-48c3-98ad-a67bdd87dcf4" />

- Nature
- Original Trainer Name & ID
- Gender
- Evolution Chain
- Stats (including IV and EVs)
- Moves
- Held Items

and more.

_Note: HexDex also supports having multiple versions of the same Pokémon (within the same generation), useful if you export the same Pokémon multiple times at different levels. Also note however, that the same Pokémon exported from different generations will show separately in the main grid view._

### Favourites, Notes & Tags

Easily add notes and tags to your Pokémon for cataloguing and categorisation, these are stored locally. For Pokémon especially dear to you, mark them as favourites for easy access later.

### Move and Ability Metadata

Pokémon natures, abilities and moves have their details available to view. The data is also cached locally after first pull.

### Filters

In addition to your tags, easily filter your collection of Pokémon by type, generation, favourite status, shiny status, legendary status or even by egg!

### Export Option

If you wish to preserve the details of your collection in other formats, simply export to CSV to have all the details from the application in one simple file. 

### Offline After First Run

HexDex runs through the generous services that PokeAPI offers (thank you PokeAPI!). In order to prevent duplicate and unnecessary (see what I did there?) API calls, any data pulled for the first time will be stored and cached locally thereafter. This means that although the first API pull might take a few moments, thereafter your collection will load instantly and entirely offline.

Of course, any new Pokémon added will need to have their information fetched once more.

### Known Issues

- Items for Gen 2 Pokémon may differ in the Detail Pane compared to what the Pokémon is actually holding, this is due to discrepancies with PokeAPI, please report any issues if you notice them. All other Generations of Pokémon work as expected

---

## Install & Run (Direct)

Download the latest version from the `Releases` section, extract the `.zip` and run Hexdex. All required folders will be automatically created. Enjoy!

## Install & Run (From Source)

If you instead prefer to run from the source, simply:

### 1. Clone Repo

```
git clone https://github.com/yourusername/hexdex.git
cd hexdex
```
Alternatively, download the files from this Repo.

### 2. Install Dependencies
```
python.exe -m pip install flask requests pywebview
```

### 3. Run

```
python.exe launch.py
```

---

## How it Works

HexDex is a local Flask web app rendered inside a pywebview desktop window. 

The backend (app.py) parses the binary .pk file formats directly (reading confirmed byte offsets for each generation) and enriches the data with species, move, and ability information from PokéAPI. 

Everything is cached locally in `cache/pokeapi_cache.json` and `cache/images/`. The frontend (`templates/index.html`) is a single-file HTML/CSS/JS app with no external framework dependencies.

Your personal data (notes, tags, favourites) lives in cache/notes.json — back this file up, it's the only thing that can't be rebuilt from scratch.

Remember, HexDex is a read-only viewer. It never modifies, writes to, or validates your .pk files. That being said, always remember to have a backup of your files as part of good practise.

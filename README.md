_Disclaimer:_

_This is an unofficial fan project.
Pokémon and related properties are owned by Nintendo / Game Freak / The Pokémon Company.
No copyrighted assets are distributed with this project._

_In addition, this project was coded with the help of AI by an Engineer who works in IT but is not a Software Developer. The application works perfectly as tested and all files are open-sourced within this repository. While AI can make mistakes, the author believes that it has helped to create a functioning program that has harmless, read-only access to your files and is intended to provide an enjoyable playing experience of the official mainline games (please support the official releases!). Any provided binaries have been compiled directly from the source._ 

---
![banner](https://github.com/user-attachments/assets/00ef647d-0743-4795-bc78-004c1f274a7f)<svg width="100%" viewBox="0 0 680 200" xmlns="http://www.w3.org/2000/svg">
<defs>
  <clipPath id="clip">
    <rect width="680" height="200" rx="12"/>
  </clipPath>
</defs>

<g clip-path="url(#clip)">
  <rect width="680" height="200" fill="#0e1117"/>

  <g opacity="0.07" stroke="#a0c4ff" stroke-width="0.8" fill="none">
    <polygon points="490,10 510,10 520,27 510,44 490,44 480,27"/>
    <polygon points="528,10 548,10 558,27 548,44 528,44 518,27"/>
    <polygon points="566,10 586,10 596,27 586,44 566,44 556,27"/>
    <polygon points="604,10 624,10 634,27 624,44 604,44 594,27"/>
    <polygon points="642,10 662,10 672,27 662,44 642,44 632,27"/>
    <polygon points="509,44 529,44 539,61 529,78 509,78 499,61"/>
    <polygon points="547,44 567,44 577,61 567,78 547,78 537,61"/>
    <polygon points="585,44 605,44 615,61 605,78 585,78 575,61"/>
    <polygon points="623,44 643,44 653,61 643,78 623,78 613,61"/>
    <polygon points="661,44 681,44 691,61 681,78 661,78 651,61"/>
    <polygon points="490,78 510,78 520,95 510,112 490,112 480,95"/>
    <polygon points="528,78 548,78 558,95 548,112 528,112 518,95"/>
    <polygon points="566,78 586,78 596,95 586,112 566,112 556,95"/>
    <polygon points="604,78 624,78 634,95 624,112 604,112 594,95"/>
    <polygon points="642,78 662,78 672,95 662,112 642,112 632,95"/>
    <polygon points="509,112 529,112 539,129 529,146 509,146 499,129"/>
    <polygon points="547,112 567,112 577,129 567,146 547,146 537,129"/>
    <polygon points="585,112 605,112 615,129 605,146 585,146 575,129"/>
    <polygon points="623,112 643,112 653,129 643,146 623,146 613,129"/>
    <polygon points="661,112 681,112 691,129 681,146 661,146 651,129"/>
    <polygon points="490,146 510,146 520,163 510,180 490,180 480,163"/>
    <polygon points="528,146 548,146 558,163 548,180 528,180 518,163"/>
    <polygon points="566,146 586,146 596,163 586,180 566,180 556,163"/>
    <polygon points="604,146 624,146 634,163 624,180 604,180 594,163"/>
    <polygon points="642,146 662,146 672,163 662,180 642,180 632,163"/>
  </g>

  <ellipse cx="60" cy="100" rx="180" ry="120" fill="#1a2a4a" opacity="0.5"/>

</g>
</svg>

# HexDex

A personal Pokémon collection frontend for PKHeX users. View your Pokémon in a clean, easy interface.

HexDex is a portable application which scans a folder of PKHeX-exported `.pk` files and turns them into a beautiful, searchable desktop app complete with HD artwork, full stats, move descriptions, evolution chains, held items, gender, and direct links to Serebii.

<img width="2331" height="1080" alt="image" src="https://github.com/user-attachments/assets/3cdf428d-17f2-4de8-a14b-b1f923ef4a12" />

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

Install the following:

```
python.exe -m pip install flask requests pywebview
```

### 3. Run

Launch the application:

```
python.exe launch.py
```

---

## How it Works

HexDex is a local Flask web app rendered inside a pywebview desktop window. 

The backend (`app.py`) parses the binary .pk file formats directly (reading confirmed byte offsets for each generation) and enriches the data with species, move, and ability information from PokéAPI. 

Everything is cached locally in `cache/pokeapi_cache.json` and `cache/images/`. The frontend (`templates/index.html`) is a single-file HTML/CSS/JS app with no external framework dependencies.

Your personal data (notes, tags, favourites) lives in `cache/notes.json`. Back this file up, it's the only thing that can't be rebuilt from scratch.

Remember, HexDex is a read-only viewer. It never modifies, writes to, or validates your .pk files. That being said, always remember to have a backup of your files as part of good practise.

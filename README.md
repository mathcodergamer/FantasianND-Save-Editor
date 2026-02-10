# Fantasian Neo Dimension Save Editor

## !!!READ FIRST!!!

I am not responsible for corrupting your save if you use it irresponsibly.
Reasonable guardrails are built-in to prevent you from ruining your save, but it is up to you to make sure __YOUR SAVE IS BACKED UP__ before any editing takes place.

## Requirements

`git clone` this repository and install dependency `pycryptodome`, which is necessary for decrypting and re-encrypting save files.  Install with:

```bash
pip install pycryptodome
```

## Locating Your Save File

Fantasian's save file is a single `root.json` file.  There are lots of online instructions for locating your save for your operating system.  Since I'm using SteamOS, I use the script below to copy over my save:

```bash
cp "/home/deck/.local/share/Steam/steamapps/compatdata/2844850/pfx/drive_c/users/steamuser/Documents/My Games/FANTASIAN Neo Dimension/Steam/**/_data/root.json" root_$(date +%m%d_%H%M).json
```

Note that I timestamp my save files so I can rollback to a known working version if editing corrupted my save file.

## Usage

### Quickstart

After copying over my save file (previous step) named `root_0208_0823.json`, the command below will add 1 million in-game currency, analyze all encountered enemies, add 24 of each box key you own, 100 of each battle item you own. 100 of each recovery item you own, 8 of each accessory, 8 of each weapon and 8 of each armor.

```bash
python fantasia.py root_0208_0823.json \
    --add-money --analyze-all --add-box-keys \
    --add-recovery-items --add-battle-items --add-accessories \
    --insert-all-weapons --insert-all-armors \
    --insert-all-accessories
```

By default, the save slot with the longest playtime will be edited.  You can specify which slot by adding `--save-slot-number [NUM]` to your command.

**Note** that I compiled a list of known items in [data/known_item_ids.json](data/known_item_ids.json) extracted from saves of mine and online players, and this might be incomplete.  The list of weapons, accessories and armor above uses this list uses this file.  Open an issue or pull request if you know of any missing ones.  Alternatively, attach your save in a GitHub issue and I have script to extract item ids and merge it with my list.

### Quickstart (Part 2)

__DO NOT USE THIS IF YOU HAVEN'T UNLOCKED PART 2!__

__NOTICE__ The command below is identical to the one above, except __it also adds Part 2 items__ to your game, including 9999x SP Capsules, all growth map gate items, 24 of each upgrade materials.
__DO NOT USE THIS__ unless you have unlocked skill points or started act 2.
I do know the consequence of using it earlier than that and I am not responsible for any game breaking as a result of it.

```bash
python fantasia.py root_0208_0823.json \
    --add-money --analyze-all --add-box-keys \
    --add-recovery-items --add-battle-items --add-accessories \
    --insert-all-weapons --insert-all-armors \
    --insert-all-accessories --insert-or-add-sp-capsules \
    --insert-all-gate-items --insert-all-upgrade-materials
```

### Remove Unsellable Weapons

If you just want to remove unsellable weapons (likely in NG+), you can use the below.  Subsitute `root_copy.json` with your save file path.

```bash
python fantasia.py root_copy.json --remove-extra-unsellable-weapons
```

### Full Usage

Below is full description of the usage as output by the program.

```txt
$ python fantasia.py --help
usage: fantasia.py [-h] [--save-slot-number NUM] [--add-money [AMOUNT]] [--print-save]
                   [--analyze-all] [--add-box-keys] [--add-recovery-items] [--add-battle-items]
                   [--add-accessories] [--insert-all-weapons] [--insert-all-armors]
                   [--insert-all-accessories] [--insert-or-add-sp-capsules]
                   [--insert-all-gate-items] [--insert-all-upgrade-materials]
                   [--remove-extra-unsellable-weapons] [--insert-items [ITEM_ID ...]]
                   root_json_path

positional arguments:
  root_json_path

options:
  -h, --help            show this help message and exit
  --save-slot-number NUM
                        Specify the save slot number to edit. If set to -1, the save with the
                        longest playtime will be edited.
  --add-money [AMOUNT]  Add specified amount of money (default: 1,000,000).
  --print-save          Print all extracted information from save to command line.
  --analyze-all         Analyze all encountered enemies (won't work on unseen ones)
  --add-box-keys        Add 25 to owned box keys (if you have less than 25). Note that max num. of
                        boxes per key is 24.
  --add-recovery-items  Add 100 to owned recovery items (if less than 100).
  --add-battle-items    Add 100 to owned battle items.
  --add-accessories     Add 8 to owned accessories (if less than 8).
  --insert-all-weapons  Add 8 copies of every weapon known in data/knwon_item_ids.json.
  --insert-all-armors   Add 8 copies of every armor known in data/known_item_ids.json.
  --insert-all-accessories
                        Add 8 copies of every accessory known in data/known_item_ids.json. To not
                        interfere with plot, Divine Artifacts are skipped.
  --insert-or-add-sp-capsules
                        Insert or add 9999 SP Capsules.
  --insert-all-gate-items
                        Insert all items that unlock growth map gates (will skip existing ones).
  --insert-all-upgrade-materials
                        Insert 24 of each weapon/armor upgrade materials.
  --remove-extra-unsellable-weapons
                        Remove extra unsellable (ultimate) weapons but keep the ones you equipped.
  --insert-items [ITEM_ID ...]
                        Insert NEW items in quantities of 8. To avoid game crashing, the program
                        will error if you try to insert existing, unknown or key/quest items. Look
                        at data/known_item_ids.json for a list of known items in the game.
```

---

Let me know of any issues by opening an issue on GitHub on this repository.


---

Built on SteamOS <3 (Legion Go S).  Thank you Valve for the incredible operating system.

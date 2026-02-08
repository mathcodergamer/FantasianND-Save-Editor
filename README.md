# Fantasian Neo Dimension Save Editor

## !!!READ FIRST!!!

I am not responsible for corrupting your save if you use it irresponsibly.
Reasonable guardrails are built-in to prevent you from ruining your save, but it is up to you to make sure YOUR SAVE IS BACKED UP before any editing takes place.

## Requirements

`pycryptodome` is necessary for decrypting and re-encrypting save files.  Install with:

```bash
pip install pycryptodome
```

## Locating Your Save File

Fantasian's save file is a single `root.json` file.  There are lots of online instructions for locating your save.  Since I'm using SteamOS, I use the script below to copy over my save:

```bash
cp "/home/deck/.local/share/Steam/steamapps/compatdata/2844850/pfx/drive_c/users/steamuser/Documents/My Games/FANTASIAN Neo Dimension/Steam/**/_data/root.json" root_$(date +%m%d_%H%M).json
```

Note that I timestamp my save files so I can rollback to a known working version if editing corrupted my save file.

## Usage

After copying over my save file (previous step) named `root_0208_0823.json`, the command below will add some money, accessories, keys, battle items, good weapons, and good armors.

```bash
python fantasia.py root_0208_0823.json \
    --add-money --analyze-all --add-box-keys \
    --add-recovery-items --add-battle-items --add-accessories \
    --insert-items \
      Acce_ParaAtk_XL Acce_ParaAgi_XL Acce_ParaAvo_L Acce_ParaDef_XL \
      Acce_ParaMp_XL Acce_ParaHp_XL \
      ArmorM_Rk06 ArmorM_OW_Nm05_Eh ArmorS_Rk06 ArmorS_OW_Eh05_02 \
      WpSword_Rk06 WpSword_OW_EhUlt_13 WpWand_OW_EhUlt_12 WpWand_Rk04_Healing \
      WpRing_Rk04_VsMachine WpRing_OW_EhUlt_12 WpLantern_OW_EhUlt_12 \
      WpKnuckle_Rk06 WpKnuckle_OW_EhUlt_12 WpGun_OW_EhUlt_12 WpGadget_OW_EhUlt_12 \
      WpBoomer_Rk06 WpBoomer_OW_EhUlt_12
```

Below is full description of the usage as output by the program.

```bash
$ python fantasia.py --help
usage: fantasia.py [-h] [--add-money [AMOUNT]] [--print-save] [--analyze-all] [--add-box-keys] [--add-recovery-items] [--add-battle-items] [--add-accessories] [--insert-items [ITEM_ID ...]] root_json_path

positional arguments:
  root_json_path

options:
  -h, --help            show this help message and exit
  --add-money [AMOUNT]  Add specified amount of money (default: 1,000,000).
  --print-save          Print all extracted information from save to command line.
  --analyze-all         Analyze all encountered enemies (won't work on unseen ones)
  --add-box-keys        Add 25 to owned box keys (if you have less than 25). Note that max num. of boxes per key is 24.
  --add-recovery-items  Add 100 to owned recovery items (if less than 100).
  --add-battle-items    Add 60 to owned battle items (if less than 60).
  --add-accessories     Add 8 to owned accessories (if less than 8).
  --insert-items [ITEM_ID ...]
                        Insert NEW items in quantities of 8.To avoid game crashing, the program will error if you try to insert existing, unknown or key/quest items. Look atdata/known_item_ids.json for a list of known items in the game.
```

---

Built on SteamOS <3 (Legion Go S).  Thank you Valve for the incredible operating system.

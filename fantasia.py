import argparse
import json
import base64
import sys
import os
import pprint

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

AesIV = b"Nq4G3pTQFLTCeiB7"
AesKey = b"yrhWj8EiU83kXupm"

KNOWN_ITEM_IDS = json.load(open("data/known_item_ids.json"))

def decrypt(data):
    cipher = AES.new(AesKey, AES.MODE_CBC, AesIV)
    return unpad(cipher.decrypt(data), AES.block_size)

def encrypt(data):
    cipher = AES.new(AesKey, AES.MODE_CBC, AesIV)
    return cipher.encrypt(pad(data, AES.block_size))

def extract_record(record):
    decrypted_save_str = decrypt(base64.b64decode(record["encryptedString"])).decode("utf-8")
    decrypted_save = json.loads(decrypted_save_str)
    save_dict = {
        k: v for k, v in zip(decrypted_save["keys"], decrypted_save["values"])
    }
    return save_dict

def encrypt_save_dict(save_dict):
    save_string = json.dumps({
        "keys": list(save_dict.keys()),
        "values": list(save_dict.values()),
    }, indent=4)  # if nothing changed, this should perfectly recover decrypted_save_str
    return base64.b64encode(encrypt(save_string.encode("utf-8"))).decode("utf-8")


def insert_item(
        inventory_data, item_id, skip_existing=False, count=8,
        add_to_existing=False):
    # some minimal guardrails to avoid game crashing
    if item_id not in KNOWN_ITEM_IDS:
        raise ValueError(f"unknown item id: {item_id}")
    if item_id.startswith("Item_Key_") or item_id.startswith("Item_Quest_"):
        raise ValueError(f"Cannot insert key/quest item: {item_id}")

    if item_id in inventory_data["itemTable"]["keyList"]:
        index = inventory_data["itemTable"]["keyList"].index(item_id)
        assert inventory_data["itemTable"]["valueList"][index]["itemId"] == item_id
        curr_count = inventory_data["itemTable"]["valueList"][index]["count"]

        if skip_existing:
            if curr_count == 0:
                # item doesn't actually exist -- still add amount
                inventory_data["itemTable"]["valueList"][index]["count"] += count
            else:
                # item already existed (>1 quantity), skip
                return
        elif add_to_existing:
            inventory_data["itemTable"]["valueList"][index]["count"] += count
        else:
            raise ValueError(f"Item: {item_id} already in inventory!")

    # newType: 0=unknown, 1=discovery, 2=get, 3=confirm
    inventory_data["itemTable"]["keyList"].append(item_id)
    inventory_data["itemTable"]["valueList"].append(
        {"count": count, "itemId": item_id, "newType": 2})

def quicktest(record):
    save_dict = extract_record(record)
    encryped_str = encrypt_save_dict(save_dict)
    assert encryped_str == record["encryptedString"]
    print("Quick Test passed!")

def find_latest_save_slot(records):
    """Find the save slot with the longest playtime."""
    records = [records[0]] + records[2:]  # records[1] is the quicksave slot

    max_playtime = 0
    max_idx = 0
    for i, record in enumerate(records):
        save_dict = extract_record(record)
        playtime = json.loads(save_dict["GameSystemInfo"])["_playTimeSec"]
        if playtime > max_playtime:
            max_playtime = playtime
            max_idx = i

    return max_idx



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        formatter_class=lambda prog: argparse.HelpFormatter(prog, width=100))
    parser.add_argument("root_json_path", type=str)
    parser.add_argument(
        "--save-slot-number", type=int, default=-1, metavar="NUM",
        help=("Specify the save slot number to edit.  If set to -1, the save with the "
              "longest playtime will be edited."))
    parser.add_argument(
        "--add-money", nargs="?", type=int, const=1_000_000, metavar="AMOUNT",
        help="Add specified amount of money (default: 1,000,000).")
    parser.add_argument(
        "--print-save", action="store_true",
        help="Print all extracted information from save to command line.")
    parser.add_argument(
        "--analyze-all", action="store_true",
        help="Analyze all encountered enemies (won't work on unseen ones)")
    parser.add_argument(
        "--add-box-keys", action="store_true",
        help=("Add 25 to owned box keys (if you have less than 25). "
             "Note that max num. of boxes per key is 24."))
    parser.add_argument(
        "--add-recovery-items", action="store_true",
        help="Add 100 to owned recovery items (if less than 100)."
    )
    parser.add_argument(
        "--add-battle-items", action="store_true",
        help="Add 100 to owned battle items."
    )
    parser.add_argument(
        "--add-accessories", action="store_true",
        help="Add 8 to owned accessories (if less than 8)."
    )
    parser.add_argument(
        "--insert-all-weapons", action="store_true",
        help="Add 8 copies of every weapon known in data/knwon_item_ids.json."
    )
    parser.add_argument(
        "--insert-all-armors", action="store_true",
        help="Add 8 copies of every armor known in data/known_item_ids.json."
    )
    parser.add_argument(
        "--insert-all-accessories", action="store_true",
        help=("Add 8 copies of every accessory known in data/known_item_ids.json."
            "  To not interfere with plot, Divine Artifacts are skipped.")
    )
    parser.add_argument(
        "--insert-or-add-sp-capsules", action="store_true",
        help="Insert or add 9999 SP Capsules."
    )
    parser.add_argument(
        "--insert-all-gate-items", action="store_true",
        help=("Insert all items that unlock growth map gates (will skip existing ones).")
    )
    parser.add_argument(
        "--insert-all-upgrade-materials", action="store_true",
        help="Insert 24 of each weapon/armor upgrade materials."
    )
    parser.add_argument(
        "--remove-extra-unsellable-weapons", action="store_true",
        help="Remove extra unsellable (ultimate) weapons but keep the ones you equipped."
    )
    parser.add_argument(
        "--insert-items", metavar="ITEM_ID", type=str, nargs="*", default=[],
        help=("Insert NEW items in quantities of 8. "
              "To avoid game crashing, the program will error if you try to "
              "insert existing, unknown or key/quest items.  Look at "
              "data/known_item_ids.json for a list of known items in the game.")
    )

    args = parser.parse_args()

    root_json_path = args.root_json_path
    edited = False

    root = json.load(open(root_json_path))
    records = json.loads(root["dataString"])["records"]
    print(f"Retrieved {len(records)-1} save slots and 1 quicksave.")
    if args.save_slot_number == -1:
        save_slot = find_latest_save_slot(records)
        print(f"Found latest save slot: {save_slot+1}")
    else:
        save_slot = args.save_slot_number

    record_idx = 0 if save_slot == 0 else save_slot + 1  # records[1] is the quicksave
    record = records[record_idx]
    save_dict = extract_record(record)
    print(f"Editing save slot {save_slot+1} (saved on date: {save_dict['Date']})")

    quicktest(record)

    if args.add_money:
        game_system_info = json.loads(save_dict["GameSystemInfo"])
        game_system_info["_money"] += args.add_money
        game_system_info_str = json.dumps(game_system_info, separators=(",", ":"))
        save_dict["GameSystemInfo"] = game_system_info_str
        edited = True

    if args.analyze_all:
        battle_data = json.loads(save_dict["BattleData"])
        for values in battle_data["libraryInfoTable"]["valueList"]:
            values["analyzed"] = True  # value looks like {'analyzed': False, 'defeatCount': 18}
        battle_data_str = json.dumps(battle_data, separators=(",", ":"))
        save_dict["BattleData"] = battle_data_str
        edited = True

    if args.add_box_keys:
        inventory_data = json.loads(save_dict["Inventory"])
        for value in inventory_data["itemTable"]["valueList"]:
            # value looks like {'count': 1, 'itemId': 'WpSword_Rk01', 'newType': 3}
            if value["itemId"].startswith("Item_BoxKey_") and value["count"] < 25:
                value["count"] += 25
        inventory_data_str = json.dumps(inventory_data, separators=(",", ":"))
        save_dict["Inventory"] = inventory_data_str
        edited = True

    edit_inventory = (
        args.add_box_keys or
        args.add_recovery_items or
        args.add_battle_items or
        args.add_accessories or
        args.insert_all_weapons or
        args.insert_all_armors or
        args.remove_extra_unsellable_weapons or
        args.insert_items
    )
    if edit_inventory:
        edited = True
        inventory_data = json.loads(save_dict["Inventory"])
        player_status = json.loads(save_dict["PlayerStatus"])
        equipped_weapons = [p["_weapon"] for p in player_status["_items"]]

        # process all amount increments
        for value in inventory_data["itemTable"]["valueList"]:
            # value looks like {'count': 1, 'itemId': 'WpSword_Rk01', 'newType': 3}

            if (args.add_box_keys and value["itemId"].startswith("Item_BoxKey_")
                    and value["count"] < 25):
                value["count"] += 25

            if (args.add_recovery_items and value["itemId"].startswith("Item_Recover_")
                    and value["count"] < 100):
                value["count"] += 100

            if (args.add_battle_items and value["itemId"].startswith("Item_Battle_")):
                value["count"] += 100

            if (args.add_accessories and value["itemId"].startswith("Acce_")
                    and value["count"] < 8):
                value["count"] += 8

            if (args.remove_extra_unsellable_weapons and
                    value["itemId"].startswith("Wp") and "_OW_EhUlt_" in value["itemId"]):
                value["count"] = 1 if value["itemId"] in equipped_weapons else 0

        # process new item insertions
        if args.insert_all_weapons:
            for item_id in KNOWN_ITEM_IDS:
                if item_id.startswith("Wp"):
                    insert_item(inventory_data, item_id, skip_existing=True)

        if args.insert_all_armors:
            for item_id in KNOWN_ITEM_IDS:
                if item_id.startswith("ArmorM_") or item_id.startswith("ArmorS_"):
                    insert_item(inventory_data, item_id, skip_existing=True)

        if args.insert_all_accessories:
            for item_id in KNOWN_ITEM_IDS:
                if item_id.startswith("Acce_") and not item_id.startswith("Acce_God"):
                    insert_item(inventory_data, item_id, skip_existing=True)

        if args.insert_all_gate_items:
            for item_id in KNOWN_ITEM_IDS:
                if item_id.startswith("Item_Gate_"):
                    insert_item(inventory_data, item_id, skip_existing=True, count=1)

        if args.insert_all_upgrade_materials:
            for item_id in KNOWN_ITEM_IDS:
                if item_id.startswith("Item_Material_"):
                    insert_item(inventory_data, item_id, add_to_existing=True, count=24)

        if args.insert_or_add_sp_capsules:
            insert_item(inventory_data, "Item_SpAdd_Capsule", add_to_existing=True, count=9999)

        for item_id in args.insert_items:
            insert_item(inventory_data, item_id)

        inventory_data_str = json.dumps(inventory_data, separators=(",", ":"))
        save_dict["Inventory"] = inventory_data_str

    if args.print_save:
        for k, v in save_dict.items():
            print("-" * 100)
            print(k)
            print("-" * 100)
            try:
                pprint.pprint(json.loads(v))
            except:
                print(v)
            print("\n" * 3)

    if edited:
        print("Finished editing.")
        encrypted_str = encrypt_save_dict(save_dict)

        records[-1]["encryptedString"] = encrypted_str
        new_data_str = json.dumps({"records": records}, separators=(",", ":"))
        root["dataString"] = new_data_str
        edited_save_path = "edited_" + os.path.basename(root_json_path)
        with open(edited_save_path, "w") as f:
            json.dump(root, f, indent=4)
        print(f"Edited save file is at {edited_save_path}")

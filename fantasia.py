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


def quicktest(record):
    save_dict = extract_record(record)
    encryped_str = encrypt_save_dict(save_dict)
    assert encryped_str == record["encryptedString"]
    print("Quick Test passed!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root_json_path", type=str)
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
        help="Add 60 to owned battle items (if less than 60)."
    )
    parser.add_argument(
        "--add-accessories", action="store_true",
        help="Add 8 to owned accessories (if less than 8)."
    )
    parser.add_argument(
        "--insert-items", metavar="ITEM_ID", type=str, nargs="*", default=[],
        help=("Insert NEW items in quantities of 8."
              "To avoid game crashing, the program will error if you try to "
              "insert existing, unknown or key/quest items.")
    )

    args = parser.parse_args()

    root_json_path = args.root_json_path
    edited = False

    root = json.load(open(root_json_path))
    records = json.loads(root["dataString"])["records"]
    record = records[-1]

    quicktest(record)

    save_dict = extract_record(record)

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
        args.insert_items
    )
    if edit_inventory:
        edited = True
        inventory_data = json.loads(save_dict["Inventory"])

        # process all amount increments
        for value in inventory_data["itemTable"]["valueList"]:
            # value looks like {'count': 1, 'itemId': 'WpSword_Rk01', 'newType': 3}

            if (args.add_box_keys and value["itemId"].startswith("Item_BoxKey_")
                    and value["count"] < 25):
                value["count"] += 25

            if (args.add_recovery_items and value["itemId"].startswith("Item_Recover_")
                    and value["count"] < 100):
                value["count"] += 100

            if (args.add_battle_items and value["itemId"].startswith("Item_Battle_")
                    and value["count"] < 60):
                value["count"] += 60

            if (args.add_accessories and value["itemId"].startswith("Acce_")
                    and value["count"] < 8):
                value["count"] += 8

        # process new item insertions
        for item_id in args.insert_items:
            # some minimal guardrails to avoid game crashing
            if item_id not in KNOWN_ITEM_IDS:
                raise ValueError(f"unknown item id: {item_id}")
            if item_id.startswith("Item_Key_") or item_id.startswith("Item_Quest_"):
                raise ValueError(f"Cannot insert key/quest item: {item_id}")
            if item_id in inventory_data["itemTable"]["keyList"]:
                raise ValueError(f"Item: {item_id} already in inventory!")

            # newType: 0=unknown, 1=discovery, 2=get, 3=confirm
            inventory_data["itemTable"]["keyList"].append(item_id)
            inventory_data["itemTable"]["valueList"].append(
                {"count": 8, "itemId": item_id, "newType": 2})

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

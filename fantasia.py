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
        "--add-money", nargs="?", type=int, const=1_000_000)
    parser.add_argument(
        "--print-save", action="store_true")
    parser.add_argument(
        "--analyze-all", action="store_true", 
        help="Analyze all encountered enemies (won't work on unseen ones)")
    parser.add_argument(
        "--add-box-keys", action="store_true", 
        help=("Add 25 to a box key type you already own (if you have less than 25). "
             "Note that max num. of boxes per key is 24."))
    parser.add_argument(
        "--add-recovery-items", action="store_true",
        help="Add 100 "
    )
    parser.add_argument("--insert-items", type=str, nargs="+")
    
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
    
    if args.add_elixir:
        inventory_data = json.loads(save_dict["Inventory"])
        for value in inventory_data["itemTable"]["valueList"]:
            # value looks like {'count': 1, 'itemId': 'WpSword_Rk01', 'newType': 3}
            if value["itemId"].startswith("Item_BoxKey_"):
                value["count"] += 25
        inventory_data_str = json.dumps(inventory_data, separators=(",", ":"))
        save_dict["Inventory"] = inventory_data_str
        edited = True

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
        encrypted_str = encrypt_save_dict(save_dict)

        records[-1]["encryptedString"] = encrypted_str
        new_data_str = json.dumps({"records": records}, separators=(",", ":"))
        root["dataString"] = new_data_str
        edited_save_path = "edited_" + os.path.basename(root_json_path)
        with open(edited_save_path, "w") as f:
            json.dump(root, f, indent=4)
        print(f"Edited save file is at {edited_save_path}")

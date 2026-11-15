import hashlib
import json
import os
import time

CHAIN_FILE = "chain.json"


def hash_block(block):
    content = {k: block[k] for k in ("index", "timestamp", "data", "prev_hash")}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def save_chain(chain):
    with open(CHAIN_FILE, "w") as f:
        json.dump(chain, f, indent=2)


def load_chain():
    if os.path.exists(CHAIN_FILE):
        with open(CHAIN_FILE) as f:
            return json.load(f)
    genesis = {
        "index": 0,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": "Genesis Block",
        "prev_hash": "0",
    }
    genesis["hash"] = hash_block(genesis)
    save_chain([genesis])
    return [genesis]


def add_transaction(survey_no, action, from_owner, to_owner):
    chain = load_chain()
    block = {
        "index": len(chain),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": {
            "survey_no": survey_no,
            "action": action,
            "from": from_owner,
            "to": to_owner,
        },
        "prev_hash": chain[-1]["hash"],
    }
    block["hash"] = hash_block(block)
    chain.append(block)
    save_chain(chain)
    return block


def is_chain_valid():
    chain = load_chain()
    for i in range(1, len(chain)):
        if chain[i]["hash"] != hash_block(chain[i]):
            return False
        if chain[i]["prev_hash"] != chain[i - 1]["hash"]:
            return False
    return True


def get_history(survey_no):
    chain = load_chain()
    return [b for b in chain[1:] if b["data"]["survey_no"] == survey_no]

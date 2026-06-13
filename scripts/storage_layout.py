"""
Storage layout analysis for A1 (SWSD), C5, and H4 algorithms.
Requires Foundry (forge) for full analysis from source.
For deployed contracts, uses bytecode heuristics + storage slot probing.
"""
import json
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from rpc_helpers import get_storage_at, get_code
from selector_utils import keccak256


# ── EIP-1967 Standard Slots ──
STANDARD_SLOTS = {
    "eip1967_impl": "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc",
    "eip1967_admin": "0xb53127684a568b3173ae13b9f8a6016e243e63b6e8ee1178d6a717850b5d6103",
    "eip1967_beacon": "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50",
    "oz_impl_old": "0x7050c9e0f4ca769c69bd3a8ef740bc37934f8e2c036e5a723fd8ee048ed3f8c3",
}


def probe_standard_slots(chain: str, address: str) -> dict:
    """Probe EIP-1967 and other standard storage slots."""
    results = {}
    for name, slot in STANDARD_SLOTS.items():
        try:
            val = get_storage_at(chain, address, slot)
            if val and val != "0x" + "0" * 64:
                results[name] = {
                    "slot": slot,
                    "value": val,
                    "decoded_address": "0x" + val[-40:] if len(val) >= 42 else val,
                }
        except Exception:
            pass
    return results


def compute_mapping_slot(base_slot: int, key: str) -> str:
    """Compute storage slot for mapping[key] at base_slot.
    slot = keccak256(key . base_slot)
    """
    key_bytes = bytes.fromhex(key.replace("0x", "").zfill(64))
    slot_bytes = base_slot.to_bytes(32, "big")
    h = keccak256(key_bytes + slot_bytes)
    return "0x" + h.hex()


def compute_array_element_slot(base_slot: int, index: int) -> str:
    """Compute storage slot for array[index] at base_slot.
    slot = keccak256(base_slot) + index
    """
    slot_bytes = base_slot.to_bytes(32, "big")
    h = keccak256(slot_bytes)
    base = int(h.hex(), 16)
    return hex(base + index)


def probe_sequential_slots(chain: str, address: str, n: int = 20) -> list:
    """Read first N sequential storage slots to fingerprint layout."""
    slots = []
    for i in range(n):
        slot_hex = hex(i)
        try:
            val = get_storage_at(chain, address, slot_hex)
            if val and val != "0x" + "0" * 64:
                slots.append({
                    "slot": i,
                    "hex": slot_hex,
                    "value": val,
                    "decoded_uint": int(val, 16) if val else 0,
                })
        except Exception:
            pass
    return slots


def diff_storage_layouts(layout_a: list, layout_b: list) -> dict:
    """Diff two storage layouts (from forge inspect or sequential probing).
    Finds: new slots, removed slots, type changes, offset collisions.
    """
    map_a = {s["slot"]: s for s in layout_a}
    map_b = {s["slot"]: s for s in layout_b}
    
    all_slots = set(map_a.keys()) | set(map_b.keys())
    
    added = []
    removed = []
    changed = []
    
    for slot in sorted(all_slots):
        in_a = slot in map_a
        in_b = slot in map_b
        
        if in_a and not in_b:
            removed.append(map_a[slot])
        elif in_b and not in_a:
            added.append(map_b[slot])
        elif in_a and in_b:
            if map_a[slot].get("value") != map_b[slot].get("value"):
                changed.append({
                    "slot": slot,
                    "old": map_a[slot],
                    "new": map_b[slot],
                })
    
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "collision_risk": len(changed) > 0,
    }


def analyze_proxy_storage(chain: str, proxy_addr: str) -> dict:
    """Full proxy storage analysis: probe standard slots, find impl, diff layouts."""
    result = {
        "proxy": proxy_addr,
        "standard_slots": probe_standard_slots(chain, proxy_addr),
        "sequential_slots": probe_sequential_slots(chain, proxy_addr),
    }
    
    # Check for implementation
    impl_slot = result["standard_slots"].get("eip1967_impl")
    if impl_slot:
        impl_addr = impl_slot["decoded_address"]
        result["implementation"] = impl_addr
        result["impl_code_size"] = len(get_code(chain, impl_addr) or "") // 2 - 1
    
    return result


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python storage_layout.py <chain> <address>")
        sys.exit(1)
    
    chain = sys.argv[1]
    addr = sys.argv[2]
    
    result = analyze_proxy_storage(chain, addr)
    print(json.dumps(result, indent=2, default=str))

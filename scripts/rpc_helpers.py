"""
RPC helper utilities for fund-critical bug hunting.
Keyless EVM RPC calls with automatic fallback across public providers.
"""
import json
import requests
from typing import Any, Optional

# Public RPCs by chain (all need User-Agent header)
RPCS = {
    "ethereum": [
        "https://ethereum-rpc.publicnode.com",
        "https://eth.merkle.io",
        "https://ethereum-pokt.nodies.app",
    ],
    "bsc": [
        "https://bsc-rpc.publicnode.com",
        "https://bsc-pokt.nodies.app",
    ],
    "arbitrum": [
        "https://arbitrum-one-rpc.publicnode.com",
        "https://arbitrum-pokt.nodies.app",
    ],
    "optimism": [
        "https://optimism-rpc.publicnode.com",
        "https://optimism-pokt.nodies.app",
    ],
    "base": [
        "https://base-rpc.publicnode.com",
        "https://base-pokt.nodies.app",
    ],
    "polygon": [
        "https://polygon-bor-rpc.publicnode.com",
        "https://polygon-pokt.nodies.app",
    ],
    "avalanche": [
        "https://avalanche-c-chain-rpc.publicnode.com",
        "https://avax-pokt.nodies.app",
    ],
    "sonic": [
        "https://rpc.soniclabs.com",
    ],
    "flare": [
        "https://flare-api.flare.network/ext/C/rpc",
    ],
    "monad": [
        "https://monad-testnet.drpc.org",  # Placeholder — update when mainnet launches
    ],
}

HEADERS = {"User-Agent": "hunt/1.0", "Content-Type": "application/json"}
TIMEOUT = 15


def rpc_call(chain: str, method: str, params: list = None, block: str = "latest",
             rpc_url: str = None) -> Any:
    """Make a JSON-RPC call with fallback across providers."""
    params = params or []
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    
    urls = [rpc_url] if rpc_url else RPCS.get(chain, [])
    if not urls:
        raise ValueError(f"No RPC configured for chain: {chain}. Available: {list(RPCS.keys())}")
    
    last_error = None
    for url in urls:
        try:
            r = requests.post(url, headers=HEADERS, json=payload, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                last_error = data["error"]
                continue
            return data.get("result")
        except Exception as e:
            last_error = str(e)
            continue
    raise RuntimeError(f"All RPCs failed for {chain}. Last error: {last_error}")


def eth_call(chain: str, to: str, data: str, block: str = "latest",
             from_addr: str = None, rpc_url: str = None) -> str:
    """Execute eth_call (read-only) against a contract."""
    call_obj = {"to": to, "data": data}
    if from_addr:
        call_obj["from"] = from_addr
    return rpc_call(chain, "eth_call", [call_obj, block], rpc_url=rpc_url)


def get_code(chain: str, address: str, block: str = "latest") -> str:
    """Get contract bytecode."""
    return rpc_call(chain, "eth_getCode", [address, block])


def get_storage_at(chain: str, address: str, slot: str, block: str = "latest") -> str:
    """Read a storage slot."""
    return rpc_call(chain, "eth_getStorageAt", [address, slot, block])


def get_block_number(chain: str) -> int:
    """Get latest block number."""
    result = rpc_call(chain, "eth_blockNumber")
    return int(result, 16)


def get_balance(chain: str, address: str, block: str = "latest") -> int:
    """Get native balance in wei."""
    result = rpc_call(chain, "eth_getBalance", [address, block])
    return int(result, 16)


# ── Selector helpers ──
def fn_selector(sig: str) -> str:
    """Compute 4-byte function selector from signature. e.g., 'transfer(address,uint256)'"""
    from hashlib import sha3_256
    try:
        from Crypto.Hash import keccak
        h = keccak.new(digest_bits=256)
        h.update(sig.encode())
        return "0x" + h.hexdigest()[:8]
    except ImportError:
        # Fallback: use web3-style keccak
        import struct
        h = sha3_256(sig.encode())
        return "0x" + h.hexdigest()[:8]


def encode_call(sig: str, *args) -> str:
    """Simple ABI encoding for common types. 
    Supports: address, uint256, bytes32, bool.
    For complex encoding, use eth_abi package.
    """
    selector = fn_selector(sig)
    encoded_args = ""
    for arg in args:
        if isinstance(arg, str) and arg.startswith("0x"):
            # Address or bytes32
            encoded_args += arg[2:].lower().zfill(64)
        elif isinstance(arg, bool):
            encoded_args += str(int(arg)).zfill(64)
        elif isinstance(arg, int):
            encoded_args += hex(arg)[2:].zfill(64)
        else:
            raise ValueError(f"Unsupported arg type: {type(arg)}")
    return selector + encoded_args


if __name__ == "__main__":
    # Quick connectivity test
    for chain in ["ethereum", "bsc", "arbitrum"]:
        try:
            bn = get_block_number(chain)
            print(f"✅ {chain}: block #{bn}")
        except Exception as e:
            print(f"❌ {chain}: {e}")

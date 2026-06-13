"""
Function selector computation and ABI encoding utilities.
Uses pycryptodome's keccak for correctness.
"""
import struct
from typing import Union


def keccak256(data: bytes) -> bytes:
    """Compute keccak256 hash. Uses pycryptodome if available, falls back to python3.12 subprocess."""
    try:
        from Crypto.Hash import keccak
        h = keccak.new(digest_bits=256)
        h.update(data)
        return h.digest()
    except ImportError:
        pass
    # Fallback: call python3.12 which has pycryptodome installed
    import subprocess
    hex_data = data.hex()
    r = subprocess.run(
        ["python3.12", "-c",
         f"from Crypto.Hash import keccak; h = keccak.new(digest_bits=256); "
         f"h.update(bytes.fromhex('{hex_data}')); print(h.hexdigest())"],
        capture_output=True, text=True, timeout=5
    )
    if r.returncode == 0 and r.stdout.strip():
        return bytes.fromhex(r.stdout.strip())
    raise ImportError(f"keccak256 failed: {r.stderr}")


def fn_selector(sig: str) -> str:
    """Compute 4-byte function selector. e.g., 'transfer(address,uint256)' -> '0xa9059cbb'"""
    h = keccak256(sig.encode("utf-8"))
    return "0x" + h[:4].hex()


def event_topic(sig: str) -> str:
    """Compute event topic hash. e.g., 'Transfer(address,address,uint256)' -> '0xddf2...'"""
    h = keccak256(sig.encode("utf-8"))
    return "0x" + h.hex()


def encode_uint256(val: int) -> str:
    """ABI-encode a uint256."""
    return hex(val)[2:].zfill(64)


def encode_address(addr: str) -> str:
    """ABI-encode an address."""
    return addr.lower().replace("0x", "").zfill(64)


def encode_bytes32(val: Union[str, bytes]) -> str:
    """ABI-encode bytes32."""
    if isinstance(val, str):
        val = val.replace("0x", "")
        return val.ljust(64, "0")
    return val.hex().ljust(64, "0")


def encode_call(sig: str, *args: Union[int, str, bool]) -> str:
    """
    Simple ABI encoding for static types.
    Supports: uint256 (int), address (0x..., 40 hex chars), bytes32 (0x..., 64 hex chars), bool.
    """
    sel = fn_selector(sig)
    parts = []
    for arg in args:
        if isinstance(arg, bool):
            parts.append(encode_uint256(int(arg)))
        elif isinstance(arg, int):
            parts.append(encode_uint256(arg))
        elif isinstance(arg, str) and arg.startswith("0x"):
            clean = arg[2:]
            if len(clean) <= 40:
                parts.append(encode_address(arg))
            else:
                parts.append(encode_bytes32(arg))
        else:
            raise ValueError(f"Unsupported arg: {arg!r}")
    return sel + "".join(parts)


def decode_uint256(hex_str: str) -> int:
    """Decode a uint256 from hex."""
    return int(hex_str.replace("0x", ""), 16)


def decode_address(hex_str: str) -> str:
    """Decode an address from 32-byte hex."""
    clean = hex_str.replace("0x", "")
    return "0x" + clean[-40:]


# ── Common selectors ──
COMMON_SELECTORS = {
    "totalSupply()": None,
    "balanceOf(address)": None,
    "decimals()": None,
    "symbol()": None,
    "name()": None,
    "totalAssets()": None,
    "totalBorrow()": None,
    "totalDebt()": None,
    "exchangeRate()": None,
    "pricePerShare()": None,
    "getPrice(address)": None,
    "latestAnswer()": None,
    "latestRoundData()": None,
    "owner()": None,
    "admin()": None,
    "implementation()": None,
}

# Compute on import
for sig in COMMON_SELECTORS:
    try:
        COMMON_SELECTORS[sig] = fn_selector(sig)
    except ImportError:
        break


if __name__ == "__main__":
    print("Common selectors:")
    for sig, sel in COMMON_SELECTORS.items():
        print(f"  {sig:40s} → {sel}")

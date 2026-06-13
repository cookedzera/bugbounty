"""
Fetch verified contract source code from block explorers.
Supports Blockscout API v2 and Etherscan-compatible APIs (no key needed for Blockscout).
"""
import json
import requests
from typing import Optional

HEADERS = {"User-Agent": "hunt/1.0"}
TIMEOUT = 20

# Blockscout-compatible explorers
BLOCKSCOUT_EXPLORERS = {
    "ethereum": "https://eth.blockscout.com",
    "bsc": "https://bscscan.com",  # Not blockscout, use etherscan API
    "arbitrum": "https://arbitrum.blockscout.com",
    "optimism": "https://optimism.blockscout.com",
    "base": "https://base.blockscout.com",
    "polygon": "https://polygon.blockscout.com",
    "gnosis": "https://gnosis.blockscout.com",
    "sonic": "https://sonicscan.org",
    "flare": "https://flare-explorer.flare.network",
    "avalanche": "https://snowscan.xyz",
}

# Etherscan-compatible APIs (keyless limited but works)
ETHERSCAN_APIS = {
    "ethereum": "https://api.etherscan.io/api",
    "bsc": "https://api.bscscan.com/api",
    "arbitrum": "https://api.arbiscan.io/api",
    "optimism": "https://api-optimistic.etherscan.io/api",
    "base": "https://api.basescan.org/api",
    "polygon": "https://api.polygonscan.com/api",
    "avalanche": "https://api.snowscan.xyz/api",
}


def fetch_source_blockscout(chain: str, address: str) -> dict:
    """Fetch contract source from Blockscout API v2."""
    base = BLOCKSCOUT_EXPLORERS.get(chain)
    if not base:
        raise ValueError(f"No Blockscout explorer for chain: {chain}")
    
    url = f"{base}/api/v2/smart-contracts/{address}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    
    result = {
        "name": data.get("name", "Unknown"),
        "compiler": data.get("compiler_version", ""),
        "optimization": data.get("optimization_enabled", False),
        "runs": data.get("optimization_runs", 200),
        "is_proxy": data.get("is_proxy", False),
        "implementation": data.get("implementations", []),
        "source_code": data.get("source_code", ""),
        "abi": data.get("abi", []),
        "additional_sources": data.get("additional_sources", []),
        "verified": data.get("is_verified", False),
    }
    return result


def fetch_source_etherscan(chain: str, address: str) -> dict:
    """Fetch contract source from Etherscan-compatible API (keyless, rate-limited)."""
    base = ETHERSCAN_APIS.get(chain)
    if not base:
        raise ValueError(f"No Etherscan API for chain: {chain}")
    
    url = f"{base}?module=contract&action=getsourcecode&address={address}"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    
    if data.get("status") != "1" or not data.get("result"):
        return {"verified": False, "error": data.get("message", "Unknown error")}
    
    info = data["result"][0]
    is_proxy = info.get("Proxy") == "1"
    impl = info.get("Implementation", "")
    
    result = {
        "name": info.get("ContractName", "Unknown"),
        "compiler": info.get("CompilerVersion", ""),
        "optimization": info.get("OptimizationUsed") == "1",
        "runs": int(info.get("Runs", 200)),
        "is_proxy": is_proxy,
        "implementation": impl,
        "source_code": info.get("SourceCode", ""),
        "abi": json.loads(info.get("ABI", "[]")) if info.get("ABI") else [],
        "verified": bool(info.get("SourceCode")),
    }
    return result


def fetch_source(chain: str, address: str) -> dict:
    """Fetch contract source, trying Blockscout first, then Etherscan."""
    # Try Blockscout first (usually no rate limit)
    try:
        result = fetch_source_blockscout(chain, address)
        if result.get("verified") or result.get("source_code"):
            result["source"] = "blockscout"
            return result
    except Exception:
        pass
    
    # Fallback to Etherscan
    try:
        result = fetch_source_etherscan(chain, address)
        result["source"] = "etherscan"
        return result
    except Exception as e:
        return {"verified": False, "error": str(e), "source": "none"}


def get_proxy_implementation(chain: str, address: str) -> Optional[str]:
    """Check if address is a proxy and return implementation address.
    Reads EIP-1967 implementation slot.
    """
    from rpc_helpers import get_storage_at
    # EIP-1967 implementation slot
    IMPL_SLOT = "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    raw = get_storage_at(chain, address, IMPL_SLOT)
    if raw and raw != "0x" + "0" * 64:
        return "0x" + raw[-40:]
    return None


def list_functions(abi: list) -> list:
    """Extract function signatures from ABI."""
    fns = []
    for item in abi:
        if item.get("type") == "function":
            name = item["name"]
            inputs = ",".join(i["type"] for i in item.get("inputs", []))
            mutability = item.get("stateMutability", "nonpayable")
            fns.append({
                "name": name,
                "sig": f"{name}({inputs})",
                "mutability": mutability,
                "inputs": item.get("inputs", []),
                "outputs": item.get("outputs", []),
            })
    return fns


def find_fund_functions(abi: list) -> dict:
    """Categorize functions into fund-touching categories."""
    fns = list_functions(abi)
    categories = {
        "deposit": [],
        "withdraw": [],
        "borrow": [],
        "repay": [],
        "liquidate": [],
        "mint": [],
        "redeem": [],
        "transfer": [],
        "claim": [],
        "other_payable": [],
    }
    
    keywords = {
        "deposit": ["deposit", "supply", "stake", "addLiquidity", "addCollateral"],
        "withdraw": ["withdraw", "unstake", "removeLiquidity", "removeCollateral"],
        "borrow": ["borrow", "loan", "leverage"],
        "repay": ["repay", "payback", "payOff", "settle"],
        "liquidate": ["liquidat", "seize", "absorb"],
        "mint": ["mint"],
        "redeem": ["redeem", "burn"],
        "transfer": ["transfer", "send"],
        "claim": ["claim", "harvest", "collect", "getReward"],
    }
    
    for fn in fns:
        categorized = False
        for cat, kws in keywords.items():
            if any(kw.lower() in fn["name"].lower() for kw in kws):
                categories[cat].append(fn)
                categorized = True
                break
        if not categorized and fn["mutability"] == "payable":
            categories["other_payable"].append(fn)
    
    return {k: v for k, v in categories.items() if v}


if __name__ == "__main__":
    # Test: fetch a known contract (USDC on Ethereum)
    result = fetch_source("ethereum", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48")
    print(f"Contract: {result.get('name')}")
    print(f"Verified: {result.get('verified')}")
    print(f"Proxy: {result.get('is_proxy')}")
    if result.get("abi"):
        funds = find_fund_functions(result["abi"])
        for cat, fns in funds.items():
            print(f"  {cat}: {[f['sig'] for f in fns]}")

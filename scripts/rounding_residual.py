"""
A2 — Rounding Residual Loop (RRL) Algorithm

For each deposit/withdraw (or mint/redeem, borrow/repay) inverse pair,
compute the round-trip residual: f(g(x)) - x.
If residual > 0 for the attacker and cheaply loopable → flashloan mega-loop drain.

Usage:
  python rounding_residual.py <chain> <vault_address>
  
Reads totalAssets, totalSupply, then simulates deposit→withdraw round-trips
at various amounts to detect favorable rounding.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from rpc_helpers import eth_call, get_block_number
from selector_utils import encode_call, decode_uint256, fn_selector


def read_vault_state(chain: str, vault: str) -> dict:
    """Read basic vault state: totalAssets, totalSupply, decimals."""
    state = {}
    
    calls = {
        "totalAssets": encode_call("totalAssets()"),
        "totalSupply": encode_call("totalSupply()"),
        "decimals": encode_call("decimals()"),
        "totalDebt": encode_call("totalDebt()"),
    }
    
    for name, data in calls.items():
        try:
            result = eth_call(chain, vault, data)
            if result and result != "0x":
                state[name] = decode_uint256(result)
        except Exception:
            pass
    
    return state


def simulate_rounding_residual(total_assets: int, total_supply: int,
                                deposit_amount: int, decimals: int = 18) -> dict:
    """
    Simulate ERC-4626 deposit→withdraw round-trip.
    
    Deposit: shares = (amount * totalSupply) / totalAssets  (round down)
    Withdraw: assets = (shares * totalAssets) / totalSupply  (round down)
    
    Residual = deposit_amount - withdrawn_assets
    Attacker profit if residual < 0 (they get MORE back than deposited).
    """
    if total_assets == 0 or total_supply == 0:
        return {"error": "Empty vault — first-deposit attack vector (A5), not RRL"}
    
    # Deposit → shares (round down favors vault)
    shares_minted = (deposit_amount * total_supply) // total_assets
    
    if shares_minted == 0:
        return {"shares": 0, "residual": deposit_amount, "direction": "vault_keeps_all",
                "note": "Dust deposit — zero shares minted"}
    
    # Withdraw → assets (round down favors vault) 
    assets_withdrawn = (shares_minted * total_assets) // total_supply
    
    residual = deposit_amount - assets_withdrawn
    
    # Check the REVERSE: withdraw first, then deposit to cover
    # Withdraw: shares_needed = ceil(amount * totalSupply / totalAssets)
    # Deposit back: assets_needed = floor(shares * totalAssets / totalSupply)
    shares_for_withdraw = (deposit_amount * total_supply + total_assets - 1) // total_assets  # ceil
    assets_to_redeposit = (shares_for_withdraw * total_assets) // total_supply
    reverse_residual = assets_to_redeposit - deposit_amount
    
    return {
        "deposit_amount": deposit_amount,
        "shares_minted": shares_minted,
        "assets_withdrawn": assets_withdrawn,
        "residual_fwd": residual,  # >0 means vault profits, <0 means attacker profits
        "residual_rev": reverse_residual,
        "direction_fwd": "vault_profits" if residual > 0 else ("neutral" if residual == 0 else "ATTACKER_PROFITS"),
        "direction_rev": "vault_profits" if reverse_residual > 0 else ("neutral" if reverse_residual == 0 else "ATTACKER_PROFITS"),
        "loopable": residual < 0,  # Can attacker profit by looping?
    }


def sweep_amounts(total_assets: int, total_supply: int, decimals: int = 18) -> list:
    """Sweep across deposit amounts to find favorable rounding points."""
    results = []
    unit = 10 ** decimals
    
    # Test various amounts from dust to large
    test_amounts = [
        1,  # 1 wei
        10,
        100,
        1000,
        unit // 1000,  # 0.001 token
        unit // 100,   # 0.01 token
        unit // 10,    # 0.1 token
        unit,          # 1 token
        unit * 10,
        unit * 100,
        unit * 1000,
        unit * 10000,
        total_assets // 100 if total_assets > 100 else 1,  # 1% of vault
        total_assets // 10 if total_assets > 10 else 1,    # 10% of vault
    ]
    
    for amount in sorted(set(test_amounts)):
        if amount <= 0:
            continue
        r = simulate_rounding_residual(total_assets, total_supply, amount, decimals)
        if "error" not in r:
            results.append(r)
    
    return results


def analyze_vault(chain: str, vault: str) -> dict:
    """Full A2 RRL analysis of a vault."""
    state = read_vault_state(chain, vault)
    
    if "totalAssets" not in state or "totalSupply" not in state:
        return {"verdict": "SKIP", "reason": "Cannot read totalAssets/totalSupply — may not be ERC-4626"}
    
    decimals = state.get("decimals", 18)
    total_assets = state["totalAssets"]
    total_supply = state["totalSupply"]
    
    print(f"Vault state: totalAssets={total_assets}, totalSupply={total_supply}, decimals={decimals}")
    
    if total_assets == 0 or total_supply == 0:
        return {
            "verdict": "A5_VECTOR",
            "reason": "Empty vault — first-deposit inflation attack possible (NSMOT, not RRL)",
            "state": state,
        }
    
    results = sweep_amounts(total_assets, total_supply, decimals)
    
    attacker_profits = [r for r in results if r.get("loopable") or r.get("direction_rev") == "ATTACKER_PROFITS"]
    
    if attacker_profits:
        return {
            "verdict": "LIVE_LEAD",
            "reason": f"Found {len(attacker_profits)} amount(s) where attacker profits from round-trip",
            "profitable_amounts": attacker_profits,
            "state": state,
        }
    
    # Check if rounding is always exactly zero (custom math, not standard mulDiv)
    zero_residuals = [r for r in results if r["residual_fwd"] == 0 and r["residual_rev"] == 0]
    if len(zero_residuals) == len(results):
        return {
            "verdict": "CLEAN",
            "reason": "All round-trips have zero residual — 1:1 ratio or custom exact math",
            "state": state,
        }
    
    return {
        "verdict": "CLEAN",
        "kill_criterion": "All rounding favors vault (residual > 0)",
        "max_vault_profit_wei": max(r["residual_fwd"] for r in results),
        "state": state,
    }


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rounding_residual.py <chain> <vault_address>")
        print("Example: python rounding_residual.py ethereum 0x1234...")
        sys.exit(1)
    
    chain = sys.argv[1]
    vault = sys.argv[2]
    result = analyze_vault(chain, vault)
    
    import json
    print(json.dumps(result, indent=2, default=str))

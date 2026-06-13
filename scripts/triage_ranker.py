"""
Triage Ranker — Score and rank targets by Expected Value.

Scoring formula:
  EV = TVL_score × audit_score × chain_score × algo_depth × category_score

Where:
  TVL_score: log-scaled, peaks at $10-30M (sweet spot for naive bugs)
  audit_score: unaudited (aud=0) = 3.0, partial = 2.0, audited = 1.0
  chain_score: newer/less-tested chains score higher
  algo_depth: more applicable algorithms = more attack surface
  category_score: lending/CDP highest, yield next, then others
"""
import math
import json


def tvl_score(tvl_m: float) -> float:
    """TVL scoring: sweet spot $5-30M. Too small = low reward, too big = too-audited."""
    if tvl_m < 1:
        return 0.3
    elif tvl_m < 5:
        return 0.8 + (tvl_m - 1) * 0.05
    elif tvl_m <= 30:
        return 1.0  # Sweet spot
    elif tvl_m <= 60:
        return 0.9 - (tvl_m - 30) * 0.005
    else:
        return 0.7


def audit_score(audited: int) -> float:
    """0 = unaudited (best), 1 = partial, 2 = audited."""
    return {0: 3.0, 1: 2.0, 2: 1.0}.get(audited, 1.0)


def chain_score(chain: str) -> float:
    """Newer/less-battle-tested chains = more likely bugs."""
    scores = {
        "Fluent": 1.5,    # New L2, free gas amplifies rounding
        "Strato": 1.5,    # New chain
        "Mezo": 1.4,      # New chain
        "Flare": 1.3,     # Less tested
        "Monad": 1.3,     # New chain
        "Sonic": 1.2,
        "HL": 1.2,
        "Base": 1.1,
        "BNB": 1.0,
        "Ethereum": 1.0,
        "ETH": 1.0,
        "Arb": 1.0,
        "OP": 1.0,
    }
    # Handle multi-chain (e.g., "ETH/Arb")
    chains = chain.split("/")
    return max(scores.get(c.strip(), 1.0) for c in chains)


def algo_depth_score(algos: str) -> float:
    """More applicable algorithms = more attack surface explored."""
    algo_list = [a.strip() for a in algos.split(",")]
    n = len(algo_list)
    has_h = any(a.startswith("H") for a in algo_list)
    has_c = any(a.startswith("C") for a in algo_list)
    
    base = 1.0 + (n - 1) * 0.15  # Each extra algo adds 0.15
    if has_h:
        base += 0.3  # H-series = deeper analysis possible
    if has_c:
        base += 0.2  # C-series = cross-protocol/dynamic
    return min(base, 2.5)


def category_score(cat: str) -> float:
    """Fund-touching category weighting."""
    scores = {
        "Lending": 1.3,
        "CDP": 1.3,
        "Synthetics": 1.2,
        "Yield": 1.1,
        "Yield Agg": 1.1,
        "Derivatives": 1.2,
        "Options": 1.2,
        "Insurance": 1.0,
        "Algo-Stables": 1.1,
    }
    return scores.get(cat, 1.0)


def rank_targets(targets: list) -> list:
    """Score and rank all targets. Each target is a dict with keys:
    num, name, cat, tvl_m, chain, algos, hypothesis, audited (0/1/2)
    """
    scored = []
    for t in targets:
        tv = tvl_score(t["tvl_m"])
        au = audit_score(t["audited"])
        ch = chain_score(t["chain"])
        al = algo_depth_score(t["algos"])
        ca = category_score(t["cat"])
        
        ev = tv * au * ch * al * ca
        
        scored.append({
            **t,
            "scores": {
                "tvl": round(tv, 2),
                "audit": round(au, 2),
                "chain": round(ch, 2),
                "algo_depth": round(al, 2),
                "category": round(ca, 2),
            },
            "ev_score": round(ev, 2),
        })
    
    scored.sort(key=lambda x: x["ev_score"], reverse=True)
    
    for i, t in enumerate(scored):
        t["rank"] = i + 1
    
    return scored


# ── Target Data ──
TARGETS = [
    {"num": 1, "name": "Vena Finance", "cat": "Lending", "tvl_m": 22.7, "chain": "Fluent", "algos": "A3,A2,H1", "audited": 0,
     "hypothesis": "per-asset oracle scaling + borrow/repay round-trip residual (Fluent free gas makes the loop pay)"},
    {"num": 2, "name": "STRATO", "cat": "CDP", "tvl_m": 17.3, "chain": "Strato", "algos": "A3,C2", "audited": 0,
     "hypothesis": "thin-chain peg oracle off a low-liq DEX TWAP → manipulate-then-mint"},
    {"num": 3, "name": "Avalon Superearn", "cat": "Yield", "tvl_m": 30.4, "chain": "Ethereum", "algos": "A1,A4,A5,H2", "audited": 0,
     "hypothesis": "BTC-yield PPS desync; inner unprotected strategy vault; multi-step state-machine check"},
    {"num": 4, "name": "Royco V2", "cat": "Yield", "tvl_m": 15.9, "chain": "ETH/Arb", "algos": "A1,A4", "audited": 0,
     "hypothesis": "IOU/reward var across market-hub→wrapped-vault hops"},
    {"num": 5, "name": "Usual ETH0", "cat": "Synthetics", "tvl_m": 4.0, "chain": "Ethereum", "algos": "A2,A3", "audited": 0,
     "hypothesis": "mint⇔redeem residual + collateral-ratio decimals"},
    {"num": 6, "name": "Enosys Loans", "cat": "CDP", "tvl_m": 9.6, "chain": "Flare", "algos": "A3", "audited": 0,
     "hypothesis": "Flare FTSO oracle decimals/staleness/fallback"},
    {"num": 7, "name": "Venus Flux", "cat": "Lending", "tvl_m": 12.3, "chain": "BNB", "algos": "A3,A1,C4", "audited": 0,
     "hypothesis": "fork's unsupported-collateral fault + bad-debt socialization"},
    {"num": 8, "name": "Mezo Borrow", "cat": "CDP", "tvl_m": 6.2, "chain": "Mezo", "algos": "A3,C3", "audited": 0,
     "hypothesis": "Liquity-fork redemption hint-list ordering + BTC oracle fallback"},
    {"num": 9, "name": "Nerona", "cat": "Yield Agg", "tvl_m": 5.5, "chain": "Fluent", "algos": "A5,A2", "audited": 0,
     "hypothesis": "first-deposit inflation + withdraw rounding"},
    {"num": 10, "name": "RockSolid Network", "cat": "Yield", "tvl_m": 19.8, "chain": "Ethereum", "algos": "A1,A5", "audited": 0,
     "hypothesis": "loss-report/PPS update; strategy accounting"},
    {"num": 11, "name": "Lazy", "cat": "Yield", "tvl_m": 1.0, "chain": "Ethereum", "algos": "A2,A5", "audited": 0,
     "hypothesis": "totalAssets() source-of-truth + auto-compound rounding"},
    {"num": 12, "name": "Twyne", "cat": "Lending", "tvl_m": 1.5, "chain": "Ethereum", "algos": "A1,A4,C5", "audited": 2,
     "hypothesis": "credit-vault cross-contract invariant; upgrade seam"},
    {"num": 13, "name": "Alchemix V3", "cat": "Synthetics", "tvl_m": 29.8, "chain": "ETH/OP/Arb", "algos": "A1,A4,H6", "audited": 2,
     "hypothesis": "fresh V3 transmuter accounting; diff deployed vs audited"},
    {"num": 14, "name": "Flying Tulip Lend", "cat": "Lending", "tvl_m": 4.0, "chain": "ETH/Sonic", "algos": "A3,C2,H3", "audited": 2,
     "hypothesis": "bespoke AMM-oracle manipulability; game-theoretic deviation"},
    {"num": 15, "name": "Tangent Finance", "cat": "Lending", "tvl_m": 3.3, "chain": "Ethereum", "algos": "A3,A2", "audited": 2,
     "hypothesis": "e-mode correlated-collateral LTV"},
    {"num": 16, "name": "Fira", "cat": "Lending", "tvl_m": 7.8, "chain": "Ethereum", "algos": "A1,C4", "audited": 2,
     "hypothesis": "liquidation-bonus/close-factor rounding; adversarial liquidation"},
    {"num": 17, "name": "Hypersurface", "cat": "Options", "tvl_m": 3.5, "chain": "HL/Base", "algos": "A4,H3", "audited": 2,
     "hypothesis": "settlement payoff/collateral release; IV oracle"},
    {"num": 18, "name": "Cozy Earn", "cat": "Insurance", "tvl_m": 1.7, "chain": "Ethereum", "algos": "A5,A1", "audited": 2,
     "hypothesis": "partial-trigger payout vs reserve share math"},
    {"num": 19, "name": "Generic.Money", "cat": "Algo-Stables", "tvl_m": 1.2, "chain": "Ethereum", "algos": "A2,A3", "audited": 2,
     "hypothesis": "mint/redeem peg arbitrage"},
    {"num": 20, "name": "Curvance", "cat": "Lending", "tvl_m": 55.4, "chain": "Monad", "algos": "A1,A4,H5", "audited": 2,
     "hypothesis": "cross-chain msg→collateral invariant; message causality/reorg"},
]


def main():
    ranked = rank_targets(TARGETS)
    
    print("=" * 100)
    print("FUND-CRITICAL BUG HUNT — TARGET RANKING BY EXPECTED VALUE")
    print("=" * 100)
    print()
    
    print(f"{'Rank':<5} {'#':<4} {'Name':<22} {'Cat':<14} {'TVL':<8} {'Chain':<12} {'Aud':<5} {'Algos':<16} {'EV':>6}")
    print("-" * 100)
    
    for t in ranked:
        aud_label = {0: "No", 1: "Part", 2: "Yes"}[t["audited"]]
        print(f"{t['rank']:<5} {t['num']:<4} {t['name']:<22} {t['cat']:<14} ${t['tvl_m']:<7.1f} {t['chain']:<12} {aud_label:<5} {t['algos']:<16} {t['ev_score']:>6.2f}")
    
    print()
    print("=" * 100)
    print("TOP 5 RECOMMENDED HUNT ORDER:")
    print("=" * 100)
    for t in ranked[:5]:
        print(f"\n  #{t['rank']} {t['name']} (EV: {t['ev_score']:.2f})")
        print(f"     TVL: ${t['tvl_m']}M | Chain: {t['chain']} | Audited: {'No' if t['audited']==0 else 'Yes'}")
        print(f"     Algos: {t['algos']}")
        print(f"     Hypothesis: {t['hypothesis']}")
        s = t['scores']
        print(f"     Score breakdown: TVL={s['tvl']} × Audit={s['audit']} × Chain={s['chain']} × AlgoDepth={s['algo_depth']} × Cat={s['category']}")


if __name__ == "__main__":
    main()

# AGENT HANDOFF — Fund-Critical Smart-Contract Bug Hunt

> **Read this first.** This file exists so the next AI/agent does **not** waste time
> re-researching what's already been done. It captures current state, what's been
> ruled out, hard-won learnings, tooling gotchas, and the highest-EV next moves.
> Last updated: 2026-06-13.

---

## 0. Mission
Find **fund-critical** bugs (direct theft / drain / unbacked mint / permanent freeze of
user funds). Ignore gas griefing, centralization-by-design, and info findings.
**Never claim a bug without a runnable proof artifact.** Report verdicts honestly as
`CLEAN` / `RESIDUAL` / `LIVE LEAD`. Do **not** manufacture bugs.

## 1. What has already been done (DON'T REDO)

### Deep hunts completed — ALL CLEAN
| Target | Type | Verdict | Why clean |
|--------|------|---------|-----------|
| **Vena Finance** (Fluent) | Lending | CLEAN core / RESIDUAL oracle | Custom oracle layer defensively written; canonical Aave core |
| **Generic.Money (GUSD)** | ERC-7575 omnichain stablecoin (~6.9k LoC) | CLEAN core / RESIDUAL deps | Tight mint/redeem accounting; residual = external integrations |
| **Royco V2 "Dawn"** (~8.6k LoC) | Structured tranching | CLEAN / RESIDUAL | Certora formal verification + 3× Hexens + Cantina; typed-unit math; slow (non-spot) price feeds |

Full per-target reasoning is in `methodology/hunt_log.md`. PDF reports in `reports/`.

### Dead/skipped targets (see `methodology/dead_targets.md`)
- **STRATO** — not public EVM (BlockApps/Mercata SolidVM). SKIP.
- **Avalon Superearn** — actually audited. Deprioritize.
- **Nerona** — thin bespoke surface. Lower priority.
- Also dead: 3F, Ledgity, Acre, Altitude V2, mStable V2, Antarctic, StableHodl.

### Scanner built + run
`scripts/arbitrary_call_scanner.py` — keyless Blockscout enumeration of recently-verified
contracts + F1 (arbitrary-call drain) and F4 (unguarded signer/allowlist setter) detectors.
**Run on Base (300) + Ethereum (300) = 600 contracts → only false positives** (admin
`rescueToken`/`withdrawNative` sweeps to hardcoded treasuries; one contract literally named
`AllInOneExploit` = an attacker's own contract).

## 2. THE key strategic learning (this is the whole game)

> **3 deep hunts on well-engineered / audited flagships were all CLEAN.**
> **The real 2026 hack victims were SMALL, UNAUDITED, CLOSED-SOURCE, or LEGACY contracts** —
> SwapNet ($13.4M), Aperture ($4M), TrustedVolumes ($6.7M), Transit, Truebit ($26M).
> **You are hunting in the wrong neighborhood if you pick formally-verified flagships.**

Corollaries:
- **Random-recent-verified-contract scanning has ~0 hit rate.** Fresh verifications skew to
  tokens / proxies / test / scam. Real vulnerable routers are **older** (already audited or
  already drained). To find F1 this way you'd need to scan **tens of thousands**, OR — much
  better — **seed the scanner with known router/aggregator/zap addresses** and diff vs their
  audited equivalents.
- Most mega-hacks (Bybit $1.4B, Resolv, Infini, THORChain) were **key/infra/social
  compromises, NOT code bugs** → not huntable by source review. Don't chase these.

## 3. The 6 huntable code-bug fingerprints (full detail: `methodology/hack_fingerprints_2026.md`)
- **F1 Arbitrary-call + weak validation** (MOST FREQUENT 2026): router/zap does
  `target.call(data)` with user-controlled `target` → set target=token, data=`transferFrom(victim,attacker)`
  → drain standing approvals. *Provable without stealing.*
- **F2 Unbacked / mispriced mint** (Truebit, Meta Pool mpETH).
- **F3 Bridge input ≠ output** (Verus-ETH, TAC, SagaEVM).
- **F4 Missing access control on signer/allowlist** (TrustedVolumes, RetoSwap).
- **F5 Legacy / deprecated-but-funded contract** (Truebit, Transit).
- **F6 Round-trip LP loop** (TMX).

## 4. Highest-EV NEXT MOVES (do these, in order)
1. **Seed-based F1 hunt** (best EV): collect known router/aggregator/zap/"execute"/"multicall"
   adapter addresses across Base/ETH/Arbitrum/BNB (from DexScreener, 1inch/0x/LiFi/Socket
   integrators, new DEX launches). Fetch source, run the F1 detector, and for any low-level
   call with a user-controlled target **confirm there is no allowlist/validation** and that
   standing approvals exist. PoC = `eth_call` simulating `transferFrom` via the call path.
2. **F5 legacy sweep**: find deprecated-but-still-funded contracts (old router versions,
   migration contracts) with leftover approvals/balances.
3. **F4 sweep on small/new protocols**: grep for `addSigner`/`setOperator`/`addToWhitelist`/
   `grantRole`-style setters missing `onlyOwner`/`onlyRole`/`require(msg.sender...)`.
4. Only after the above: vet a specific named small/unaudited protocol from
   `methodology/target_list.md` (Tier A, unaudited, $1M–$50M TVL).

## 5. Tooling gotchas (sandbox-specific — save yourself hours)
- **Blockscout API is keyless.** List: `{explorer}/api/v2/smart-contracts?filter=solidity`
  (paginate via `next_page_params`, newest first). Source:
  `{explorer}/api/v2/smart-contracts/{addr}` → `source_code` + `additional_sources`.
  Explorers: `https://base.blockscout.com`, `https://eth.blockscout.com`,
  `optimism/arbitrum/gnosis.blockscout.com`. Send a `User-Agent` header.
- **Long scans exceed the 60s tool cap.** Run detached: `nohup uv run python scanner.py base 300 > out.txt 2>err.txt & disown`, then poll the output file. Each source fetch = 1 HTTP call.
- **Foundry is NOT installable** (downloads blocked) and `uv.lock` is read-only. Use raw
  `eth_call` via `scripts/rpc_helpers.py` and pure-Python ray-math instead of `cast`/`forge`.
- **keccak256:** use `scripts/selector_utils.keccak256()` (auto-falls back to a python3.12
  subprocess for `pycryptodome`). Do NOT use `hashlib.sha3_256` — it is ≠ EVM keccak.
- **Keyless RPCs:** `eth.merkle.io`, `{chain}-rpc.publicnode.com`, `{chain}-pokt.nodies.app`
  (need `User-Agent` header).
- **web_search is async** and returns generic listings — useless for pinpointing soft targets.
  Use on-chain enumeration instead.

## 6. The hunting prompt (paste to any agent)
> You are an elite fund-critical smart-contract bug hunter. Work one target at a time,
> depth > breadth. For each target: (1) find the REAL fund-holding contract (use DefiLlama
> adapters, docs, or a deposit tx — not the gov token); (2) confirm verified source, check
> `/audits`, cross-check Immunefi; (3) state the core conservation invariants; (4) run the
> tagged algorithms (see `methodology/CODEX.md`) and report a verdict (CLEAN / RESIDUAL /
> LIVE LEAD with a runnable proof artifact). Bias targets to SMALL / UNAUDITED / LEGACY —
> not audited flagships. Never claim a bug without runnable proof.

## 7. Repo map
- `methodology/CODEX.md` — full methodology: target filter, A/C/H algorithm library, meta-method for inventing algorithms.
- `methodology/hack_fingerprints_2026.md` — the 6 fingerprints with real-hack provenance.
- `methodology/target_list.md` — 20 ranked targets (Tier A unaudited / Tier B audited).
- `methodology/dead_targets.md` — already-triaged, don't re-dive.
- `methodology/hunt_log.md` — per-target verdicts + full reasoning from completed hunts.
- `scripts/` — scanner + RPC/source-fetch/selector/storage/round-trip/triage helpers.
- `reports/` — PDF hunt reports.

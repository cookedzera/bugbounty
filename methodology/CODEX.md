---
name: smart_contract_hunting
description: Fund-critical smart-contract bug hunting methodology. Algorithms (A/C/H series), target selection, tooling, and reusable prompts for DeFi vulnerability research.
---

# Fund-Critical Bug-Hunt Codex

## Role & Rules
Hunt **only fund-critical** bugs (direct theft / drain / mint / permanent freeze of user funds). Skip gas-griefing, centralization-by-design, info findings unless asked.

## Target Selection Filter (best EV)
- NOT on Immunefi (unbountied)
- TVL $1M–$50M
- Listed <12 months
- Fund-touching category: Lending / CDP / Yield / Derivatives / Synthetics
- EVM with verified source
- Small + self-coded + real money = naive bugs live here
- Deprioritize: RWA/off-chain-custody vaults (tiny on-chain surface)

## Tooling (keyless)
- **RPCs:** `eth.merkle.io`, `{chain}-rpc.publicnode.com`, `{chain}-pokt.nodies.app` (need `User-Agent` header)
- **Foundry:** `forge`/`cast`/`anvil` — install with `foundryup`
- **Blockscout API:** `https://<explorer>/api/v2/smart-contracts/{addr}` — returns source + implementations, no key
- **Python:** `pdfplumber` for audit PDFs, `pycryptodome` `Crypto.Hash.keccak` for selectors

## Hunting Prompt (paste to any agent)
> You are an elite fund-critical smart-contract bug hunter. Work one target at a time, depth > breadth.
> For each target: (1) find the REAL fund-holding contract (not gov token — use DefiLlama adapters, docs, or deposit-tx); (2) confirm verified source + check `/audits` + cross-check Immunefi; (3) state core conservation invariants; (4) run tagged algorithms and report verdict (CLEAN / RESIDUAL / LIVE LEAD with proof artifact). Never claim a bug without runnable proof.

## Algorithm Library

### A-Series (static-structural)
- **A1 SWSD:** Map each fn's read/write-set → var X updates but Y reads without updating → accounting desync
- **A2 RRL:** Round-trip residual `f(g(x))−x` per inverse pair → >0 for attacker + cheaply loopable → drain
- **A3 CDDS:** Enumerate every feed's decimals()/base-asset → bug when Nth token listed post-audit on path validated only for 18-dec
- **A4 VCRP:** CEI-violating mutator + view reading half-updated state + consumer trusting mid-callback = triple bug
- **A5 NSMOT:** OZ virtual-shares protects outer vault; donation/inflation lives one accounting layer down

### C-Series (dynamic / cross-protocol / time / MEV)
- **C1:** Undocumented-invariant fuzzing (Foundry invariant tests)
- **C2:** Cross-protocol composability seam (manipulate external rate target trusts)
- **C3:** Epoch/block-boundary sandwich (lastUpdated/checkpoint/TWAP vars)
- **C4:** Adversarial liquidation / forced bad-debt
- **C5:** Init/upgrade/storage-layout seam
- **C6:** Intent/signature completeness (does hash bind ALL economic fields?)
- **C7:** External-balance poison (`balanceOf(address(this))` as accounting truth)

### H-Series (frontier, tool-heavy)
- **H1:** Symbolic round-trip equivalence proving (SMT/Z3 via halmos/hevm)
- **H2:** Bounded model-checking of state machine (conservation invariant reachability)
- **H3:** Game-theoretic profit-maximization solver (LP/MILP/convex)
- **H4:** Storage-slot aliasing & diamond-collision differential
- **H5:** Cross-chain message causality / reorg-atomicity break
- **H6:** Invariant-guided differential bytecode execution (deployed vs audited)

## Inventing New Algorithms (meta-method)
1. Start from an invariant, not a function
2. Aim at a dimension audits under-cover (composition, time, future state, economics, deployed-vs-audited)
3. Reverse a real hack into a fingerprint
4. Make it mechanical — yields a runnable artifact (grep, Foundry test, eth_call, bytecode diff)
5. Define kill-criterion up front for fast CLEAN verdicts
6. Compose two known bug-classes: most novel criticals = bug-A under condition of bug-B

## Antarctic Fingerprint (worked example)
Sibling contracts per asset/pool → shared admin signer → custom (non-EIP-712) signed message missing `address(this)` + `block.chainid` → one sig replays across every sibling/chain → N× payout.
**Prove-without-stealing PoC:** Pull historic tx, decode calldata, recover signer, `eth_call` same calldata against replay-target at original block (impersonating original `from`). Success proves replay path with zero state change.

## Scripts
- `scripts/rpc_helpers.py` — RPC call utilities
- `scripts/contract_fetcher.py` — Fetch verified source from Blockscout/Etherscan
- `scripts/selector_utils.py` — Function selector computation
- `scripts/storage_layout.py` — Storage layout analysis (requires Foundry)
- `scripts/rounding_residual.py` — A2 RRL algorithm implementation
- `scripts/triage_ranker.py` — Score and rank targets by EV

## References
- `references/target_list.md` — Current 20-target list with tiers and hypotheses
- `references/dead_targets.md` — Already-triaged dead targets (don't re-dive)
- `references/hunt_log.md` — Per-target verdicts from completed live hunts

## Environment / Tooling Gotchas (sandbox)
- **keccak256:** uv's Python 3.13 env lacks `pycryptodome`; `Crypto.Hash.keccak` lives only in `python3.12`. `selector_utils.keccak256()` auto-falls back to a `python3.12` subprocess — works without changes. Do NOT trust `hashlib.sha3_256` (≠ EVM keccak).
- **Foundry not installed**; `uv add`/`uv.lock` is read-only (Permission denied). For on-chain probing use raw `eth_call` via `rpc_helpers` instead of `cast`. A2 round-trips can be simulated in pure Python (ray-math) — no forge needed.
- **Aave V3 forks:** read `Pool` impl `additional_sources` file paths first — canonical `@aave/...` paths = unmodified core (skip, it's audited); only files under `contracts/` (non-`hardhat-dependency-compiler`) are bespoke and worth diffing. `PoolConfiguratorV2`/`EmptyContract`-type files are usually just revision bumps/build stubs.
- **Custom Pyth/Chainlink adapters are the real surface in oracle-fork lenders.** Check: does `latestAnswer()` apply the feed exponent, or return raw price assuming a fixed decimals? AaveOracle assumes BASE_CURRENCY_UNIT decimals for ALL feeds — an unvalidated `exponent==-8` assumption is a latent A3 decimal bug that detonates on the next asset listing. Also check `decimals()` is constant vs dynamically read from latest entry.
- **Verdict discipline:** report CLEAN/RESIDUAL honestly. A defensively-written custom layer + canonical core = no bug; don't manufacture one. Latent risks are RESIDUAL, not LIVE LEAD, unless attacker-triggerable at current on-chain state.

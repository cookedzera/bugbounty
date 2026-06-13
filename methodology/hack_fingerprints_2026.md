# 2025–2026 Hack Fingerprints (for target/loophole hunting)

Distilled from real incidents. Split into KEY-THEFT (not huntable via code) vs CODE-BUG (huntable). Hunt the code-bug fingerprints.

## NOT huntable (key/infra/social — skip)
Raydium 2022 (admin key → withdrawPNL drain), Resolv USR Mar-2026 ($25M, AWS KMS key, no max-mint limit), Infini ($50M role/key), Bybit ($1.4B UI/Safe JS injection), Step Finance ($30M wallets), THORChain (validator key leak), Trezor victim ($282M social). Lesson: most $ lost = trust-point compromise, not code. We don't hunt these.

## CODE-BUG fingerprints (HUNT THESE)

### F1 — Arbitrary-call + insufficient input validation (MOST FREQUENT 2026)
Incidents: SwapNet $13.4M, Aperture Finance $4M (Jan-26), Ekubo $1.4M, Transit Finance $1.88M (May-26).
Mechanism: a router/aggregator/zap/"recipe"/swap-executor does a low-level `target.call(data)` where `target` and/or `data` are user-supplied and under-validated. Attacker sets `target = USDC` (or any token already approved to the victim contract) and `data = transferFrom(victim, attacker, amt)`. Drains all standing approvals. Aperture: replacing expected router/pool addr with a token addr; contract treats token as valid execution target.
HUNT: grep periphery for `.call(`, `.delegatecall(`, `functionCall(` with a `target` param flowing from calldata. Confirm no allowlist on target AND no selector restriction. Check whether the contract holds long-lived ERC20 approvals (or users approve it). Prove via decoded calldata + eth_call (token.transferFrom path) — no theft needed.
TARGET CLASSES: Weiroll/recipe VMs, zappers, 1inch-style aggregators, "universal router" clones, LP-automation managers, cross-chain "execute arbitrary action" adapters.

### F2 — Unbacked / free / mispriced mint
Incidents: Truebit $26M (Jan-26, pricing-math: huge mint with crafted msg.value → getPurchasePrice returns ~0 → mint cheap, sell to bonding curve), Meta Pool $27M (mpETH minted w/o ETH collateral), Resolv (key, but contract lacked max-mint/oracle/amount validation).
Mechanism: mint price/amount math is manipulable (crafted msg.value, rounding, missing oracle/amount check) → acquire token below value → redeem/sell at full value. = codex A2 (mint⇔redeem residual) + A3 (decimals/oracle).
HUNT: every mint path — does cost scale correctly with amount? any msg.value-dependent pricing with rounding? missing max-mint cap / oracle / amount>0? legacy mint contract still funded? Verify mint cost rounds protocol-favoring (Ceil) and redeem payout (Floor).

### F3 — Bridge input≠output / cross-chain causality
Incidents: Verus-ETH $11.58M ("neither end validated tx inputs matched outputs"), TAC TON/EVM $2.8M (Jetton bridge path logic), SagaEVM $7M (inherited Ethermint precompile bridge).
Mechanism: each side verifies its own step but no invariant binds source-burn == dest-mint (amount/recipient/token). = codex H5.
HUNT: does the inbound settler bind {amount, token, recipient, srcChain} to the outbound commitment? replay guard? inherited precompile/legacy bridge code?

### F4 — Missing access control on allowlist/signer set
Incidents: TrustedVolumes $6.7M (attacker added self to approved order signers), RetoSwap (named self arbitrator).
Mechanism: a function that mutates the trusted signer/arbitrator/allowlist set lacks onlyOwner/role gate → attacker self-authorizes.
HUNT: grep setters that add to signer/allowlist/role mappings; confirm each has access modifier.

### F5 — Legacy/deprecated-but-active contract
Incidents: Truebit (5-yr-old contract, still funded), Transit Finance (deprecated legacy still callable, weak validation).
Mechanism: old contract never decommissioned, holds funds/approvals, weak modern validation.
HUNT: enumerate a protocol's old deployments still holding balances/approvals; weakest validation lives there.

### F6 — Round-trip loop (LP mint/stake/swap/unstake)
Incident: TMX $1.4M (mint LP w/ USDT, swap USDC→USDG, unstake, sell USDG in a loop).
Mechanism: pricing/fee asymmetry across mint-LP vs redeem/sell makes a repeatable loop net-positive. = codex A2 RRL.
HUNT: any asset that can enter as one valuation and exit at another within a loop, fees < spread.

## Best fingerprint→target mapping on current list
- **F1 (arbitrary-call)** → **Royco V2** (#4): recipe/Weiroll-style market execution = prime arbitrary-call/approval-drain surface. TOP huntable pick.
- **F2 (free-mint)** → **Usual ETH0** (#5) mint⇔redeem; Generic.Money (DONE-clean).
- **F3 (bridge)** → **Curvance** (#20) cross-chain msg→collateral; Generic bridging (DONE-clean).

# Target List (2026-06-12)

## Dead Targets (already triaged — don't re-dive)
3F, Ledgity, Acre, Altitude V2, mStable V2, Antarctic, StableHodl

## Tier A — Unaudited (aud=0), highest EV

| # | Target | Cat | TVL | Chain | Algo | Hypothesis |
|---|--------|-----|-----|-------|------|-----------|
| 1 | Vena Finance | Lending | $22.7M | Fluent | A3,A2,H1 | per-asset oracle scaling + borrow/repay round-trip residual (Fluent free gas makes the loop pay) |
| 2 | STRATO | CDP | $17.3M | Strato | A3,C2 | thin-chain peg oracle off a low-liq DEX TWAP → manipulate-then-mint |
| 3 | Avalon Superearn | Yield | $30.4M | Ethereum | A1,A4,A5,H2 | BTC-yield PPS desync; inner unprotected strategy vault; multi-step state-machine check |
| 4 | Royco V2 | Yield | $15.9M | ETH/Arb | A1,A4 | IOU/reward var across market-hub→wrapped-vault hops |
| 5 | Usual ETH0 | Synthetics | $4.0M | Ethereum | A2,A3 | mint⇔redeem residual + collateral-ratio decimals |
| 6 | Enosys Loans | CDP | $9.6M | Flare | A3 | Flare FTSO oracle decimals/staleness/fallback |
| 7 | Venus Flux | Lending | $12.3M | BNB | A3,A1,C4 | fork's unsupported-collateral fault + bad-debt socialization |
| 8 | Mezo Borrow | CDP | $6.2M | Mezo | A3,C3 | Liquity-fork redemption hint-list ordering + BTC oracle fallback |
| 9 | Nerona | Yield Agg | $5.5M | Fluent | A5,A2 | first-deposit inflation + withdraw rounding |
| 10 | RockSolid Network | Yield | $19.8M | Ethereum | A1,A5 | loss-report/PPS update; strategy accounting |
| 11 | Lazy | Yield | $1.0M | Ethereum | A2,A5 | totalAssets() source-of-truth + auto-compound rounding |

## Tier B — Audited (aud=2), audit-gap + post-audit algorithms

| # | Target | Cat | TVL | Chain | Algo | Hypothesis |
|---|--------|-----|-----|-------|------|-----------|
| 12 | Twyne | Lending | $1.5M | Ethereum | A1,A4,C5 | credit-vault cross-contract invariant; upgrade seam |
| 13 | Alchemix V3 | Synthetics | $29.8M | ETH/OP/Arb | A1,A4,H6 | fresh V3 transmuter accounting; diff deployed vs audited |
| 14 | Flying Tulip Lend | Lending | $4.0M | ETH/Sonic | A3,C2,H3 | bespoke AMM-oracle manipulability; game-theoretic deviation |
| 15 | Tangent Finance | Lending | $3.3M | Ethereum | A3,A2 | e-mode correlated-collateral LTV |
| 16 | Fira | Lending | $7.8M | Ethereum | A1,C4 | liquidation-bonus/close-factor rounding; adversarial liquidation |
| 17 | Hypersurface | Options | $3.5M | HL/Base | A4,H3 | settlement payoff/collateral release; IV oracle |
| 18 | Cozy Earn | Insurance | $1.7M | Ethereum | A5,A1 | partial-trigger payout vs reserve share math |
| 19 | Generic.Money | Algo-Stables | $1.2M | Ethereum | A2,A3 | mint/redeem peg arbitrage |
| 20 | Curvance | Lending | $55.4M | Monad | A1,A4,H5 | cross-chain msg→collateral invariant; message causality/reorg |

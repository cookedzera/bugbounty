
## Recon notes (2026-06-13) — targets to skip/deprioritize
- **STRATO (#2)** — NOT a public EVM chain. Runs on BlockApps/Mercata (SolidVM), accessed via OAuth + Cirrus REST/SQL layer; registries at 0x...100x addresses. No public verified source, no keyless eth_call. NOT huntable with keyless EVM tooling → SKIP.
- **Avalon Superearn (#3)** — actually AUDITED (Spearbit, Cantina Managed, CertiK; 2026 reports at github.com/superearn-io/superearn-audit-reports). Tier-A "aud=0" was wrong. Deprioritize (audit-gap only).
- **Nerona (#9)** — thin bespoke surface: USDnr is 1:1 RWA-backed by M0 wM (T-bill token); yield vault sUSDnr is a third-party Upshift ERC-4626. Most code is external. Lower P(bespoke bug). Redemption via wM/USDC Uniswap V3 pool on ETH.

## Usual ETH0 (2026-06-13) — HUNTED, CLEAN core / RESIDUAL oracle
wstETH-only synthetics; LidoProxyWstETHPriceFeed hardcodes stETH:ETH=1:1 (RESIDUAL depeg, by-design). Floor-rounded math, no free-mint round-trip. Don't re-dive unless new non-wstETH collateral added. See hunt_log.md.

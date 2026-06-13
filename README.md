# bugbounty

Fund-critical smart-contract bug-hunting research, methodology, and tooling.

> **New agent or AI picking this up? → Read [`AGENT_HANDOFF.md`](./AGENT_HANDOFF.md) first.**
> It tells you exactly what's done, what's ruled out, what to do next, and the tooling
> gotchas — so you don't waste time re-researching.

## What's here
| Path | What |
|------|------|
| [`AGENT_HANDOFF.md`](./AGENT_HANDOFF.md) | **Start here.** State of the hunt + next moves + gotchas. |
| [`methodology/CODEX.md`](./methodology/CODEX.md) | Full methodology: target-selection filter, A/C/H algorithm library, meta-method. |
| [`methodology/hack_fingerprints_2026.md`](./methodology/hack_fingerprints_2026.md) | The 6 huntable code-bug fingerprints (F1–F6) distilled from real 2026 hacks. |
| [`methodology/target_list.md`](./methodology/target_list.md) | 20 ranked targets (Tier A unaudited / Tier B audited). |
| [`methodology/dead_targets.md`](./methodology/dead_targets.md) | Already-triaged dead targets — don't re-dive. |
| [`methodology/hunt_log.md`](./methodology/hunt_log.md) | Per-target verdicts + full reasoning. |
| [`scripts/`](./scripts/) | Keyless scanner + RPC/source/selector/storage helpers. |
| [`reports/`](./reports/) | PDF hunt reports. |

## Methodology in one line
Hunt **fund-critical** bugs only. Bias to **small / unaudited / legacy** contracts (that's
where 2026's real victims were), not audited flagships. Report `CLEAN` / `RESIDUAL` /
`LIVE LEAD` honestly. **Never claim a bug without a runnable proof artifact.**

## Quickstart — arbitrary-call (F1) scanner
```bash
# keyless; enumerates recently-verified contracts on a chain and flags F1/F4 fingerprints
python scripts/arbitrary_call_scanner.py base 300     # or: eth / arbitrum / optimism / gnosis
```
Long scans exceed short tool timeouts — run detached:
```bash
nohup python scripts/arbitrary_call_scanner.py eth 300 > out.txt 2>err.txt & disown
```

## Status (2026-06-13)
3 deep hunts done (Vena, Generic.Money, Royco V2) — all **CLEAN** (all were well-audited).
Scanner run on Base + ETH (600 contracts) — only false positives. **Key learning: random
recent-contract scanning ≈ 0 hit rate; seed with known router/aggregator addresses instead.**
See `AGENT_HANDOFF.md` §2 and §4.

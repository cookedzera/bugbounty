#!/usr/bin/env python3
"""
Arbitrary-call (F1) + missing-access-control (F4) scanner.

Enumerates recently-verified contracts from a Blockscout instance (keyless),
fetches source, and flags two fund-critical fingerprints:

  F1: an externally-callable function forwards a USER-CONTROLLED `address` target
      + `bytes` calldata into a low-level call (`target.call(data)` /
      `target.functionCall(data)` / `.call{value:}`), enabling
      `token.transferFrom(victim, attacker, amt)` drains of standing approvals.
      (SwapNet $13.4M, Aperture $4M, Ekubo, Transit — Jan/May 2026.)

  F4: a function mutates a signer/operator/allowlist/role mapping with NO access
      modifier (onlyOwner/onlyRole/require(msg.sender...)).
      (TrustedVolumes $6.7M — May 2026.)

Usage: python arbitrary_call_scanner.py <base|eth|...> [max_contracts]
Output: ranked candidates (address, balance, txcount, fingerprint, snippet).

This is a TRIAGE tool — flagged contracts need manual confirmation
(does the target lack an allowlist? are there real standing approvals?).
"""
import json, re, sys, time, urllib.request

EXPLORERS = {
    "base": "https://base.blockscout.com",
    "eth": "https://eth.blockscout.com",
    "ethereum": "https://eth.blockscout.com",
    "optimism": "https://optimism.blockscout.com",
    "arbitrum": "https://arbitrum.blockscout.com",
    "gnosis": "https://gnosis.blockscout.com",
}
HDR = {"User-Agent": "Mozilla/5.0 sc-research"}


def _get(url, tries=3):
    last = None
    for _ in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=30).read()
        except Exception as e:
            last = e
            time.sleep(1.5)
    raise last


def list_verified(base, max_n):
    """Yield recently-verified solidity contracts, newest first."""
    url = base + "/api/v2/smart-contracts?filter=solidity"
    seen = 0
    while url and seen < max_n:
        d = json.loads(_get(url))
        for it in d.get("items", []):
            yield it
            seen += 1
            if seen >= max_n:
                return
        npp = d.get("next_page_params")
        if not npp:
            return
        from urllib.parse import urlencode
        url = base + "/api/v2/smart-contracts?" + urlencode(npp)
        time.sleep(0.2)


def fetch_source(base, addr):
    try:
        d = json.loads(_get(f"{base}/api/v2/smart-contracts/{addr}"))
    except Exception:
        return "", {}
    parts = [d.get("source_code") or ""]
    for a in d.get("additional_sources") or []:
        parts.append(a.get("source_code") or "")
    return "\n".join(parts), d


def strip_comments(src):
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"//[^\n]*", " ", src)
    return src


# externally-callable function header capture: name + param block
FUNC_RE = re.compile(
    r"function\s+(\w+)\s*\(([^)]*)\)([^{;]*)(\{)", re.S)
LOWCALL_RE = re.compile(
    r"(\w+)\s*\.\s*(?:call|delegatecall)\s*[\({]|functionCall\s*\(\s*(\w+)|functionCallWithValue\s*\(\s*(\w+)")
SAFE_TARGETS = {"address(this)", "this", "msg", "WETH", "weth", "_WETH"}


def find_f1(src):
    """Return list of (func_name, target_param, snippet) for arbitrary-call funcs."""
    hits = []
    s = strip_comments(src)
    for m in FUNC_RE.finditer(s):
        name, params, mods, _ = m.groups()
        if not re.search(r"\bexternal\b|\bpublic\b", mods):
            continue
        # skip access-gated functions (by-design admin execute, not an arbitrary-call bug)
        if re.search(r"only[A-Z]\w*|restricted|requiresAuth|\bauth\b|onlyRole|onlyGov", mods):
            continue
        # collect param identifiers by type
        addr_params, bytes_params = [], []
        for p in params.split(","):
            p = p.strip()
            if not p:
                continue
            toks = p.split()
            if len(toks) < 2:
                continue
            ptype, pname = toks[0], toks[-1]
            if ptype == "address" or ptype.startswith("address"):
                addr_params.append(pname)
            if ptype == "bytes":
                bytes_params.append(pname)
        if not addr_params:
            continue
        # find function body (balance braces from header end)
        start = m.end() - 1
        depth, i = 0, start
        while i < len(s):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = s[start:i + 1]
        # does body forward an address param into a low-level call?
        for cm in LOWCALL_RE.finditer(body):
            tgt = cm.group(1) or cm.group(2) or cm.group(3)
            if tgt in SAFE_TARGETS:
                continue
            if tgt in addr_params:
                # snippet around the call
                a = max(0, cm.start() - 60)
                b = min(len(body), cm.end() + 80)
                snip = re.sub(r"\s+", " ", body[a:b]).strip()
                has_bytes = any(bp in body for bp in bytes_params) or "data" in body.lower()
                hits.append((name, tgt, has_bytes, snip))
                break
    return hits


F4_SETTER_RE = re.compile(
    r"function\s+(\w*(?:[Ss]igner|[Oo]perator|[Ww]hitelist|[Aa]llowlist|[Aa]llowList|[Rr]elayer|[Kk]eeper|[Mm]inter|[Aa]uthoriz)\w*)\s*\(([^)]*)\)([^{;]*)\{",
    re.S)


def find_f4(src):
    hits = []
    s = strip_comments(src)
    for m in F4_SETTER_RE.finditer(s):
        name, params, mods = m.groups()
        # body
        start = m.end() - 1
        depth, i = 0, start
        while i < len(s):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        head_body = s[m.start():i + 1]
        # heuristics: must WRITE a mapping/bool (=true / [x]=) and be state-changing
        if not re.search(r"=\s*true|\]\s*=|\.push\(|\.add\(", head_body):
            continue
        if re.search(r"\bview\b|\bpure\b", mods):
            continue
        # access control present?
        guarded = bool(re.search(r"only\w+|_checkOwner|_checkRole|hasRole|require\s*\(\s*msg\.sender|require\s*\(\s*_?owner", head_body))
        if not guarded and re.search(r"\bexternal\b|\bpublic\b", mods):
            snip = re.sub(r"\s+", " ", head_body[:160]).strip()
            hits.append((name, snip))
    return hits


def main():
    chain = sys.argv[1] if len(sys.argv) > 1 else "base"
    max_n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    base = EXPLORERS.get(chain, chain)
    print(f"# scanning {base} — up to {max_n} recently-verified contracts\n")
    scanned = 0
    cand = []
    for it in list_verified(base, max_n):
        addr = it.get("address", {}).get("hash")
        name = it.get("address", {}).get("name") or it.get("name") or "?"
        if not addr:
            continue
        src, meta = fetch_source(base, addr)
        scanned += 1
        if not src:
            continue
        f1 = find_f1(src)
        f4 = find_f4(src)
        if f1 or f4:
            bal = it.get("coin_balance")
            txc = it.get("transactions_count")
            has_tf = "transferFrom" in src or "safeTransferFrom" in src
            score = 0
            score += 5 * sum(1 for h in f1 if h[2])  # f1 with bytes data
            score += 2 * (len(f1) - sum(1 for h in f1 if h[2]))
            score += 3 * len(f4)
            if has_tf:
                score += 4
            try:
                if bal and int(bal) > 0:
                    score += 2
            except Exception:
                pass
            cand.append((score, addr, name, bal, txc, has_tf, f1, f4))
        if scanned % 25 == 0:
            print(f"  ...scanned {scanned}, candidates {len(cand)}", file=sys.stderr)
        time.sleep(0.12)
    cand.sort(reverse=True)
    print(f"\n# scanned {scanned} contracts; {len(cand)} flagged\n")
    for score, addr, name, bal, txc, has_tf, f1, f4 in cand[:40]:
        print(f"\n=== [score {score}] {name}  {addr}")
        print(f"    balance={bal} txs={txc} transferFrom={has_tf}  {base}/address/{addr}?tab=contract")
        for fn, tgt, hb, snip in f1:
            print(f"    F1 fn={fn}() target-param={tgt} bytesData={hb}")
            print(f"       …{snip}")
        for fn, snip in f4:
            print(f"    F4 unguarded setter: {fn}()  | {snip}")


if __name__ == "__main__":
    main()

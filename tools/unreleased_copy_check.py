"""Local upper bound of the platform's unreleased-copy pair score (ditto-subnet api_server/unreleased_copy.py).

    .venv/bin/python tools/unreleased_copy_check.py CANDIDATE.tgz SOURCE.tgz [SOURCE.tgz ...]

Removes the packaged public corpus and every item also present in a released archive under released/*/agent.tar.gz,
then weighs what the candidate shares with each source (text/seq 1.0, ident/short 0.25, wordseq 0.1). The platform's
fuzzy released-text refinement and the common-item floor are not applied, so this over-estimates. Threshold 100.
"""
import glob
import importlib.util
import sys
import types
from collections import Counter
from pathlib import Path

PLATFORM = Path("/home/bittensor/ditto/repos/ditto-subnet/apps/platform/ditto")
sys.path.insert(0, str(PLATFORM.parent))
import ditto.anticopy  # noqa: E402,F401
server = types.ModuleType("ditto.api_server")
server.__path__ = [str(PLATFORM / "api_server")]
sys.modules["ditto.api_server"] = server


def load(name):
    spec = importlib.util.spec_from_file_location(f"ditto.api_server.{name}", PLATFORM / "api_server" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


fp = load("fingerprint")
dc = load("distinctive_content")
WEIGHTS = {dc.KIND_TEXT: 1.0, dc.KIND_SEQ: 1.0, dc.KIND_IDENT: 0.25, dc.KIND_SHORT: 0.25, dc.KIND_WORD_SEQ: 0.1,
           dc.KIND_RESOURCE: 0.0}


def items(path):
    got = dc.extract_items(Path(path).read_bytes(), excluded=fp._excluded_from_fingerprints)
    return got.items if got else {}


cand = items(sys.argv[1])
public = dc.public_item_keys()
released = set()
for arch in glob.glob("/home/bittensor/ditto/released/*/agent.tar.gz"):
    released |= set(items(arch)) & set(cand)
base = set(cand) - public - released
print(f"candidate items {len(cand)}, public {len(set(cand) & public)}, released {len(released)}, left {len(base)}")
for src in sys.argv[2:]:
    shared = base & set(items(src))
    kinds = Counter(dc.key_kind(k) for k in shared)
    score = sum(WEIGHTS[dc.key_kind(k)] for k in shared)
    print(f"{src}: score {score:.2f} (threshold 100) shared {dict(kinds)}")
    for k in sorted(shared, key=lambda k: -WEIGHTS[dc.key_kind(k)])[:12]:
        it = cand[k]
        print("   ", dc.key_kind(k), getattr(it, "path", ""), getattr(it, "line", ""), str(getattr(it, "text", "") or getattr(it, "normalized", ""))[:90])

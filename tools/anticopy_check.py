"""Run the platform's own lexical anti-copy fingerprint on harness trees.

    .venv/bin/python tools/anticopy_check.py REFERENCE_DIR CANDIDATE_DIR [CANDIDATE_DIR ...]

Uses ditto-subnet apps/platform/ditto/api_server/fingerprint.py unchanged: 4-line windows and
30+ character lines, starter-kit content subtracted, copy bars Jaccard 0.75 / containment 0.95.
A match against a published release is withdrawn by the platform; one against an unpublished
submission is held.
"""
import importlib.util
import io
import sys
import tarfile
import types
from pathlib import Path

PLATFORM = Path("/home/bittensor/ditto/repos/ditto-subnet/apps/platform/ditto")
sys.path.insert(0, str(PLATFORM.parent))
import ditto.anticopy  # noqa: E402,F401  light packages; only api_server pulls in the web stack
server = types.ModuleType("ditto.api_server")
server.__path__ = [str(PLATFORM / "api_server")]
sys.modules["ditto.api_server"] = server
spec = importlib.util.spec_from_file_location("ditto.api_server.fingerprint", PLATFORM / "api_server" / "fingerprint.py")
fp = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fp
spec.loader.exec_module(fp)


def tar_of(root: Path) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        for p in sorted(root.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
                t.add(p, arcname=str(p.relative_to(root)))
    return buf.getvalue()


ref = fp.compute_content_fingerprint(tar_of(Path(sys.argv[1])))
print(f"reference {sys.argv[1]}: shingles {ref.get('n') if ref else None}")
for cand in sys.argv[2:]:
    fc = fp.compute_content_fingerprint(tar_of(Path(cand)))
    j, c = fp.content_similarity(ref, fc)
    lj, lc = fp.line_similarity(ref, fc)
    hit = j >= 0.75 or c >= 0.95 or lj >= 0.75 or lc >= 0.95
    print(f"{cand}: windows jaccard {j:.3f} containment {c:.3f} | lines jaccard {lj:.3f} containment {lc:.3f} | "
          f"{'WOULD TRIGGER (0.75 / 0.95)' if hit else 'below the copy bars'}")

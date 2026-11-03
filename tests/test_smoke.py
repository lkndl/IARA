"""Smoke tests: run the installed `iara` command as dtand's interface-score does."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from gemmi import cif

FIXTURE = Path(__file__).parent / "fixtures" / "1brs_AD.cif"


def run_iara(*args):
    # the console script installed next to this interpreter, iara.exe on Windows
    command = shutil.which("iara", path=os.path.dirname(sys.executable))
    assert command, "the iara command is not installed in this environment"
    return subprocess.run([command, *args], capture_output=True, text=True, encoding="utf-8")


def atom_site_residues(path):
    """(chain, number) of every residue with a C-alpha, by author and by label IDs."""
    block = cif.read(str(path)).sole_block()
    table = block.find("_atom_site.", ["label_atom_id", "auth_asym_id", "auth_seq_id", "label_asym_id", "label_seq_id"])
    auth, label = set(), set()
    for row in table:
        if row[0] == "CA":
            auth.add((row[1], int(row[2])))
            label.add((row[3], int(row[4])))
    return auth, label


def test_track_sits_on_author_chains(tmp_path):
    auth, label = atom_site_residues(FIXTURE)
    # the fixture only tests something if author and label chains differ
    assert {c for c, _ in auth} != {c for c, _ in label}

    result = run_iara("-i", str(FIXTURE), "-o", str(tmp_path), "-j")
    assert result.returncode == 0, result.stdout + result.stderr

    track = json.loads((tmp_path / "1brs_AD_IARA_track.json").read_text(encoding="utf-8"))

    # the fields af-molstar-viewer requires, see docs/residue-score-track.md there
    assert track["schema_version"] == 1
    assert track["id"] == "iara-interface"
    assert track["label"]
    assert track["index"] == "auth"
    assert track["scale"] == {"kind": "sequential", "domain": [0.0, 100.0]}
    assert track["palette"] == {"name": "purples"}
    assert "structure_ref" not in track
    provenance = track["provenance"]
    assert provenance["tool"] == "iara"
    assert provenance["source_structure"] == FIXTURE.name
    assert provenance["parameters"] == {"edge_distance_threshold_A": 10.0, "smoothing_radius_A": 8.0}

    values = track["values"]
    keys = [(v["chain"], v["seq"], v.get("ins_code", "")) for v in values]
    assert len(keys) == len(set(keys)), "duplicate residues"
    for v in values:
        assert isinstance(v["chain"], str) and isinstance(v["seq"], int)
        assert v["value"] is None or 0.0 <= v["value"] <= 100.0

    # every residue is scored, on its author chain and number
    assert {(c, s) for c, s, _ in keys} == auth
    assert {c for c, _, _ in keys} == {"A", "D"}


def test_failed_input_exits_non_zero(tmp_path):
    broken = tmp_path / "broken.pdb"
    broken.write_text("not a structure\n")

    result = run_iara("-i", str(tmp_path), "-o", str(tmp_path / "out"), "-j")
    assert result.returncode == 1, result.stdout + result.stderr

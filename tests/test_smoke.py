"""Smoke tests: run the installed `iara` command as dtand's interface-score does."""

import gzip
import hashlib
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
    """Every residue with a C-alpha: its label_comp_id by author (chain, number), and its label (chain, number)."""
    block = cif.read(str(path)).sole_block()
    table = block.find("_atom_site.", ["label_atom_id", "auth_asym_id", "auth_seq_id", "label_asym_id", "label_seq_id", "label_comp_id"])
    auth, label = {}, set()
    for row in table:
        if row[0] == "CA":
            auth[(row[1], int(row[2]))] = row[5]
            label.add((row[3], int(row[4])))
    return auth, label


def read_track(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_track_sits_on_author_chains(tmp_path):
    auth, label = atom_site_residues(FIXTURE)
    # the fixture only tests something if author and label chains differ
    assert {c for c, _ in auth} != {c for c, _ in label}

    result = run_iara("-i", str(FIXTURE), "-o", str(tmp_path), "-j")
    assert result.returncode == 0, result.stdout + result.stderr

    track = read_track(tmp_path / "1brs_AD_IARA_track.json")

    # the fields af-molstar-viewer requires, see docs/residue-score-track.md there
    assert track["schema_version"] == 2
    assert track["id"] == "iara-interface"
    assert track["label"]
    assert track["index"] == "auth"
    assert track["scale"] == {"kind": "sequential", "domain": [0.0, 100.0]}
    assert track["palette"] == {"name": "purples"}
    assert "structure_ref" not in track
    provenance = track["provenance"]
    assert provenance["tool"] == "iara"
    assert provenance["source_structure"] == FIXTURE.name
    assert provenance["source_sha1sum"] == hashlib.sha1(FIXTURE.read_bytes()).hexdigest()
    assert provenance["parameters"] == {"edge_distance_threshold_A": 10.0, "smoothing_radius_A": 8.0}

    values = track["values"]
    keys = [(v["chain"], v["idx"], v.get("ins_code", "")) for v in values]
    assert len(keys) == len(set(keys)), "duplicate residues"
    for v in values:
        assert set(v) <= {"chain", "idx", "res_name", "ins_code", "value"}
        assert isinstance(v["chain"], str) and isinstance(v["idx"], int)
        assert v["value"] is None or 0.0 <= v["value"] <= 100.0
        # the name as the file has it, not a one-letter code
        assert v["res_name"] == auth[(v["chain"], v["idx"])]

    # every residue is scored, on its author chain and number
    assert {(c, s) for c, s, _ in keys} == set(auth)
    assert {c for c, _, _ in keys} == {"A", "D"}


def test_gzipped_input_has_the_hash_of_the_plain_file(tmp_path):
    packed = tmp_path / "1brs_AD.cif.gz"
    packed.write_bytes(gzip.compress(FIXTURE.read_bytes()))

    result = run_iara("-i", str(packed), "-o", str(tmp_path), "-j")
    assert result.returncode == 0, result.stdout + result.stderr

    track = read_track(tmp_path / "1brs_AD_IARA_track.json")
    assert track["provenance"]["source_sha1sum"] == hashlib.sha1(FIXTURE.read_bytes()).hexdigest()


def test_failed_input_exits_non_zero(tmp_path):
    broken = tmp_path / "broken.pdb"
    broken.write_text("not a structure\n")

    result = run_iara("-i", str(tmp_path), "-o", str(tmp_path / "out"), "-j")
    assert result.returncode == 1, result.stdout + result.stderr

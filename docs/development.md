# Development

## Install and test

```bash
uv sync
uv run pytest
```

The tests run the installed `iara` command, as dtand's `interface-score` does.
GitHub Actions runs them on Linux, macOS and Windows
([.github/workflows/tests.yml](../.github/workflows/tests.yml)), after a
`uv tool install` of the checkout, which resolves without `uv.lock`.

### The fixture

`tests/fixtures/1brs_AD.cif` is PDB entry 1BRS reduced to the protein atoms of
barnase (author chain A) and barstar (author chain D), without hydrogens,
waters or alternative conformations. Its label chains are A and B, numbered in
order as the PDB numbers them, so barstar's author and label chain IDs differ.
A track on label chains puts barstar on chain B and fails the test. It was
written with gemmi from the full entry, with only the `atom_site`, `entity`,
`entity_poly`, `struct_asym` and `chem_comp` categories.

## Structures are read with gemmi

gemmi names chains and residues by author ID (`auth_asym_id`, `auth_seq_id`) in
both PDB and mmCIF, which is what the score track declares with
`"index": "auth"`. The residue name, the track's `res_name`, is
`auth_comp_id` where an mmCIF file has that column and `label_comp_id`
otherwise; the two agree in wwPDB files. ProDy, used before, put the label
chain ID into the chain of mmCIF input, had no wheel for Python 3.13 (so it
compiled on every install, which on Windows needs the MSVC Build Tools), and
capped `pyparsing<=3.1.1`.

## Versions come from git tags

The version is derived from git by hatch-vcs: tag `v0.2.0` builds as `0.2.0`,
later commits as `0.2.1.devN+g<hash>`, and a dirty tree adds the date. It ends up
in `provenance.tool_version` of every track, so tag each change that dtand
should pick up; dtand installs with
`uv tool install git+https://github.com/lkndl/IARA@<tag>`. Without git, e.g.
from a ZIP download, the version is `0.0.0`.

## Dependencies

`uv tool install` resolves from `pyproject.toml` and ignores `uv.lock`, so every
dependency keeps a lower bound there.

## Platform notes

- **macOS:** `main()` sets `KMP_DUPLICATE_LIB_OK=TRUE` when unset, because
  more than one OpenMP runtime may load and the second aborts the process.
- **Windows:** `main()` writes stdout and stderr as UTF-8. Windows otherwise
  writes to a pipe in the ANSI code page, which cannot encode the emoji in the
  output, and every run with captured output would fail. Callers should decode
  as UTF-8, as the plugins do.

## Plugins

The PyMOL and ChimeraX plugins run the `iara` command: the path saved by
`iara_configure` in `~/.iara_command.txt`, else `iara` on the `PATH`, else
`~/.local/bin/iara`, where `uv tool install` puts it. Apps started from the
Dock or the Start menu do not see a terminal's `PATH`, hence the last. The
plugins import only what PyMOL and ChimeraX provide, so they need no extra.

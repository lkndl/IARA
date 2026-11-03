import os
import shutil
import tempfile
import subprocess
from chimerax.core.commands import CmdDesc, StringArg, register
from chimerax.atomic import AtomicStructuresArg
from chimerax.core.errors import UserError
from chimerax.core.commands import run

# Where iara_configure saves the path of the iara command
CONFIG_FILE = os.path.expanduser("~/.iara_command.txt")

def find_iara():
    """The iara command: the configured one, else the one on the PATH, else the one in ~/.local/bin."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    return shutil.which("iara") or shutil.which("iara", path=os.path.join(os.path.expanduser("~"), ".local", "bin"))

def iara_configure(session, path):
    clean_path = os.path.expanduser(path.strip(" '\""))

    # Accept the folder that holds the command, e.g. the bin folder of an environment
    if os.path.isdir(clean_path):
        clean_path = shutil.which("iara", path=clean_path) or clean_path
    if not os.path.isfile(clean_path):
        session.logger.warning(f"Warning: Could not find the iara command at {clean_path}")

    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(clean_path)
        session.logger.info(f"IARA configured successfully! Path saved to {CONFIG_FILE}")
    except Exception as e:
        raise UserError(f"Error saving configuration: {e}")

def iara_predict(session, structures):
    if len(structures) == 0:
        raise UserError("No structures provided to predict.")

    structure = structures[0] # Target only the first selected model

    iara = find_iara()
    if iara is None:
        raise UserError("The iara command was not found. Install it with "
                        "'uv tool install git+https://github.com/lkndl/IARA', "
                        "or tell the plugin where it is: iara_configure /path/to/iara")

    # Save temp PDB
    temp_dir = tempfile.mkdtemp()
    temp_pdb = os.path.join(temp_dir, "temp_target.pdb")

    run(session, f"save {temp_pdb} models #{structure.id_string}")
    session.logger.info("Running IARA Neural Network...")

    try:
        result = subprocess.run([iara, "--input", temp_pdb, "--outdir", temp_dir],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        raise UserError(f"Failed to launch {iara}: {e}")
    if result.returncode != 0:
        session.logger.warning(result.stdout)
        session.logger.warning(result.stderr)
        raise UserError("IARA Inference Failed! Check Log.")

    scored_pdb = os.path.join(temp_dir, "temp_target_IARA.pdb")
    if not os.path.exists(scored_pdb):
        raise UserError("Could not locate output file.")

    # Open and Render inside ChimeraX
    models = run(session, f"open {scored_pdb}")
    new_model = models[0]

    # Keep probabilities scaled 0-100 to match PyMOL behavior

    run(session, f"hide #{new_model.id_string} atoms")
    run(session, f"show #{new_model.id_string} cartoons")

    # ChimeraX's native brilliant command for coloring directly by bfactor onto a color key
    run(session, f"color bfactor #{new_model.id_string} palette blue:white:red range 0,100 key true")

    # Hide original to prevent 3D clipping overlap
    run(session, f"hide #{structure.id_string} models")
    session.logger.info("IARA Prediction Complete!")

# Register commands globally using the `session` object that ChimeraX automatically injects
def register_iara_commands(sess):
    try:
        predict_desc = CmdDesc(required=[("structures", AtomicStructuresArg)], synopsis="Run IARA on selected model")
        configure_desc = CmdDesc(required=[("path", StringArg)], synopsis="Set the path of the iara command")

        register("iara_predict", predict_desc, iara_predict, logger=sess.logger)
        register("iara_configure", configure_desc, iara_configure, logger=sess.logger)

        if find_iara() is None:
            sess.logger.info("IARA Plugin commands loaded, but the iara command was not found. Run: iara_configure /path/to/iara")
        else:
            sess.logger.info("IARA Plugin commands loaded successfully! Try: iara_predict #1")
    except Exception as e:
        sess.logger.error(f"Failed to load IARA commands: {e}")

# The 'session' variable is provided by the ChimeraX 'open' command runtime.
register_iara_commands(session)

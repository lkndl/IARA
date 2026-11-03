import os
import shutil
import tempfile
import subprocess
from pymol import cmd

# -----------------------------------------------------------------------------
# IARA: Interface Analysis and Recognition Architecture
# PyMOL Plugin
# -----------------------------------------------------------------------------

# Where iara_configure saves the path of the iara command
CONFIG_FILE = os.path.expanduser("~/.iara_command.txt")

def find_iara():
    """The iara command: the configured one, else the one on the PATH, else the one in ~/.local/bin."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return f.read().strip()
    return shutil.which("iara") or shutil.which("iara", path=os.path.join(os.path.expanduser("~"), ".local", "bin"))

def iara_predict(*args, **kwargs):
    # PyMOL splits arguments by comma, so we join them back together for complex selections
    selection = ",".join(args) if args else "all"
    """
    DESCRIPTION
    
        Runs the IARA Graph Neural Network on the specified selection to predict 
        thermodynamic interaction hotspots. The predicted probability (0-100) 
        is written to the B-factor column, and the protein is recolored as a heatmap.
        
    USAGE
    
        iara_predict [selection]
        
    EXAMPLE
    
        fetch 1cse
        iara_predict 1cse
    """
    print(f"\n🌊 IARA Inference (Interface Analysis and Recognition Architecture) 🌊")
    print(f"Targeting selection: {selection}")
    
    # PyMOL ships with its own python, so IARA runs as the separately installed iara command
    iara = find_iara()

    if iara is None:
        print("❌ Error: The iara command was not found.")
        print("Install it with 'uv tool install git+https://github.com/lkndl/IARA',")
        print("or tell PyMOL where it is by typing this into the PyMOL console:")
        print("    iara_configure /absolute/path/to/iara")
        return

    temp_dir = tempfile.mkdtemp()
    temp_pdb = os.path.join(temp_dir, "temp_target.pdb")
    
    # Save the PyMOL selection to a temporary PDB file
    try:
        cmd.save(temp_pdb, selection)
    except Exception as e:
        print(f"❌ Failed to save selection: {e}")
        return
        
    print(f"🏃 Running IARA Neural Network...")

    try:
        # Capture the output so we can show EXACTLY why it failed in the PyMOL console
        result = subprocess.run([iara, "--input", temp_pdb, "--outdir", temp_dir],
                                capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            print("❌ IARA Inference Failed! Backend Error Traceback:")
            print("-" * 50)
            print(result.stdout)
            print(result.stderr)
            print("-" * 50)
            print(f"Troubleshooting: does '{iara} --help' run in a terminal?")
            return
    except Exception as e:
        print(f"❌ Failed to launch {iara}: {e}")
        return
        
    # The script names the output <stem>_IARA.pdb
    scored_pdb = os.path.join(temp_dir, "temp_target_IARA.pdb")
    
    if not os.path.exists(scored_pdb):
        print("❌ Could not locate the scored output file.")
        return
        
    # Load it back into PyMOL
    new_obj_name = f"{selection}_IARA"
    cmd.load(scored_pdb, new_obj_name)
    
    # Beautify the visualization
    print("🎨 Applying IARA Heatmap Visualization...")
    cmd.hide("everything", new_obj_name)
    cmd.show("cartoon", new_obj_name)
    
    # Scale B-factors from 0-100 down to 0.0-1.0 for standard interpretation
    cmd.alter(new_obj_name, "b = b / 100.0")
    
    # PyMOL B-factor coloring spectrum: Blue (0.0) -> White (0.5) -> Red (1.0)
    cmd.spectrum("b", "blue_white_red", new_obj_name, minimum=0.0, maximum=1.0)
    
    # Generate an explicit color legend (ramp) using a dummy gaussian map
    # This is standard practice in PyMOL for adding color bars without complex plugins
    dummy_map = f"{new_obj_name}_map"
    legend_name = f"IARA_Scale_{new_obj_name}"
    
    # Remove old legends if re-running
    if legend_name in cmd.get_names():
        cmd.delete(legend_name)
        cmd.delete(dummy_map)
        
    cmd.map_new(dummy_map, "gaussian", 1, new_obj_name)
    cmd.ramp_new(legend_name, dummy_map, [0.0, 0.5, 1.0], ["blue", "white", "red"])
    
    # Hide the ugly invisible map, but keep the beautiful color bar legend visible
    cmd.disable(dummy_map)
    cmd.disable(selection)
    
    print(f"✅ IARA Prediction Complete! ({new_obj_name})")
    print(f"🔥 Red patches indicate highly designable thermodynamic hotspots.")

# Extend the PyMOL command line
cmd.extend("iara_predict", iara_predict)

# Enable TAB auto-completion for loaded PyMOL objects as the first argument
cmd.auto_arg[0]['iara_predict'] = [cmd.object_sc, 'object', '']


def iara_configure(installation_path, **kwargs):
    """
    DESCRIPTION

        Configures the IARA plugin with the path to the iara command, or to its folder.

    USAGE

        iara_configure [path]
    """
    # Clean up the path
    clean_path = os.path.expanduser(installation_path.strip(" '\""))

    # Accept the folder that holds the command, e.g. the bin folder of an environment
    if os.path.isdir(clean_path):
        clean_path = shutil.which("iara", path=clean_path) or clean_path
    if not os.path.isfile(clean_path):
        print(f"⚠️ Warning: Could not find the iara command at {clean_path}")

    try:
        with open(CONFIG_FILE, "w") as f:
            f.write(clean_path)
        print(f"✅ IARA configured successfully! Path saved to {CONFIG_FILE}")
        print("You can now run 'iara_predict' on any loaded structure.")
    except Exception as e:
        print(f"❌ Error saving configuration: {e}")

cmd.extend("iara_configure", iara_configure)


# Optional: Add it to the GUI menu (Requires Tkinter which PyMOL usually has)
def __init_plugin__(app=None):
    from pymol.plugins import addmenuitemqt
    addmenuitemqt('IARA Hotspot Predictor', lambda: cmd.scene(''), 'iara_predict')

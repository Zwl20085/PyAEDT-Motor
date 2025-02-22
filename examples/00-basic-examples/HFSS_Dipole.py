"""
Dipole Antenna Example
----------------------
This example shows how you can use PyAEDT to create an antenna setup in HFSS and postprocess results.
"""
# sphinx_gallery_thumbnail_path = 'Resources/Dipole.png'

import os
from pyaedt import Hfss
from pyaedt import Desktop
from pyaedt import generate_unique_name

if os.name == "posix":
    tmpfold = os.environ["TMPDIR"]
else:
    tmpfold = os.environ["TEMP"]

temp_folder = os.path.join(tmpfold, generate_unique_name("Example"))
if not os.path.exists(temp_folder):
    os.mkdir(temp_folder)

###############################################################################
# Launch AEDT in Graphical Mode
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This examples launches AEDT 2021.1 in graphical mode.

nongraphical = False
d = Desktop("2021.1", NG=nongraphical)

###############################################################################
# Launch HFSS in Graphical Mode
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This examples launches HFSS 2021.1 in graphical mode.

hfss=Hfss()

###############################################################################
# Define a Dipole Length Variable
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# This command defines a dipole length variable.

hfss['l_dipole'] = "13.5cm"

###############################################################################
# Get a 3D Component from the `syslib` Directory
# ----------------------------------------------
# To run this example correctly, you must get all geometry parameters of the
# 3D component or, in case of an encrypted 3D component, create a dictionary
# of the parameters.

compfile = hfss.components3d['Dipole_Antenna_DM']
geometryparams = hfss.get_components3d_vars('Dipole_Antenna_DM')
geometryparams['dipole_length'] = "l_dipole"
hfss.modeler.primitives.insert_3d_component(compfile, geometryparams)

###############################################################################
# Create Boundaries
# -----------------
# A region with openings is needed to run the analysis.

hfss.create_open_region(Frequency="1GHz")

###############################################################################
# Create the Setup
# ----------------
# A setup with a sweep will be used to run the simulation.

setup = hfss.create_setup("MySetup", hfss.SimulationSetupTypes.HFSSDrivenAuto)
setup.props["Type"] = "Interpolating"
setup.props["Sweeps"]['Sweep']['RangeType'] = 'LinearCount'
setup.props["Sweeps"]['Sweep']['RangeStart'] = '0.5GHz'
setup.props["Sweeps"]['Sweep']['RangeEnd'] = '1.5GHz'
setup.props["Sweeps"]['Sweep']['RangeCount'] = 401
setup.props["Sweeps"]['Sweep']['AutoSolverSetting'] = "Higher Speed"
setup.update()

###############################################################################
# Save and Run the Simulation
# ---------------------------
# A setup with a sweep will be used to run the simulation.

hfss.save_project(os.path.join(temp_folder, "MyDipole.aedt"))
hfss.analyze_setup("MySetup")

###############################################################################
# Postprocessing
# --------------
# Generate a scattering plot and a far fields plot.

hfss.create_scattering("MyScattering")
variations = hfss.available_variations.nominal_w_values_dict
variations["Freq"] = ["1GHz"]
variations["Theta"] = ["All"]
variations["Phi"] = ["All"]
hfss.post.create_rectangular_plot("db(GainTotal)",hfss.nominal_adaptive,
                                  variations, "Theta", "3D",plottype="Far Fields")

###############################################################################
# Close AEDT
# ~~~~~~~~~~
# After the simulaton is completed, you can close AEDT or release it using the
# :func:`pyaedt.Desktop.release_desktop` method.
# All methods provide for saving the project before exiting.

if os.name != "posix":
    d.force_close_desktop()

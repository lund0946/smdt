# DEIMOS Slitmask Design Tool

This software is still in active development and close to ready for release.  Any feedback is welcome

### Installation
Several python modules may need to be installed including flask, astropy, numpy, etc.

Launch using `python app.py`

### Instructions
- Select catalog file and click load targets.  
- Set parameters like field center and mask PA.
- Click update parameters to save parameters.
- Press the Auto-select button to populate the target table and display targets
- Select targets manually by clicking on a target/table row and updating select from 0 to 1 or vise versa.
- Click the Generate Slits button to visualize slits.
- Click save mask design file to save the file.

### Other items
- Auto-select, generate slits, and the save mask buttons do not automatically update the parameters, instead they require the update parameters button to be pressed first to lock in the selection.

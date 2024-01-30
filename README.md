# DEIMOS Slitmask Design Tool

This software is still in active development and close to ready for release.  Any feedback is welcome

### Installation
Several python modules may need to be installed including flask, astropy, numpy, etc.

Launch using `python app.py`

### Instructions
- Select catalog file and click load targets.  
- Set parameters like field center and mask PA.
- Click update parameters to save parameters.
- Select targets manually by clicking on a target/table row and updating select from 0 to 1 or automatically with the Auto-select button.
- Click the Generate Slits button to visualize slits.
- Click save mask design file to save the file.

### Known bugs
- SaveMaskDesignFile Button doesn't show correct filename/path.
- If loading a dsimulator output file, it adds an extra target for the field center.


### Other items
- Recalculate mask or save mask doesn't automatically update the parameters, instead it requires the update parameters button to be pressed first to lock in the selection.

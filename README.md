# DEIMOS Slitmask Design Tool

This software is still in active development and not yet ready for release, but feedback is welcome

### Installation
Several python modules may need to be installed including flask, astropy, numpy, etc.
In your `.astropy/configs/astropy.cfg` set `extension_name_case_sensitive = True`

Launch using `python app.py`

### Instructions
Select catalog file and click load targets.  
Set parameters and click update parameters.
Change mask PA or any individual slit PAs.
Update parameters.
Click recalculate mask to visualize slits.
Click save mask design file to save the file.

### Known bugs
- Discrepency between dsimulator and smdt slit angles
- Mask Design Output includes all 
- Plot not yet includeed
- Recalculate mask or save mask doesn't automatically update the parameters.

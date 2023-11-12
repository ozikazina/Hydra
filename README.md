# Hydra

Blender GPU accelerated hydraulic erosion addon using OpenGL.

Setup guide
===========

To install this project, import the corresponding **zip** file into Blender addons and activate it.

This project requires external dependencies, which can be downloaded with a provided button in the preferences.
Executing this command will probably require elevated privileges. If the installation fails, launch Blender as an administrator and try again.
If it succeeds, restart the app normally.

The addon page will indicate whether ModernGL is installed.

If you have the Fedora operating system, this addon might not work, as ModernGL can't attach itself to Blender's drawing context on this operating system.

Manual ModernGL installation
----------------------------

Go to your Blender installation directory and to the version you want to use. Then navigate to the `python\bin` directory. Path example:

`C:\Program Files\Blender Foundation\Blender 3.5\3.5\python\bin`

Once there, open this folder in the command line and install ModernGL through the Python executable:

`python.exe -m pip install --upgrade moderngl`

or

`./python -m pip install --upgrade moderngl`

Uninstalling
------------

To uninstall the project, go to the addons tab and press remove. Removing the ModernGL library needs to be done manually.

Go to the Python folder specified above in the [Manual ModernGL installation](#manual-moderngl-installation) section and execute:

`python.exe -m pip uninstall moderngl`

or

`./python -m pip uninstall moderngl`

Addon usage
===========

This addon supports erosion for objects and images. The resulting heightmap can be applied back to the object in multiple ways, or it can be exported as an image.

It can be found in the right side panel in both 3D View and Image Editor windows.

Water erosion
-------------

To erode objects, select any object with a mesh and simply press erode in the corresponding tab.
Objects with overlapping geometry are supported, but the resulting heightmap might not be applicable back to the object.

Once erosion starts, the object or image is converted into a heightmap. In the case of objects, the chosen image resolution becomes locked.

> To pick a different resolution, you first have to clear generated textures for the current object.

Two heightmaps are created - **source** and **current**. Source is the starting point for erosion.
Choosing different parameters and eroding again will erode start from the source map, giving you the option to test different settings.
The current map is the result of erosion. It is automatically previewed.

To use the current map as a starting point and to exchange maps between thermal and water erosion, simply apply it as a source in the Heightmaps subtab.

> The source layer can also be set as back current to be exported or applied.

### Applying results

The current map can be applied in a few different ways.

> * `Automatic preview` - creates a temporary modifier. Only applies to one object at a time.
> * `Modifier` - adds a Displace modifier to the object.
> * `Bump` - adds a bump map to the first material slot. Creates one if necessary.
> * `Displacement` - adds a displacement map to the first material slot. Creates one if necessary.
> * `To mesh` - applies modifiers to the mesh. Available if the preview or modifier option was chosen.
> * `As shape key` - applies modifiers as a shape key. Available if the preview or modifier option was chosen. `Locks to mesh option`.
> * `As image` - creates a Blender image of the corresponding heightmap.

### Parameters

> * `Iterations` - number of iterations to perform.
> * `Lifetime` - number of steps a particle can take in an iteration.
> * `Acceleration` - defines how strongly slopes affect particle movement.
> * `Drag` - slows down particle movement.
> * `Erosion smoothness` - erosion strength. Slightly smoothes surface features.
> * `Deposition strength` - strength of sedimentation.
> * `Capacity` - particle material capacity. Higher values lead to deeper features.

### Extra functions

Water erosion can also create extra output maps:

> * `Color` - provided color map will be transported by erosion.
> * `Sediment`- map of sedimentation amounts.
> * `Depth` - map of erosion depth.

Heightmap generation
--------------------

Heightmaps can be generated directly at an arbitrary resolution. Cached heightmaps are also offered for direct export.

Flow maps
---------

A special tab is offered for flow map generation. The output texture stores flow concentration, which can be varied by a contrast slider.
Particle settings are shared with water erosion.

Thermal erosion
---------------

Thermal erosion produces smooth slopes with a specified maximum angle. It shares the same heightmap system as water erosion.

Cleanup
-------

Allocated textures and active preview can be released using functions in this tab.

## License

This project is also a Bachelor's thesis implementation for the Brno University of Technology. It is released under the MIT license.
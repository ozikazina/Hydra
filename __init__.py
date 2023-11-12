"""Hydra initialization module."""

bl_info = {
	"name": "Hydra",
	"author": "Ondrej Vlcek",
	"version": (0, 2, 1),
	"blender": (3, 3, 0),
	"location": "View3D > Sidebar > Hydra Tab",
	"description": "Blender addon for hydraulic erosion using textures.",
	"warning": "Requires external dependencies. See Preferences below.",
	"doc_url": "",
	"category": "Mesh",
	"support": "COMMUNITY",
}
"""Blender Addon information."""

_hydra_invalid:bool = False
"""Helper flag. `False` if ModernGL is found."""

def checkModernGL():
	"""Checks :mod:`moderngl` installation and sets the addon invalid flag."""
	global _hydra_invalid
	try:
		import moderngl
	except:
		_hydra_invalid = True

checkModernGL()

import bpy
from bpy.props import PointerProperty

# ------------------------------------------------------------
# Init:
# ------------------------------------------------------------

_classes = []
"""List of UI classes to be imported."""

from Hydra import startup

if not _hydra_invalid:
	from Hydra import common, opengl
	from Hydra.UI import addon, opsHeightmap, opsObject, opsImage, props
	_classes += props.EXPORTS
	_classes += addon.EXPORTS
	_classes += opsHeightmap.EXPORTS
	_classes += opsObject.EXPORTS
	_classes += opsImage.EXPORTS
else:
	from Hydra.UI import addon
	_classes += addon.EXPORTS

# ------------------------------------------------------------
# Register:
# ------------------------------------------------------------

def register():
	"""Blender Addon register function.
	Creates :data:`common.data` object and calls initialization functions.
	Adds settings properties to `Scene`, `Object` and `Image` Blender classes."""
	global _hydra_invalid
	global _classes
	for cls in _classes:
			bpy.utils.register_class(cls)

	if not _hydra_invalid:
		common.data = common.HydraData()
		common.data.initContext()
		opengl.initContext()
		startup.invalid = False

		bpy.types.Scene.hydra = PointerProperty(type=props.HydraGlobalGroup)
		bpy.types.Object.hydra = PointerProperty(type=props.ErosionGroup)
		bpy.types.Image.hydra = PointerProperty(type=props.ErosionGroup)

def unregister():
	"""Blender Addon unregister function.
	Removes UI classes, settings properties and releases all resources."""
	global _hydra_invalid
	global _classes
	for cls in reversed(_classes):
			bpy.utils.unregister_class(cls)
	if not _hydra_invalid:
		del bpy.types.Object.hydra
		del bpy.types.Scene.hydra
		del bpy.types.Image.hydra

		common.data.freeAll()
		common.data = None

# ------------------------------------------------------------

if __name__ == "__main__":
	register()

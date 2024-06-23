"""Module of addon preferences and ModernGL installation."""

import bpy
from Hydra import startup

from bpy.props import (
	BoolProperty, IntProperty, EnumProperty
)

class AddonPanel(bpy.types.AddonPreferences):
	"""Addon preferences panel."""
	bl_idname = "Hydra"

	skip_indexing: BoolProperty(name="Fix heightmaps", default=False,
		description="Fixes heightmap generation if it fails. Skips vertex indexing, which can fail outside Windows in ModernGL. Uses more memory during generation"
	)
	"""Heightmap generation indexing override."""

	split_direction: EnumProperty(
		default="any",
		items=(
			("any", "Best fit", "Splits the longer dimension, e.g. into top and bottom for a vertical window", 0),
			("x", "Horizontal", "Splits into left and right views", 1),
			("y", "Vertical", "Splits into top and bottom views", 2),
		),
		name="Preview split direction",
		description="Direction in which the window is split to view resulting outputs (e.g. to create an Image Viewer for generated images)"
	)
	"""Split direction preference."""

	debug_mode: BoolProperty(name="Debug mode", default=False,
		description="Enables debug mode, giving access to additional operators"
	)

	image_preview: EnumProperty(
		default="landscape",
		items=(
			("landscape", "3D View", "Creates a landscape to preview erosion in 3D", 0),
			("image", "Image View", "Previews erosion as an image", 1),
		),
		name="Image erosion preview",
		description="Type of preview for image erosion results"
	)

	image_preview_resolution: IntProperty(
		name="3D preview resolution",
		description="Maximum side length of preview landscape in vertices",
		default=1024,
		min=2
	)

	def draw(self, context):
		layout = self.layout

		box = layout.box()
		split = box.split(factor=0.33)
		split.label(text="Image erosion preview: ")
		split.prop(self, "image_preview", text="")

		if self.image_preview == "landscape":
			box.prop(self, "image_preview_resolution")

		split = box.split(factor=0.33)
		split.label(text="Preview split direction: ")
		split.prop(self, "split_direction", text="")
		if startup.invalid and not startup.promptRestart:
			box.enabled = False
			
		box.prop(self, "skip_indexing")
		box.prop(self, "debug_mode")

		box = layout.box()
		if startup.promptFailed:
			box.label(text="Install failed. Please launch Blender as an administrator and try again.")
		elif startup.promptRestart:
			box.label(text="Success! Please restart Blender to apply package changes.")
		elif startup.invalid:
			box.label(text="ModernGL needs to be installed (~5MB). Launch Blender as administrator and press:")
			box.operator('hydra.install', text="Install ModernGL (will freeze for a few seconds)", icon="CONSOLE")
		else:
			box.label(text="ModernGL and GLContext successfuly found.")
			box.operator('hydra.install', text="Check ModernGL updates", icon="CONSOLE")
		
class ModernGLInstaller(bpy.types.Operator):
	"""
	Operator for automatic installation of ModernGL. Original code by Robert Gutzkow.
	Taken from: https://github.com/robertguetzkow/blender-python-examples/blob/master/add_ons/install_dependencies/install_dependencies.py
	"""
	bl_idname = "hydra.install"
	bl_label = "Install ModernGL"
	bl_description = "Install ModernGL (into Blender directory -> [version] -> python -> lib -> site-packages)"
			
	def invoke(self, context, event):
		if not startup.invalid:
			print("ModernGL already installed.")
			return {'FINISHED'}
			
		import os, sys, subprocess
		environ_copy = dict(os.environ)
		environ_copy["PYTHONNOUSERSITE"] = "1"
		try:
			subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "moderngl"], check=True, env=environ_copy)
			self.report({'INFO'}, f"Successfuly installed. Please restart Blender.")
			startup.promptRestart = True
		except Exception as ex:
			startup.promptFailed = True
			print("Exception during install:")
			print(ex)
			self.report({'ERROR'}, f"Failed to install. Try launching Blender as administrator.")
		return {'FINISHED'}
	
def get_exports()->list:
	return [
		ModernGLInstaller, AddonPanel
	]

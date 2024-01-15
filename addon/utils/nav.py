"""Module responsible for window and result navigation."""

import bpy.types
from Hydra import common
from mathutils import Euler
import math

def getSplitDir(target)->str:
	"""Creates a split direction based on the window size and global preferences.

	:param target: Window to be split.
	:return: Window split direction.
	:rtype: :class:`str`"""
	prefs = common.getPreferences()
	if prefs.split_direction == "x":
		return "VERTICAL"	#direction of split line -> perpendicular
	elif prefs.split_direction == "y":
		return "HORIZONTAL"
	else:
		return "VERTICAL" if target.height < target.width else "HORIZONTAL"

def getOrMakeArea(type: str, uiType: str = "")->bpy.types.Area:
	"""Gets or creates a window of the specified type.
	
	:param type: Window type.
	:type type: :class:`str`
	:param uiType: Window subtype.
	:type uiType: :class:`str`
	:return: Created or found area.
	:rtype: :class:`bpy.types.Area`"""
	active = bpy.context.area.spaces.active
	if active.type == type:
		other = None
		for area in bpy.context.screen.areas:	#tries to find a different window
			if area.type == type and area.spaces[0] != active:
				if not uiType or uiType == area.ui_type:
					other = area
					break
		if not other:	#splits active
			area = next(i for i in bpy.context.screen.areas if i.spaces[0] == active)
			bpy.ops.screen.area_split(direction=getSplitDir(area))
			other = bpy.context.screen.areas[-1]
		return other

	target = None
	for area in bpy.context.screen.areas:
		if area.type == type:
			if not uiType or uiType == area.ui_type:
				return area
		if area.type == "VIEW_3D":
			target = area
	
	#splits 3D view if type not found
	if not target:	#else anything other than outliner or properties
		target = [i for i in bpy.context.screen.areas if i.type != "OUTLINER" and i.type != "PROPERTIES"][-1]
	if not target:	#else anything
		target = bpy.context.screen.areas[-1]
	
	with bpy.context.temp_override(area=target): #select target area for split
		bpy.ops.screen.area_split(direction=getSplitDir(target))

	target = bpy.context.screen.areas[-1]	#new area is last
	target.type = type
	if uiType:
		target.ui_type = uiType
	return target


def gotoImage(img: bpy.types.Image):
	"""Navigates Blender to the specified image.
	
	:param img: Image to navigate to.
	:type img: :class:`bpy.types.Image`"""
	imgEditor = getOrMakeArea("IMAGE_EDITOR")
	space = imgEditor.spaces[0]
	space.image = img

def gotoShader(obj: bpy.types.Object):
	"""Navigates Blender to the material of the specified object.
	
	:param obj: Object to navigate to.
	:type obj: :class:`bpy.types.Object`"""
	mats = obj.material_slots
	if (len(mats) == 0):
		return
	
	nodeEditor = getOrMakeArea("NODE_EDITOR", "ShaderNodeTree")
	space = nodeEditor.spaces[0]
	space.shader_type = "OBJECT"

def gotoObject(obj: bpy.types.Object):
	"""Navigates Blender to the specified object.
	
	:param obj: Object to navigate to.
	:type obj: :class:`bpy.types.Object`"""
	space = getOrMakeArea("VIEW_3D").spaces[0]
	space.region_3d.view_rotation = Euler((3/math.pi,0,math.pi/4), "XYZ").to_quaternion()
	space.region_3d.view_location = obj.location

def gotoModifier():
	"""Navigates to the Modifiers tab."""
	space = getOrMakeArea("PROPERTIES").spaces[0]
	space.context = "MODIFIER"

def gotoShape():
	"""Navigates to the Mesh data tab."""
	space = getOrMakeArea("PROPERTIES").spaces[0]
	space.context = "DATA"
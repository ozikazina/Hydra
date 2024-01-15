"""Module responsible for thermal erosion."""

from Hydra.sim import heightmap
from Hydra.utils import texture
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

#Active texture list indices
_MAP_HEIGHT = 0
_MAP_REQUESTS = 1
_MAP_FREE = 2

def thermalPrepare(obj: bpy.types.Image | bpy.types.Object):
	"""Prepares textures for thermal erosion.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	print("Preparing for thermal erosion")
	data = common.data
	hyd = obj.hydra_erosion
	if not data.hasMap(hyd.map_base):
		heightmap.prepareHeightmap(obj)

	size = obj.hydra_erosion.getSize()

	data.active = [
		texture.clone(data.maps[hyd.map_source].texture),
		texture.createTextureFull(size),
		texture.createTexture(size)]
	print("Preparation finished")

def thermalRun(obj: bpy.types.Image | bpy.types.Object):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	ctx = data.context
	opts = obj.hydra_erosion
	size = opts.getSize()

	height = data.active[_MAP_HEIGHT]
	request = data.active[_MAP_REQUESTS]
	free = data.active[_MAP_FREE]

	progA = data.shaders["thermalA"]
	progB = data.shaders["thermalB"]

	mapI = 1
	mapO = 3
	temp = 3

	height.bind_to_image(1, read=True, write=True)
	request.bind_to_image(2, read=True, write=True)
	free.bind_to_image(3, read=True, write=True)

	progA["requests"].value = 2
	progA["Ks"] = opts.thermal_strength * 0.5	#0-1 -> 0-0.5, higher is unstable
	progA["alpha"] = math.tan(math.tau * opts.thermal_angle / 360) / (size[0] * opts.height_scale)#higher scale -> Z shrunk down -> lower alpha
	progA["by"] = opts.scale_ratio
	progB["requests"].value = 2

	diagonal = opts.thermal_solver == "diagonal"
	alternate = opts.thermal_solver == "both"

	time = datetime.now()
	for i in range(opts.thermal_iter_num):
		if alternate:
			diagonal = (i&1) == 1
		progA["diagonal"] = diagonal
		progA["mapH"].value = mapI
		progA.run(group_x = size[0], group_y = size[1])
		progB["diagonal"] = diagonal
		progB["mapH"].value = mapI
		progB["outH"].value = mapO
		progB.run(group_x = size[0], group_y = size[1])
		temp = mapI
		mapI = mapO
		mapO = temp

	ctx.finish()
	print((datetime.now() - time).total_seconds())

def thermalFinish(obj: bpy.types.Image | bpy.types.Object):
	"""Releases resources allocated for thermal erosion.
	
	:param obj: Object or image that was eroded.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	opts = obj.hydra_erosion
	
	data.releaseMap(opts.map_current)
	
	name = common.incrementLayer(data.maps[opts.map_source].name, "Thermal 1")

	hmid = data.createMap(name, data.active[_MAP_HEIGHT])
	opts.map_current = hmid

	data.active[_MAP_HEIGHT] = None #prevents release by releaseActive
	data.releaseActive()
	print("Erosion finished")
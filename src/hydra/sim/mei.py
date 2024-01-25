"""Module responsible for water erosion."""

import moderngl

from Hydra.utils import texture, model
from Hydra.sim import heightmap
from Hydra import common

import math, random

import bpy, bpy.types

# --------------------------------------------------------- Erosion

#Active texture list indices
MAP_HEIGHT = 0
MAP_PIPE = 1
MAP_VELOCITY = 2
MAP_WATER = 3
MAP_SEDIMENT = 4
MAP_TEMP = 5

def erosionPrepare(obj: bpy.types.Object | bpy.types.Image):
	"""Prepares textures for water erosion.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	print("Preparing for water erosion")
	data = common.data
	hyd = obj.hydra_erosion
	if not data.hasMap(hyd.map_base):
		heightmap.prepareHeightmap(obj)

	size = hyd.getSize()
	
	data.active = [
		texture.clone(data.maps[hyd.map_source].texture),#height
		texture.createTextureFull(size),#pipe
		common.data.context.texture(size, 2, dtype="f4"),#velocity
		texture.createTexture(size),#water
		texture.createTexture(size),#sediment
		texture.createTexture(size)	#temp
	]

	print("Preparation finished")

def erosionRun(obj: bpy.types.Object | bpy.types.Image):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	hyd = obj.hydra_erosion
	size = hyd.getSize()
	ctx = data.context
	data.active[MAP_HEIGHT].bind_to_image(1, read=True, write=True) #don't use 0 -> default value -> cross-contamination
	data.active[MAP_PIPE].bind_to_image(2, read=True, write=True)
	data.active[MAP_VELOCITY].bind_to_image(3, read=True, write=True)
	data.active[MAP_WATER].bind_to_image(4, read=True, write=True)
	data.active[MAP_SEDIMENT].bind_to_image(5, read=True, write=True)
	data.active[MAP_TEMP].bind_to_image(6, read=True, write=True)

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()

	for i in range(hyd.mei_iter_num):
		prog = data.shaders["mei1"]
		prog["d_map"].value = 4
		prog["dt"] = hyd.mei_dt
		prog["Ke"] = hyd.mei_evaporation
		prog["Kr"] = hyd.mei_rain
		prog.run(group_x=size[0], group_y=size[1])

		prog = data.shaders["mei2"]
		prog["b_map"].value = 1
		prog["pipe_map"].value = 2
		prog["d_map"].value = 4
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog.run(group_x=size[0], group_y=size[1])
	
		prog = data.shaders["mei3"]
		prog["pipe_map"].value = 2
		prog["d_map"].value = 4
		prog["c_map"].value = 6
		prog["dt"] = hyd.mei_dt
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog.run(group_x=size[0], group_y=size[1])

		prog = data.shaders["mei4"]
		prog["b_map"].value = 1
		prog["pipe_map"].value = 2
		prog["v_map"].value = 3
		prog["d_map"].value = 4
		prog["dmean_map"].value = 6
		prog["Kc"] = hyd.mei_capacity
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["minalpha"] = hyd.mei_min_alpha
		prog.run(group_x=size[0], group_y=size[1])

		prog = data.shaders["mei5"]
		prog["b_map"].value = 1
		prog["s_map"].value = 5
		prog["c_map"].value = 6
		prog["Ks"] = hyd.mei_erosion
		prog["Kd"] = hyd.mei_deposition
		prog.run(group_x=size[0], group_y=size[1])

		prog = data.shaders["mei6"]
		prog["s_alt_map"].value = 5
		prog["v_map"].value = 3
		prog["s_map"].value = 6
		prog["dt"] = hyd.mei_dt
		prog.run(group_x=size[0], group_y=size[1])

		ctx.finish()

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = 1 / hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()


def erosionFinish(obj: bpy.types.Object | bpy.types.Image)->list[bpy.types.Image]:
	"""Releases resources allocated for water erosion.
	
	:param obj: Object or image that was eroded.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	data.running = False
	data.iteration = 0

	opts = obj.hydra_erosion
	data.releaseMap(opts.map_current)
	
	name = common.incrementLayer(data.maps[opts.map_source].name, "Mei 1")
	hmid = data.createMap(name, data.active[MAP_HEIGHT])
	opts.map_current = hmid

	ret = []

	data.active[MAP_HEIGHT] = None #prevents release by releaseActive
	data.releaseActive()

	print("Erosion finished")
	return ret

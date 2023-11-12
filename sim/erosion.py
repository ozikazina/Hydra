"""Module responsible for water erosion."""

import moderngl

from Hydra.utils import texture, model
from Hydra.sim import heightmap, particle
from Hydra import common

import math, random

import bpy, bpy.types

# --------------------------------------------------------- Erosion

#Active texture list indices
MAP_HEIGHT = 0
MAP_SEDIMENT= 1
MAP_DEPTH = 2
MAP_COLOR = 3

def erosionPrepare(obj: bpy.types.Object | bpy.types.Image):
	"""Prepares textures for water erosion.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	print("Preparing for water erosion")
	data = common.data
	hyd = obj.hydra
	if not data.hasMap(hyd.map_base):
		heightmap.prepareHeightmap(obj)

	ctx = data.context
	size = hyd.getSize()
	subdiv = int(hyd.part_subdiv)
	data.fbo = ctx.simple_framebuffer((math.ceil(size[0]/subdiv),math.ceil(size[1]/subdiv)), 1, dtype="f4")
	data.scope = ctx.scope(data.fbo)
	
	data.active = [
		texture.clone(data.maps[hyd.map_source].texture),
		texture.createTexture(size) if hyd.out_sediment else None,
		texture.createTexture(size) if hyd.out_depth else None,
		texture.createColorTexture(size, bpy.data.images[hyd.color_src]) if hyd.out_color else None
	]

	print("Preparation finished")

def erosionRun(obj: bpy.types.Object | bpy.types.Image):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	hyd = obj.hydra
	ctx = data.context

	subdiv = int(hyd.part_subdiv)

	prog = data.programs["erosion"]
	vao = model.createVAO(ctx, prog)

	with data.scope:
		height = data.active[MAP_HEIGHT]
		height.bind_to_image(1, read=True, write=True)
		prog["img"].value = 1	#don't use 0 -> default value -> cross-contamination

		if hyd.out_depth:
			data.active[MAP_DEPTH].bind_to_image(2, read=True, write=True)
			prog["depth"].value = 2
		if hyd.out_sediment:
			data.active[MAP_SEDIMENT].bind_to_image(3, read=True, write=True)
			prog["sediment"].value = 3
		if hyd.out_color:
			data.active[MAP_COLOR].bind_to_image(4, read=True, write=True)
			prog["color"].value = 4

		prog["squareSize"] = subdiv
		prog["useColor"] = hyd.out_color
		prog["useSideData"] = hyd.out_depth or hyd.out_sediment

		particle.setUniformsFromOptions(prog, hyd)
		prog["interpolate"] = hyd.interpolate_erosion
		prog["interpolateColor"] = hyd.interpolate_color
		prog["bite"] = hyd.part_fineness
		prog["release"] = hyd.part_deposition * 0.5
		prog["colorStrength"] = hyd.color_mixing
		prog["capacityFactor"] = hyd.part_capacity * 1e-2
		prog["contrastErode"] = hyd.depth_contrast * 40
		prog["contrastDeposit"] = hyd.sed_contrast * 30
		prog["maxJump"] = hyd.part_maxjump

		for i in range(hyd.part_iter_num):
			for y in range(subdiv):
				for x in range(subdiv):
					prog["off"] = (x, y)
					vao.render(moderngl.TRIANGLES)
			
		ctx.finish()

	vao.release()

def erosionFinish(obj: bpy.types.Object | bpy.types.Image)->list[bpy.types.Image]:
	"""Releases resources allocated for water erosion.
	
	:param obj: Object or image that was eroded.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	data.running = False
	data.iteration = 0

	opts = obj.hydra
	data.releaseMap(opts.map_current)
	
	name = common.incrementLayer(data.maps[opts.map_source].name, "Particle 1")
	hmid = data.createMap(name, data.active[MAP_HEIGHT])
	opts.map_current = hmid

	ret = [None, None, None]

	if data.active[MAP_DEPTH]:
		ret[0] = texture.writeImage(f"HYD_{obj.name}_Depth", data.active[MAP_DEPTH])
	if data.active[MAP_SEDIMENT]:
		ret[1] = texture.writeImage(f"HYD_{obj.name}_Sediment", data.active[MAP_SEDIMENT])
	if data.active[MAP_COLOR]:
		ret[2] = texture.writeImage(f"HYD_{obj.name}_Color", data.active[MAP_COLOR])

	data.active[MAP_HEIGHT] = None #prevents release by releaseActive
	data.releaseActive()

	data.fbo.release()
	data.fbo = None
	data.scope = None
	
	print("Erosion finished")
	return ret

"""Module responsible for particle-based water erosion."""

from Hydra.utils import texture, model
from Hydra.sim import heightmap
from Hydra import common
from moderngl import Texture

import math
from datetime import datetime

import bpy, bpy.types

PARTICLE_MULTIPLIER = 20

def erode(obj: bpy.types.Object | bpy.types.Image)->None:
	"""Erodes the specified entity.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""

	print("Preparing for water erosion")
	data = common.data

	hyd = obj.hydra_erosion
	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	ctx = data.context
	size = hyd.get_size()
	
	if hyd.erosion_subres != min(size[0], size[1]):
		if size[0] > size[1]:
			size = (math.ceil(size[0] * hyd.erosion_subres / size[1]), hyd.erosion_subres)
		else:
			size = (hyd.erosion_subres, math.ceil(size[1] * hyd.erosion_subres / size[0]))
		height = heightmap.resize_texture(data.get_map(hyd.map_source).texture, size)
		height_base = texture.clone(height)
	else:
		height = texture.clone(data.get_map(hyd.map_source).texture)
		height_base = None

	tile_x = hyd.get_tiling_x()
	tile_y = hyd.get_tiling_y()

	if hyd.erosion_hardness_src in bpy.data.images:
		img = bpy.data.images[hyd.erosion_hardness_src]
		hardness = texture.create_texture(tuple(img.size), channels=1, image=img)
		hardness_sampler = ctx.sampler(texture=hardness, repeat_x=tile_x, repeat_y=tile_y)
		hardness.use(2)
		hardness_sampler.use(2)
	else:
		hardness = None

	prog = data.shaders["particle"]
	
	height_sampler = ctx.sampler(texture=height, repeat_x=tile_x, repeat_y=tile_y)

	height.bind_to_image(1, read=True, write=True)
	height.use(1)
	height_sampler.use(1)
	prog["height_sampler"] = 1
	prog["height_map"].value = 1

	prog["hardness_sampler"] = 2
	prog["use_hardness"] = hardness is not None
	prog["invert_hardness"] = hyd.erosion_invert_hardness

	prog["size"] = size
	prog["tile_size"] = (math.ceil(size[0] / 32), math.ceil(size[1] / 32))
	prog["tile_mult"] = (1 / size[0], 1 / size[1])

	prog["erosion_strength"] = hyd.part_fineness / 100
	prog["deposition_strength"] = hyd.part_deposition / 100
	prog["capacity_factor"] = hyd.part_capacity / 100

	prog["max_velocity"] = 2
	prog["acceleration"] = hyd.part_acceleration / 100
	prog["lateral_acceleration"] = hyd.part_lateral_acceleration / 100
	prog["lifetime"] = hyd.part_lifetime
	prog["iterations"] = hyd.part_iter_num * PARTICLE_MULTIPLIER
	prog["max_change"] = hyd.part_max_change / (100 * 100) # from percent to 0-0.01
	prog["drag"] = 1 - (hyd.part_drag / 100)

	prog["planet"] = hyd.tiling == "planet"
	prog["tile_x"] = tile_x
	prog["tile_y"] = tile_y

	time = datetime.now()
	prog.run(group_x=1, group_y=1)
	ctx.finish()

	print((datetime.now() - time).total_seconds())

	if hardness is not None:
		hardness.release()
		hardness_sampler.release()

	if height_base is not None: # resize back to original size
		height = heightmap.add_subres(height, height_base, data.get_map(hyd.map_source).texture)

	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Particle 1")
	hmid = data.create_map(name, height)
	hyd.map_result = hmid

	print("Erosion finished")

def color(obj: bpy.types.Object | bpy.types.Image)->bpy.types.Image:
	"""Simulates color transport on the specified entity.
	
	:param obj: Object or image to simulate on.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`
	:return: Color map.
	:rtype: :class:`bpy.types.Image`"""

	print("Preparing for color transport")
	data = common.data

	hyd = obj.hydra_erosion
	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	ctx = data.context
	size = hyd.get_size()

	if data.has_map(hyd.map_result):
		height = data.get_map(hyd.map_result).texture
	else:
		height = data.get_map(hyd.map_source).texture
	
	tile_x = hyd.get_tiling_x()
	tile_y = hyd.get_tiling_y()

	height = texture.clone(height)
	height.bind_to_image(1, read=True, write=True)
	height.use(1)
	height_sampler = ctx.sampler(texture=height, repeat_x=tile_x, repeat_y=tile_y)
	height_sampler.use(1)

	color = texture.create_texture(size, channels=4, image=bpy.data.images[hyd.color_src])
	color.bind_to_image(2, read=True, write=True)

	prog = data.shaders["particle_color"]

	prog["height_map"].value = 1
	prog["height_sampler"] = 1
	prog["color_map"].value = 2

	prog["size"] = size
	prog["tile_size"] = (math.ceil(size[0] / 32), math.ceil(size[1] / 32))
	prog["tile_mult"] = (1 / size[0], 1 / size[1])

	prog["erosion_strength"] = max(hyd.color_acceleration / 100, 0.01)
	prog["deposition_strength"] = 1 - hyd.color_mixing / 100
	prog["capacity_factor"] = max(1 - hyd.color_acceleration / 100, 0.01)

	prog["max_velocity"] = 2
	prog["acceleration"] = hyd.color_acceleration / 100
	prog["lateral_acceleration"] = 1
	prog["lifetime"] = hyd.color_lifetime
	prog["iterations"] = hyd.color_iter_num * PARTICLE_MULTIPLIER
	prog["drag"] = max(1 - (hyd.color_detail / 100), 0.01)

	prog["color_strength"] = hyd.color_mixing / 100

	prog["tile_x"] = tile_x
	prog["tile_y"] = tile_y

	time = datetime.now()
	prog.run(group_x=1,group_y=1)
	ctx.finish()

	print((datetime.now() - time).total_seconds())
	
	ret, _ = texture.write_image(f"HYD_{obj.name}_Color", color)

	color.release()
	height_sampler.release()
	if hyd.color_solver == "particle":
		height.release()

	print("Simulation finished")
	return ret
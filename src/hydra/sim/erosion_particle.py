"""Module responsible for water erosion."""

from Hydra.utils import texture, model
from Hydra.sim import heightmap
from Hydra import common

import math
from datetime import datetime

import bpy, bpy.types

def erode(obj: bpy.types.Object | bpy.types.Image):
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
	
	if hyd.erosion_subres != 100.0:
		size = (math.ceil(size[0] * hyd.erosion_subres / 100.0), math.ceil(size[1] * hyd.erosion_subres / 100.0))
		height = heightmap.resize_texture(data.get_map(hyd.map_source).texture, size)
		height_base = texture.clone(height)
	else:
		height = texture.clone(data.get_map(hyd.map_source).texture)
		height_base = None
	
	groups = (math.ceil(size[0] / 32), math.ceil(size[1] / 32))

	prog = data.shaders["particle"]
	
	height_sampler = ctx.sampler(texture=height, repeat_x=False, repeat_y=False)

	height.bind_to_image(1, read=True, write=True)
	height.use(1)
	height_sampler.use(1)
	prog["height_sampler"] = 1
	prog["height_map"].value = 1

	prog["tile_size"] = groups
	prog["tile_mult"] = (1 / size[0], 1 / size[1])

	prog["erosion_strength"] = hyd.part_fineness / 100
	prog["deposition_strength"] = hyd.part_deposition / 100
	prog["capacity_factor"] = hyd.part_capacity / 100

	prog["max_velocity"] = 2
	prog["acceleration"] = hyd.part_acceleration / 100
	prog["lifetime"] = hyd.part_lifetime
	prog["iterations"] = hyd.part_iter_num * hyd.part_iter_multiplier
	prog["max_change"] = hyd.part_max_change / (100 * 100) # from percent to 0-0.01
	prog["drag"] = 1 - (hyd.part_drag / 100)

	time = datetime.now()
	prog.run(group_x=1, group_y=1)
	ctx.finish()

	print((datetime.now() - time).total_seconds())

	if height_base is not None: # resize back to original size
		dif = heightmap.subtract(height, height_base) # get difference
		height_base.release()
		height.release()

		height = heightmap.resize_texture(dif, hyd.get_size()) # resize difference
		dif.release()

		nh = heightmap.add(height, data.get_map(hyd.map_source).texture) # add difference to original
		height.release()

		height = nh

	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Particle 1")
	hmid = data.create_map(name, height)
	hyd.map_result = hmid

	ret = {}

	print("Erosion finished")
	return ret

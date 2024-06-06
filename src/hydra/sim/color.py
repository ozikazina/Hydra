"""Module responsible for color transport."""

from Hydra.utils import texture
from Hydra.sim import heightmap
from Hydra import common

import math
from datetime import datetime

import bpy, bpy.types

def simulate(obj: bpy.types.Object | bpy.types.Image):
	"""Simulates color transport on the specified entity.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""

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
	height.bind_to_image(1, read=True, write=False)

	color = texture.create_texture(size, channels=4, image=bpy.data.images[hyd.color_src])
	color.bind_to_image(2, read=True, write=True)

	SQUARE_SIZE = 4

	groups = (math.ceil(size[0] / (32 * SQUARE_SIZE)), math.ceil(size[1] / (32 * SQUARE_SIZE)))

	prog = data.shaders["particle_color"]

	prog["height_map"].value = 1
	prog["color_map"].value = 2

	prog["square_size"] = SQUARE_SIZE

	prog["erosion_strength"] = hyd.part_fineness / 100

	prog["acceleration"] = hyd.part_acceleration / 100
	prog["lifetime"] = hyd.part_lifetime
	prog["iterations"] = hyd.part_iter_num
	prog["drag"] = 1 - (hyd.part_drag / 100)

	prog["color_strength"] = hyd.color_mixing / 100

	time = datetime.now()
	prog.run(group_x=groups[0], group_y=groups[1])
	ctx.finish()

	print((datetime.now() - time).total_seconds())

	ret, _ = texture.write_image(f"HYD_{obj.name}_Color", color)
	color.release()

	print("Simulation finished")
	return ret

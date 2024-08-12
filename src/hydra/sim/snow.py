"""Module responsible for snow simulation."""

from Hydra.sim import heightmap
from Hydra.utils import texture
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

def simulate(obj: bpy.types.Image | bpy.types.Object)->bpy.types.Image|None:
	"""Simulates snow movement on the specified entity.
	
	:param obj: Object or image to simulate on.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""

	data = common.data
	ctx = data.context
	hyd = obj.hydra_erosion

	print("Preparing for snow simulation")

	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	size = hyd.get_size()

	texture_only = hyd.snow_output == "texture"
	planet = hyd.tiling == "planet"

	if texture_only and data.has_map(hyd.map_result):
		offset = data.get_map(hyd.map_result).texture
	else:
		offset = data.get_map(hyd.map_source).texture

	snow = texture.create_texture(size)
	request = texture.create_texture(size, channels=4)
	free = texture.create_texture(size)

	progA = data.shaders["thermalA"]
	progB = data.shaders["thermalB"]
	snowProg = data.shaders["snow"]

	mapI = 1
	mapO = 3
	temp = 3

	snow.bind_to_image(1, read=True, write=True)
	request.bind_to_image(2, read=True, write=True)
	free.bind_to_image(3, read=True, write=True)
	offset.bind_to_image(4, read=True, write=False)

	tile_x = hyd.get_tiling_x()
	tile_y = hyd.get_tiling_y()

	progA["requests"].value = 2
	progA["Ks"] = 0.5
	progA["alpha"] = math.tan(hyd.snow_angle) * 2 / size[0] # images are scaled to 2 z/x -> angle depends only on image width
	if planet:
		progA["by"] = 1	# image ratio is fixed
	else:
		progA["by"] = hyd.scale_ratio * size[0] / size[1] # (model y/x) / (texture y/x)
	progA["offset"].value = 4
	progA["useOffset"] = True
	progA["ds"] = 1
	progA["size"] = size
	progA["tile_x"] = tile_x
	progA["tile_y"] = tile_y
	progA["planet"] = planet
	progA["tile_mult_y"] = math.pi / size[1]

	progB["requests"].value = 2
	progB["size"] = size
	progB["tile_x"] = tile_x
	progB["tile_y"] = tile_y
	progB["ds"] = 1

	SNOW_SCALE = 0.01

	snowProg["snow_add"] = (hyd.snow_add / 100) * SNOW_SCALE

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	snowProg["mapH"].value = mapI
	snowProg.run(group_x = group_x, group_y = group_y)

	time = datetime.now()
	for i in range(hyd.snow_iter_num):
		diagonal = (i&1) == 1

		progA["diagonal"] = diagonal
		progA["mapH"].value = mapI
		progA.run(group_x = group_x, group_y = group_y)

		progB["diagonal"] = diagonal
		progB["mapH"].value = mapI
		progB["outH"].value = mapO
		progB.run(group_x = group_x, group_y = group_y)

		temp = mapI
		mapI = mapO
		mapO = temp

	ctx.finish()

	print((datetime.now() - time).total_seconds())

	ret = None

	if hyd.snow_output != "displacement":
		snow_img = snow if texture_only else texture.clone(snow)
		snow_img.bind_to_image(5, read=True, write=True)
		prog = data.shaders["scaling"]
		prog["A"].value = 5	# snow
		prog["scale"] = 1 / (SNOW_SCALE * hyd.snow_add / 100)
		prog["offset"] = 0
		prog.run(group_x = size[0], group_y = size[1])

		img_name = f"HYD_{obj.name}_Snow"
		ret, ret_updated = texture.write_image(img_name, snow_img)
		snow_img.release()

	if hyd.snow_output != "texture":
		prog = data.shaders["scaled_add"]
		prog["A"].value = mapI
		prog["B"].value = 4	# offset - source map
		prog["factor"] = 1.0
		prog["scale"] = 1.0
		prog.run(group_x = size[0], group_y = size[1])

		data.try_release_map(hyd.map_result)
		name = common.increment_layer(data.get_map(hyd.map_source).name, "Snow 1")
		hmid = data.create_map(name, snow, base=data.get_map(hyd.map_source))
		hyd.map_result = hmid

	request.release()
	free.release()

	print("Simulation finished")

	return ret

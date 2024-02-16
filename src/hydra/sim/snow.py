"""Module responsible for snow simulation."""

from Hydra.sim import heightmap
from Hydra.utils import texture
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

def simulate(obj: bpy.types.Image | bpy.types.Object):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	ctx = data.context
	hyd = obj.hydra_erosion

	print("Preparing for snow simulation")

	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	size = hyd.get_size()

	offset = data.get_map(hyd.map_source).texture

	snow = texture.create_texture(size)
	request = texture.create_texture(size, channels=4)
	free = texture.create_texture(size)

	print("Preparation finished")

	progA = data.shaders["thermalA"]
	progB = data.shaders["thermalB"]
	snowProg = data.shaders["snow"]

	mapI = 1
	mapO = 3
	temp = 3

	snow.bind_to_image(1, read=True, write=True)
	offset.bind_to_image(4, read=True)
	request.bind_to_image(2, read=True, write=True)
	free.bind_to_image(3, read=True, write=True)

	progA["requests"].value = 2
	progA["Ks"] = 0.5
	progA["alpha"] = math.tan(math.tau * hyd.snow_angle / 360) * 2 / size[0] # images are scaled to 2 z/x -> angle depends only on image width
	progA["by"] = hyd.scale_ratio
	progA["offset"].value = 4
	progA["useOffset"] = True
	progA["ds"] = 1

	progB["requests"].value = 2
	progB["ds"] = 1

	snowProg["snow_add"] = hyd.snow_add / hyd.mei_scale

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

	snow_img = texture.clone(snow)
	snow_img.bind_to_image(5, read=True, write=True)
	prog = data.shaders["scaling"]
	prog["A"].value = 5	# snow
	prog["scale"] = hyd.mei_scale / hyd.snow_add
	prog.run(group_x = size[0], group_y = size[1])

	img_name = f"HYD_{obj.name}_Snow"
	ret = texture.write_image(img_name, snow_img)
	snow_img.release()

	prog = data.shaders["diff"]
	prog["A"].value = mapI
	prog["B"].value = 4	# offset - source map
	prog["factor"] = -1.0	#add instead of subtract
	prog.run(group_x = size[0], group_y = size[1])

	data.try_release_map(hyd.map_result)
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Snow 1")
	hmid = data.create_map(name, snow)
	hyd.map_result = hmid

	request.release()
	free.release()

	print("Erosion finished")

	return ret

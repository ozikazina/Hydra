"""Module responsible for thermal erosion."""

from Hydra.sim import heightmap
from Hydra.utils import texture
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

def erode(obj: bpy.types.Image | bpy.types.Object):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	data = common.data
	ctx = data.context
	hyd = obj.hydra_erosion

	print("Preparing for thermal erosion")

	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	size = hyd.get_size()

	height = texture.clone(data.get_map(hyd.map_source).texture)
	request = texture.create_texture(size, channels=4)
	free = texture.create_texture(size)

	print("Preparation finished")


	progA = data.shaders["thermalA"]
	progB = data.shaders["thermalB"]

	mapI = 1
	mapO = 3
	temp = 3

	height.bind_to_image(1, read=True, write=True)
	request.bind_to_image(2, read=True, write=True)
	free.bind_to_image(3, read=True, write=True)

	if hyd.thermal_use_stride:
		stride = hyd.thermal_stride
		if hyd.thermal_stride_grad:
			next_pass = hyd.thermal_iter_num // 2
	else:
		stride = 1


	progA["requests"].value = 2
	progA["Ks"] = hyd.thermal_strength * 0.5	#0-1 -> 0-0.5, higher is unstable
	progA["alpha"] = math.tan(math.tau * hyd.thermal_angle / 360) * 2 / size[0] # images are scaled to 2 z/x -> angle depends only on image width
	progA["by"] = hyd.scale_ratio
	progA["useOffset"] = False

	progB["requests"].value = 2

	diagonal = hyd.thermal_solver == "diagonal"
	alternate = hyd.thermal_solver == "both"

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	time = datetime.now()
	for i in range(hyd.thermal_iter_num):
		if alternate:
			diagonal = (i&1) == 1

		progA["diagonal"] = diagonal
		progA["mapH"].value = mapI
		progA["ds"] = stride
		progA.run(group_x = group_x, group_y = group_y)

		progB["diagonal"] = diagonal
		progB["mapH"].value = mapI
		progB["outH"].value = mapO
		progB["ds"] = stride
		progB.run(group_x = group_x, group_y = group_y)
		
		temp = mapI
		mapI = mapO
		mapO = temp

		if hyd.thermal_stride_grad and i >= next_pass:
			stride = math.ceil(stride / 2)
			next_pass += (hyd.thermal_iter_num - i) // 2

	ctx.finish()
	print((datetime.now() - time).total_seconds())
	
	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Thermal 1")

	hmid = data.create_map(name, height)
	hyd.map_result = hmid

	free.release()
	request.release()

	print("Erosion finished")

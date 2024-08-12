"""Module responsible for thermal erosion."""

from Hydra.sim import heightmap
from Hydra.utils import texture
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

def erode(obj: bpy.types.Image | bpy.types.Object)->None:
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
	planet = hyd.tiling == "planet"

	height = texture.clone(data.get_map(hyd.map_source).texture)
	request = texture.create_texture(size, channels=4)
	free = texture.create_texture(size)

	progA = data.shaders["thermalA"]
	progB = data.shaders["thermalB"]

	BIND_IN = 1
	BIND_OUT = 3

	def swap(a,b):
		return b,a

	request.bind_to_image(2, read=True, write=True)

	if planet:
		heightmap.rotate_equirect_to(height, free, BIND_IN, backwards=False)
		height, free = swap(height, free)

	stride = hyd.thermal_stride
	if hyd.thermal_stride_grad:
		next_pass = hyd.thermal_iter_num // 2

	tile_x = hyd.get_tiling_x()
	tile_y = hyd.get_tiling_y()

	progA["mapH"].value = BIND_IN
	progA["requests"].value = 2
	progA["Ks"] = (hyd.thermal_strength / 100) * 0.5	#0-1 -> 0-0.5, higher is unstable
	progA["alpha"] = math.tan(hyd.thermal_angle) * 2 / size[0] # images are scaled to 2 z/x -> angle depends only on image width
	if planet:
		progA["by"] = 1	# image ratio is fixed
	else:
		progA["by"] = hyd.scale_ratio * size[0] / size[1] # (model y/x) / (texture y/x)
	progA["useOffset"] = False
	progA["size"] = size
	progA["tile_x"] = tile_x
	progA["tile_y"] = tile_y
	progA["planet"] = planet
	progA["tile_mult_y"] = math.pi / size[1]

	progB["mapH"].value = BIND_IN
	progB["outH"].value = BIND_OUT
	progB["requests"].value = 2
	progB["size"] = size
	progB["tile_x"] = tile_x
	progB["tile_y"] = tile_y

	diagonal = hyd.thermal_solver == "diagonal"
	alternate = hyd.thermal_solver == "both"

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	time = datetime.now()
	for i in range(hyd.thermal_iter_num):
		if alternate:
			diagonal = (i&1) == 1

		height.bind_to_image(BIND_IN, True, False)
		free.bind_to_image(BIND_OUT, False, True)

		progA["diagonal"] = diagonal
		progA["ds"] = stride
		progA.run(group_x = group_x, group_y = group_y)

		progB["diagonal"] = diagonal
		progB["ds"] = stride
		progB.run(group_x = group_x, group_y = group_y)
		
		if planet and i == hyd.thermal_iter_num // 2:
			free.bind_to_image(BIND_OUT, True, True)
			heightmap.rotate_equirect_to(free, height, BIND_IN, backwards=True)
		else:
			height, free = swap(height, free)

		if hyd.thermal_stride_grad and i >= next_pass:
			stride = math.ceil(stride / 2)
			next_pass += (hyd.thermal_iter_num - i) // 2

	ctx.finish()
	print((datetime.now() - time).total_seconds())
	
	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Thermal 1")

	hmid = data.create_map(name, height, base=data.get_map(hyd.map_source))
	hyd.map_result = hmid

	free.release()
	request.release()

	print("Erosion finished")

"""Module responsible for water erosion."""

from Hydra.utils import texture
from Hydra.sim import heightmap
from Hydra import common
from moderngl import Texture

import bpy, bpy.types, math
from datetime import datetime

# --------------------------------------------------------- Erosion

def erode(obj: bpy.types.Object | bpy.types.Image):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	print("Preparing for water erosion")
	data = common.data
	ctx = data.context
	hyd = obj.hydra_erosion

	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	size = hyd.get_size()

	BIND_HEIGHT = 1 # don't use 0 -> default value -> cross-contamination
	BIND_PIPE = 2
	BIND_VELOCITY = 3
	BIND_WATER = 4
	BIND_SEDIMENT = 5
	BIND_TEMP = 6
	BIND_EXTRA = 7

	LOC_SEDIMENT = 1
	LOC_VELOCITY = 2

	height = texture.clone(data.get_map(hyd.map_source).texture)
	pipe = texture.create_texture(size, channels=4)
	velocity = texture.create_texture(size, channels=2)
	water = texture.create_texture(size)
	sediment = texture.create_texture(size)
	temp = texture.create_texture(size)	# capacity, water and sediment at different stages

	if hyd.erosion_hardness_src in bpy.data.images:
		hardness = texture.create_texture(size, channels=1, image=bpy.data.images[hyd.erosion_hardness_src])
	else:
		hardness = None

	if hyd.mei_water_src in bpy.data.images:
		water_src = texture.create_texture(size, channels=1, image=bpy.data.images[hyd.mei_water_src])
	else:
		water_src = None

	height.bind_to_image(BIND_HEIGHT, read=True, write=True)
	pipe.bind_to_image(BIND_PIPE, read=True, write=True)
	velocity.bind_to_image(BIND_VELOCITY, read=True, write=True)
	water.bind_to_image(BIND_WATER, read=True, write=True)
	sediment.bind_to_image(BIND_SEDIMENT, read=True, write=True)
	temp.bind_to_image(BIND_TEMP, read=True, write=True)

	sedimentSampler = ctx.sampler(texture=temp, repeat_x=False, repeat_y=False) # sediment will be in temp at stage 6
	temp.use(LOC_SEDIMENT)
	sedimentSampler.use(LOC_SEDIMENT)

	velocity_sampler = ctx.sampler(texture=velocity, repeat_x=False, repeat_y=False)
	velocity_sampler.use(LOC_VELOCITY)
	velocity.use(LOC_VELOCITY)

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	progs = [
		data.shaders["mei1"],
		data.shaders["mei2"],
		data.shaders["mei3"],
		data.shaders["mei4"],
		data.shaders["mei5"],
		data.shaders["mei6"]
	]

	dt = 1e-2
	pipe_len = 1
	evaporation = 0.01
	deposition = 0.25

	progs[0]["d_map"].value = BIND_WATER
	progs[0]["dt"] = dt
	progs[0]["Ke"] = evaporation
	progs[0]["Kr"] = (1 - (1 - (0.25 * hyd.mei_rain / 100) ** 2) ** 0.5) * 0.1
	progs[0]["water_src"].value = BIND_EXTRA
	progs[0]["use_water_src"] = water_src is not None
	progs[0]["rainfall"] = hyd.mei_randomize

	progs[1]["b_map"].value = BIND_HEIGHT
	progs[1]["pipe_map"].value = BIND_PIPE
	progs[1]["d_map"].value = BIND_WATER
	progs[1]["size"] = size
	progs[1]["lx"] = pipe_len
	progs[1]["ly"] = pipe_len
	progs[1]["A"] = 1

	progs[2]["pipe_map"].value = BIND_PIPE
	progs[2]["d_map"].value = BIND_WATER
	progs[2]["c_map"].value = BIND_TEMP
	progs[2]["dt"] = dt
	progs[2]["lx"] = pipe_len
	progs[2]["ly"] = pipe_len

	progs[3]["b_map"].value = BIND_HEIGHT
	progs[3]["pipe_map"].value = BIND_PIPE
	progs[3]["v_map"].value = BIND_VELOCITY
	progs[3]["d_map"].value = BIND_WATER
	progs[3]["dmean_map"].value = BIND_TEMP
	progs[3]["Kc"] = (hyd.mei_capacity / 100) * 0.25 * 0.002
	progs[3]["lx"] = pipe_len
	progs[3]["ly"] = pipe_len
	progs[3]["scale"] = size[0] / 2
	progs[3]["depth_scale"] = 1 / (hyd.mei_max_depth * 0.002)

	progs[4]["b_map"].value = BIND_HEIGHT
	progs[4]["s_map"].value = BIND_SEDIMENT
	progs[4]["c_map"].value = BIND_TEMP
	progs[4]["d_map"].value = BIND_WATER
	progs[4]["Ks"] = 1 - (1 - (hyd.mei_hardness / 100 - 1) ** 2) ** 0.15 # maps interval 0.5-1.0 to hardness 0.9-1.0
	progs[4]["Kd"] = deposition
	progs[4]["hardness_map"].value = BIND_EXTRA
	progs[4]["use_hardness"] = hardness is not None
	progs[4]["invert_hardness"] = hyd.erosion_invert_hardness

	progs[5]["out_s_map"].value = BIND_SEDIMENT
	progs[5]["v_map"].value = BIND_VELOCITY
	progs[5]["s_sampler"] = LOC_SEDIMENT
	progs[5]["v_sampler"] = LOC_VELOCITY
	progs[5]["dt"] = dt
	progs[5]["tile_mult"] = (1 / size[0], 1 / size[1])

	time = datetime.now()
	for i in range(hyd.mei_iter_num * 10):
		if water_src is not None:
			water_src.bind_to_image(BIND_EXTRA, read=True, write=False)
		
		progs[0]["seed"] = i
		progs[0].run(group_x=group_x, group_y=group_y)
		
		progs[1].run(group_x=group_x, group_y=group_y)
		progs[2].run(group_x=group_x, group_y=group_y)
		progs[3].run(group_x=group_x, group_y=group_y)

		if hardness is not None:
			hardness.bind_to_image(BIND_EXTRA, read=True, write=False)
		progs[4].run(group_x=group_x, group_y=group_y)

		progs[5].run(group_x=group_x, group_y=group_y)

	ctx.finish()
	print((datetime.now() - time).total_seconds())

	pipe.release()
	velocity.release()
	velocity_sampler.release()
	water.release()
	sediment.release()
	sedimentSampler.release()
	temp.release()

	if hardness is not None:
		hardness.release()
	
	if water_src is not None:
		water_src.release()
		
	size = hyd.get_size()

	hyd = obj.hydra_erosion
	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Mei 1")
	hmid = data.create_map(name, height)
	hyd.map_result = hmid

	print("Erosion finished")

def color(obj: bpy.types.Object | bpy.types.Image)->Texture:
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
	
	height = texture.clone(height)

	BIND_HEIGHT = 1 # don't use 0 -> default value -> cross-contamination
	BIND_PIPE = 2
	BIND_VELOCITY = 3
	BIND_WATER = 4
	BIND_TEMP = 6
	BIND_COLOR = 7

	LOC_COLOR = 1
	LOC_VELOCITY = 2

	def swap(a, b):
		return (b, a)

	pipe = texture.create_texture(size, channels=4)
	velocity = texture.create_texture(size, channels=2)
	water = texture.create_texture(size)
	temp = texture.create_texture(size)	# capacity, water and sediment at different stages
	colorA = texture.create_texture(size, channels=4, image=bpy.data.images[hyd.color_src])
	colorB = texture.create_texture(size, channels=4)
	colorSamplerA = ctx.sampler(texture=colorA)
	colorSamplerB = ctx.sampler(texture=colorB)

	height.bind_to_image(BIND_HEIGHT, read=True, write=False)
	pipe.bind_to_image(BIND_PIPE, read=True, write=True)
	velocity.bind_to_image(BIND_VELOCITY, read=True, write=True)
	water.bind_to_image(BIND_WATER, read=True, write=True)
	temp.bind_to_image(BIND_TEMP, read=True, write=True)

	velocity_sampler = ctx.sampler(texture=velocity, repeat_x=False, repeat_y=False)
	velocity_sampler.use(LOC_VELOCITY)
	velocity.use(LOC_VELOCITY)

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	progs = [
		data.shaders["mei1"],
		data.shaders["mei2"],
		data.shaders["mei3"],
		data.shaders["mei4"],
		data.shaders["mei_color"],
	]

	dt = 0.25 + 0.25 * (hyd.color_detail / 100)
	pipe_len = 1 + 2 * hyd.color_speed / 100

	progs[0]["d_map"].value = BIND_WATER
	progs[0]["dt"] = dt
	progs[0]["Ke"] = hyd.color_evaporation / 100
	progs[0]["Kr"] = (1 - (1 - (hyd.color_rain / 500) ** 2) ** 0.15) * 0.1
	progs[0]["use_water_src"] = False
	progs[0]["rainfall"] = False

	progs[1]["b_map"].value = BIND_HEIGHT
	progs[1]["pipe_map"].value = BIND_PIPE
	progs[1]["d_map"].value = BIND_WATER
	progs[1]["size"] = size
	progs[1]["lx"] = pipe_len
	progs[1]["ly"] = pipe_len
	progs[1]["A"] = 1

	progs[2]["pipe_map"].value = BIND_PIPE
	progs[2]["d_map"].value = BIND_WATER
	progs[2]["c_map"].value = BIND_TEMP
	progs[2]["dt"] = dt
	progs[2]["lx"] = pipe_len
	progs[2]["ly"] = pipe_len

	progs[3]["b_map"].value = BIND_HEIGHT
	progs[3]["pipe_map"].value = BIND_PIPE
	progs[3]["v_map"].value = BIND_VELOCITY
	progs[3]["d_map"].value = BIND_WATER
	progs[3]["dmean_map"].value = BIND_TEMP
	progs[3]["Kc"] = 0
	progs[3]["lx"] = pipe_len
	progs[3]["ly"] = pipe_len
	progs[3]["scale"] = size[0] / 2

	progs[4]["v_map"].value = BIND_VELOCITY
	progs[4]["color_map"].value = BIND_TEMP
	progs[4]["out_color_map"].value = BIND_COLOR
	progs[4]["color_sampler"] = LOC_COLOR
	progs[4]["v_sampler"] = LOC_VELOCITY
	progs[4]["dt"] = dt
	progs[4]["color_scaling"] =  1 / (100 - 99 * (hyd.color_mixing / 100))
	progs[4]["tile_mult"] = (1 / size[0], 1 / size[1])

	time = datetime.now()
	for _ in range(hyd.mei_iter_num):
		progs[0].run(group_x=group_x, group_y=group_y)
		progs[1].run(group_x=group_x, group_y=group_y)
		progs[2].run(group_x=group_x, group_y=group_y)
		progs[3].run(group_x=group_x, group_y=group_y)
	
		colorA.use(LOC_COLOR)
		colorSamplerA.use(LOC_COLOR)
		
		colorA.bind_to_image(BIND_TEMP, read=True, write=False)
		colorB.bind_to_image(BIND_COLOR, write=True)

		progs[4].run(group_x=group_x, group_y=group_y)

		temp.bind_to_image(BIND_TEMP, read=True, write=True)

		colorA, colorB = swap(colorA, colorB)
		colorSamplerA, colorSamplerB = swap(colorSamplerA, colorSamplerB)

	ctx.finish()
	print((datetime.now() - time).total_seconds())

	height.release()
	pipe.release()
	velocity.release()
	water.release()
	temp.release()

	ret, _ = texture.write_image(f"HYD_{obj.name}_Color", colorA)

	colorA.release()
	colorB.release()
	colorSamplerA.release()
	colorSamplerB.release()

	velocity_sampler.release()

	print("Simulation finished")
	return ret
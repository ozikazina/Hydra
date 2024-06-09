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

	BIND_HEIGHT = 1
	BIND_PIPE = 2
	BIND_VELOCITY = 3
	BIND_WATER = 4
	BIND_SEDIMENT = 5
	BIND_TEMP = 6

	LOC_SEDIMENT = 1

	height = texture.clone(data.get_map(hyd.map_source).texture)
	pipe = texture.create_texture(size, channels=4)
	velocity = texture.create_texture(size, channels=2)
	water = texture.create_texture(size)
	sediment = texture.create_texture(size)
	temp = texture.create_texture(size)	# capacity, water and sediment at different stages

	height.bind_to_image(BIND_HEIGHT, read=True, write=True) # don't use 0 -> default value -> cross-contamination
	pipe.bind_to_image(BIND_PIPE, read=True, write=True)
	velocity.bind_to_image(BIND_VELOCITY, read=True, write=True)
	water.bind_to_image(BIND_WATER, read=True, write=True)
	sediment.bind_to_image(BIND_SEDIMENT, read=True, write=True)
	temp.bind_to_image(BIND_TEMP, read=True, write=True)

	sedimentSampler = ctx.sampler(texture=temp, repeat_x=False, repeat_y=False) # sediment will be in temp at stage 6
	temp.use(LOC_SEDIMENT)
	sedimentSampler.use(LOC_SEDIMENT)

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	diagonal:bool = hyd.mei_direction == "diagonal"
	alternate:bool = hyd.mei_direction == "both"

	switch_after = max(min(32, math.ceil(hyd.mei_iter_num / 2)), 2)

	progs = [
		data.shaders["mei1"],
		data.shaders["mei2"],
		data.shaders["mei3"],
		data.shaders["mei4"],
		data.shaders["mei5"],
		data.shaders["mei6"]
	]

	progs[0]["d_map"].value = BIND_WATER
	progs[0]["dt"] = hyd.mei_dt
	progs[0]["Ke"] = hyd.mei_evaporation / 100
	progs[0]["Kr"] = hyd.mei_rain / 100

	prog[1]["b_map"].value = BIND_HEIGHT
	prog[1]["pipe_map"].value = BIND_PIPE
	prog[1]["d_map"].value = BIND_WATER
	prog[1]["lx"] = hyd.mei_length[0]
	prog[1]["ly"] = hyd.mei_length[1]

	progs[2]["pipe_map"].value = BIND_PIPE
	progs[2]["d_map"].value = BIND_WATER
	progs[2]["c_map"].value = BIND_TEMP
	progs[2]["dt"] = hyd.mei_dt
	progs[2]["lx"] = hyd.mei_length[0]
	progs[2]["ly"] = hyd.mei_length[1]

	progs[3]["b_map"].value = BIND_HEIGHT
	progs[3]["pipe_map"].value = BIND_PIPE
	progs[3]["v_map"].value = BIND_VELOCITY
	progs[3]["d_map"].value = BIND_WATER
	progs[3]["dmean_map"].value = BIND_TEMP
	progs[3]["Kc"] = hyd.mei_capacity / 100
	progs[3]["lx"] = hyd.mei_length[0]
	progs[3]["ly"] = hyd.mei_length[1]
	progs[3]["minalpha"] = hyd.mei_min_alpha
	progs[3]["scale"] = 512 / hyd.mei_scale

	progs[4]["b_map"].value = BIND_HEIGHT
	progs[4]["s_map"].value = BIND_SEDIMENT
	progs[4]["c_map"].value = BIND_TEMP
	progs[4]["Ks"] = hyd.mei_erosion / (100 * 4)
	progs[4]["Kd"] = hyd.mei_deposition / (100 * 2)

	progs[5]["out_s_map"].value = BIND_SEDIMENT
	progs[5]["v_map"].value = BIND_VELOCITY
	progs[5]["s_sampler"] = LOC_SEDIMENT
	progs[5]["dt"] = hyd.mei_dt

	time = datetime.now()
	for i in range(hyd.mei_iter_num):
		switch = alternate and i % switch_after == switch_after - 1

		progs[0].run(group_x=group_x, group_y=group_y)
		
		prog[1]["diagonal"] = diagonal
		prog[1]["erase"] = switch
		progs[1].run(group_x=group_x, group_y=group_y)

		progs[2]["diagonal"] = diagonal
		progs[2].run(group_x=group_x, group_y=group_y)

		progs[3]["diagonal"] = diagonal
		progs[3].run(group_x=group_x, group_y=group_y)
		progs[4].run(group_x=group_x, group_y=group_y)

		progs[5]["diagonal"] = diagonal
		progs[5].run(group_x=group_x, group_y=group_y)

		if switch:
			diagonal = not diagonal

	ctx.finish()
	print((datetime.now() - time).total_seconds())

	pipe.release()
	velocity.release()
	water.release()
	sediment.release()
	temp.release()

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = 1 / hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()

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

	BIND_HEIGHT = 1
	BIND_PIPE = 2
	BIND_VELOCITY = 3
	BIND_WATER = 4
	BIND_TEMP = 6
	BIND_COLOR = 7

	LOC_COLOR = 1

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

	height.bind_to_image(BIND_HEIGHT, read=True, write=False) # don't use 0 -> default value -> cross-contamination
	pipe.bind_to_image(BIND_PIPE, read=True, write=True)
	velocity.bind_to_image(BIND_VELOCITY, read=True, write=True)
	water.bind_to_image(BIND_WATER, read=True, write=True)
	temp.bind_to_image(BIND_TEMP, read=True, write=True)

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	progs = [
		data.shaders["mei1"],
		data.shaders["mei2"],
		data.shaders["mei3"],
		data.shaders["mei4"],
		data.shaders["mei_color"],
	]

	progs[0]["d_map"].value = BIND_WATER
	progs[0]["dt"] = hyd.mei_dt
	progs[0]["Ke"] = hyd.mei_evaporation / 100
	progs[0]["Kr"] = hyd.mei_rain / 100

	progs[1]["b_map"].value = BIND_HEIGHT
	progs[1]["pipe_map"].value = BIND_PIPE
	progs[1]["d_map"].value = BIND_WATER
	progs[1]["lx"] = hyd.mei_length[0]
	progs[1]["ly"] = hyd.mei_length[1]
	progs[1]["diagonal"] = True
	progs[1]["erase"] = False

	progs[2]["pipe_map"].value = BIND_PIPE
	progs[2]["d_map"].value = BIND_WATER
	progs[2]["c_map"].value = BIND_TEMP
	progs[2]["dt"] = hyd.mei_dt
	progs[2]["lx"] = hyd.mei_length[0]
	progs[2]["ly"] = hyd.mei_length[1]
	progs[2]["diagonal"] = True

	progs[3]["b_map"].value = BIND_HEIGHT
	progs[3]["pipe_map"].value = BIND_PIPE
	progs[3]["v_map"].value = BIND_VELOCITY
	progs[3]["d_map"].value = BIND_WATER
	progs[3]["dmean_map"].value = BIND_TEMP
	progs[3]["Kc"] = hyd.mei_capacity / 100
	progs[3]["lx"] = hyd.mei_length[0]
	progs[3]["ly"] = hyd.mei_length[1]
	progs[3]["minalpha"] = hyd.mei_min_alpha
	progs[3]["scale"] = 512 / hyd.mei_scale
	progs[3]["diagonal"] = True

	progs[4]["v_map"].value = BIND_VELOCITY
	progs[4]["out_color_map"].value = BIND_COLOR
	progs[4]["color_sampler"] = LOC_COLOR
	progs[4]["dt"] = hyd.mei_dt
	progs[4]["diagonal"] = True
	progs[4]["color_scaling"] =  1 / (100 - 99 * (hyd.color_mixing / 100))

	time = datetime.now()
	for _ in range(hyd.mei_iter_num):
		progs[0].run(group_x=group_x, group_y=group_y)
		progs[1].run(group_x=group_x, group_y=group_y)
		progs[2].run(group_x=group_x, group_y=group_y)
		progs[3].run(group_x=group_x, group_y=group_y)
	
		colorA.use(LOC_COLOR)
		colorSamplerA.use(LOC_COLOR)
		colorB.bind_to_image(BIND_COLOR, write=True)

		progs[4].run(group_x=group_x, group_y=group_y)

		colorA, colorB = swap(colorA, colorB)
		colorSamplerA, colorSamplerB = swap(colorSamplerA, colorSamplerB)

	ctx.finish()
	print((datetime.now() - time).total_seconds())

	ret, _ = texture.write_image(f"HYD_{obj.name}_Color", colorA)

	height.release()
	pipe.release()
	velocity.release()
	water.release()
	temp.release()

	colorA.release()
	colorB.release()
	colorSamplerA.release()
	colorSamplerB.release()

	print("Simulation finished")
	return ret
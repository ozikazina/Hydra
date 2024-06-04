"""Module responsible for water erosion."""

from Hydra.utils import texture
from Hydra.sim import heightmap
from Hydra import common

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
	BIND_COLOR = 7

	LOC_SEDIMENT = 1
	LOC_COLOR = 2


	height = texture.clone(data.get_map(hyd.map_source).texture)
	pipe = texture.create_texture(size, channels=4)
	velocity = texture.create_texture(size, channels=2)
	water = texture.create_texture(size)
	sediment = texture.create_texture(size)
	temp = texture.create_texture(size)	# capacity, water and sediment at different stages

	if hyd.mei_out_color:
		colorA = texture.create_texture(size, channels=4, image=bpy.data.images[hyd.color_src])
		colorB = texture.create_texture(size, channels=4)
		colorSamplerA = ctx.sampler(texture=colorA)
		colorSamplerB = ctx.sampler(texture=colorB)
	else:
		colorA = None
		colorB = None

	height.bind_to_image(BIND_HEIGHT, read=True, write=True) # don't use 0 -> default value -> cross-contamination
	pipe.bind_to_image(BIND_PIPE, read=True, write=True)
	velocity.bind_to_image(BIND_VELOCITY, read=True, write=True)
	water.bind_to_image(BIND_WATER, read=True, write=True)
	sediment.bind_to_image(BIND_SEDIMENT, read=True, write=True)
	temp.bind_to_image(BIND_TEMP, read=True, write=True)


	def swap(a, b):
		return (b, a)

	sedimentSampler = ctx.sampler(texture=temp) # sediment will be in temp at stage 6
	temp.use(LOC_SEDIMENT)
	sedimentSampler.use(LOC_SEDIMENT)

	prog = data.shaders["scaling"]
	prog["A"].value = 1
	prog["scale"] = hyd.mei_scale
	prog.run(group_x=size[0], group_y=size[1])
	ctx.finish()

	group_x = math.ceil(size[0] / 32)
	group_y = math.ceil(size[1] / 32)

	capacity = hyd.mei_capacity

	diagonal:bool = hyd.mei_direction == "diagonal"
	alternate:bool = hyd.mei_direction == "both"

	switch_after = max(min(32, math.ceil(hyd.mei_iter_num / 2)), 2)

	time = datetime.now()
	for i in range(hyd.mei_iter_num):
		switch = alternate and i % switch_after == switch_after - 1

		prog = data.shaders["mei1"]
		prog["d_map"].value = BIND_WATER
		prog["dt"] = hyd.mei_dt
		prog["Ke"] = hyd.mei_evaporation
		prog["Kr"] = hyd.mei_rain
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei2"]
		prog["b_map"].value = BIND_HEIGHT
		prog["pipe_map"].value = BIND_PIPE
		prog["d_map"].value = BIND_WATER
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["diagonal"] = diagonal
		prog["erase"] = switch
		prog.run(group_x=group_x, group_y=group_y)
	
		prog = data.shaders["mei3"]
		prog["pipe_map"].value = BIND_PIPE
		prog["d_map"].value = BIND_WATER
		prog["c_map"].value = BIND_TEMP
		prog["dt"] = hyd.mei_dt
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["diagonal"] = diagonal
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei4"]
		prog["b_map"].value = BIND_HEIGHT
		prog["pipe_map"].value = BIND_PIPE
		prog["v_map"].value = BIND_VELOCITY
		prog["d_map"].value = BIND_WATER
		prog["dmean_map"].value = BIND_TEMP
		prog["Kc"] = capacity
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["minalpha"] = hyd.mei_min_alpha
		prog["scale"] = 1 / hyd.mei_scale
		prog["diagonal"] = diagonal
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei5"]
		prog["b_map"].value = BIND_HEIGHT
		prog["s_map"].value = BIND_SEDIMENT
		prog["c_map"].value = BIND_TEMP
		prog["Ks"] = hyd.mei_erosion
		prog["Kd"] = hyd.mei_deposition
		prog.run(group_x=group_x, group_y=group_y)

		if hyd.mei_out_color:
			colorA.use(LOC_COLOR)
			colorSamplerA.use(LOC_COLOR)
			colorB.bind_to_image(BIND_COLOR, write=True)

		prog = data.shaders["mei6"]
		prog["out_s_map"].value = BIND_SEDIMENT
		prog["v_map"].value = BIND_VELOCITY
		prog["s_sampler"] = LOC_SEDIMENT
		prog["dt"] = hyd.mei_dt
		prog["diagonal"] = diagonal
		prog["use_color"] = hyd.mei_out_color
		prog["color_scaling"] =  1 / (100 - 99 * (hyd.mei_color_mixing / 100))
		prog["out_color_map"].value = BIND_COLOR
		prog["color_sampler"] = LOC_COLOR
		prog.run(group_x=group_x, group_y=group_y)

		if hyd.mei_out_color:
			colorA, colorB = swap(colorA, colorB)
			colorSamplerA, colorSamplerB = swap(colorSamplerA, colorSamplerB)

		if switch:
			diagonal = not diagonal

	ctx.finish()
	print((datetime.now() - time).total_seconds())

	pipe.release()
	velocity.release()
	water.release()
	sediment.release()
	temp.release()

	ret = {}

	if colorA:
		ret["color"], _ = texture.write_image(f"HYD_{obj.name}_Color", colorA)
		colorA.release()
		colorB.release()
		colorSamplerA.release()
		colorSamplerB.release()

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

	return ret
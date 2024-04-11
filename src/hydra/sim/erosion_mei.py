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
	
	height = texture.clone(data.get_map(hyd.map_source).texture) #height
	pipe = texture.create_texture(size, channels=4) #pipe
	velocity = texture.create_texture(size, channels=2) #velocity
	water = texture.create_texture(size) #water
	sediment = texture.create_texture(size) #sediment
	temp = texture.create_texture(size)	#temp

	height.bind_to_image(1, read=True, write=True) #don't use 0 -> default value -> cross-contamination
	pipe.bind_to_image(2, read=True, write=True)
	velocity.bind_to_image(3, read=True, write=True)
	water.bind_to_image(4, read=True, write=True)
	sediment.bind_to_image(5, read=True, write=True)
	temp.bind_to_image(6, read=True, write=True)

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

	time = datetime.now()
	for i in range(hyd.mei_iter_num):
		switch = alternate and i % 64 == 63

		prog = data.shaders["mei1"]
		prog["d_map"].value = 4
		prog["dt"] = hyd.mei_dt
		prog["Ke"] = hyd.mei_evaporation
		prog["Kr"] = hyd.mei_rain
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei2"]
		prog["b_map"].value = 1
		prog["pipe_map"].value = 2
		prog["d_map"].value = 4
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["max_drop"] = hyd.part_maxjump * hyd.mei_scale
		prog["diagonal"] = diagonal
		prog["erase"] = switch
		prog.run(group_x=group_x, group_y=group_y)
	
		prog = data.shaders["mei3"]
		prog["pipe_map"].value = 2
		prog["d_map"].value = 4
		prog["c_map"].value = 6
		prog["dt"] = hyd.mei_dt
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["diagonal"] = diagonal
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei4"]
		prog["b_map"].value = 1
		prog["pipe_map"].value = 2
		prog["v_map"].value = 3
		prog["d_map"].value = 4
		prog["dmean_map"].value = 6
		prog["Kc"] = capacity
		prog["lx"] = hyd.mei_length[0]
		prog["ly"] = hyd.mei_length[1]
		prog["minalpha"] = hyd.mei_min_alpha
		prog["scale"] = 1 / hyd.mei_scale
		prog["diagonal"] = diagonal
		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei5"]
		prog["b_map"].value = 1
		prog["s_map"].value = 5
		prog["c_map"].value = 6
		prog["Ks"] = hyd.mei_erosion
		prog["Kd"] = hyd.mei_deposition

		prog.run(group_x=group_x, group_y=group_y)

		prog = data.shaders["mei6"]
		prog["s_alt_map"].value = 5
		prog["v_map"].value = 3
		prog["s_map"].value = 6
		prog["dt"] = hyd.mei_dt
		prog["diagonal"] = diagonal
		prog.run(group_x=group_x, group_y=group_y)

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
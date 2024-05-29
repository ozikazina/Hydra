"""Module responsible for water erosion."""

from moderngl import TRIANGLES

from Hydra.utils import texture, model
from Hydra.sim import heightmap
from Hydra import common

import math
from datetime import datetime

import bpy, bpy.types

def erode(obj: bpy.types.Object | bpy.types.Image):
	"""Erodes the specified entity. Can be run multiple times.
	
	:param obj: Object or image to erode.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""

	print("Preparing for water erosion")
	data = common.data
	use_vao: bool = common.get_preferences().particle_use_vao

	hyd = obj.hydra_erosion
	if not data.has_map(hyd.map_base):
		heightmap.prepare_heightmap(obj)

	ctx = data.context
	size = hyd.get_size()
	subdiv = int(hyd.part_subdiv)
	
	if hyd.erosion_subres != 1:
		size = (math.ceil(size[0] * hyd.erosion_subres / 100.0), math.ceil(size[1] * hyd.erosion_subres / 100.0))
		height = heightmap.resize_texture(data.get_map(hyd.map_source).texture, size)
		height_base = texture.clone(height)
	else:
		height = texture.clone(data.get_map(hyd.map_source).texture)
		height_base = None
	
	sediment = texture.create_texture(size) if hyd.out_sediment else None
	depth = texture.create_texture(size) if hyd.out_depth else None
	color = texture.create_texture(size, image=bpy.data.images[hyd.color_src]) if hyd.out_color else None

	if use_vao:
		prog = data.programs["erosion"]
	else:
		prog = data.shaders["erosion"]

	height.bind_to_image(1, read=True, write=True)
	prog["img"].value = 1	#don't use 0 -> default value -> cross-contamination

	if depth:
		depth.bind_to_image(2, read=True, write=True)
		prog["depth"].value = 2
	if sediment:
		sediment.bind_to_image(3, read=True, write=True)
		prog["sediment"].value = 3
	if color:
		color.bind_to_image(4, read=True, write=True)
		prog["color"].value = 4

	prog["square_size"] = subdiv
	prog["use_color"] = hyd.out_color
	prog["use_side_data"] = hyd.out_depth or hyd.out_sediment

	prog["interpolate"] = hyd.interpolate_erosion
	prog["interpolate_color"] = hyd.interpolate_color
	prog["erosion_strength"] = hyd.part_fineness
	prog["deposition_strength"] = hyd.part_deposition * 0.5
	prog["color_strength"] = hyd.color_mixing
	prog["capacity_factor"] = hyd.part_capacity * 1e-2
	prog["contrast_erode"] = hyd.depth_contrast * 40
	prog["contrast_deposit"] = hyd.sed_contrast * 30
	prog["max_jump"] = hyd.part_maxjump

	prog["acceleration"] = hyd.part_acceleration
	prog["iterations"] = hyd.part_lifetime
	prog["drag"] = 1-hyd.part_drag	#multiplicative factor

	time = datetime.now()
	if use_vao:
		resX = math.ceil(size[0] / subdiv)
		resY = math.ceil(size[1] / subdiv)

		vao = model.create_vao(ctx, prog)
		fbo = ctx.framebuffer(ctx.texture((resX, resY), 1, dtype="f1"))
		with ctx.scope(fbo):
			for _ in range(hyd.part_iter_num):
				for y in range(subdiv):
					for x in range(subdiv):
						prog["off"] = (x, y)
						vao.render()

		fbo.release()
		vao.release()
	else:
		group_x = math.ceil(size[0] / (subdiv * 32))
		group_y = math.ceil(size[1] / (subdiv * 32))

		for _ in range(hyd.part_iter_num):
			for y in range(subdiv):
				for x in range(subdiv):
					prog["off"] = (x, y)
					prog.run(group_x=group_x, group_y=group_y)
			
	ctx.finish()
	print((datetime.now() - time).total_seconds())

	if height_base is not None: # resize back to original size
		dif = heightmap.subtract(height, height_base) # get difference
		texture.write_image("tst_diff", dif)
		height_base.release()
		height.release()

		height = heightmap.resize_texture(dif, hyd.get_size()) # resize difference
		texture.write_image("tst_resized", height)
		dif.release()

		nh = heightmap.add(height, data.get_map(hyd.map_source).texture) # add difference to original
		height.release()

		height = nh

	data.try_release_map(hyd.map_result)
	
	name = common.increment_layer(data.get_map(hyd.map_source).name, "Particle 1")
	hmid = data.create_map(name, height)
	hyd.map_result = hmid

	ret = {}

	if depth:
		ret["depth"], _ = texture.write_image(f"HYD_{obj.name}_Depth", depth)
		depth.release()
	if sediment:
		ret["sediment"], _ = texture.write_image(f"HYD_{obj.name}_Sediment", sediment)
		sediment.release()
	if color:
		ret["color"], _ = texture.write_image(f"HYD_{obj.name}_Color", color)
		color.release()

	print("Erosion finished")
	return ret

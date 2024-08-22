"""Module responsible for flow simulation."""

from Hydra.sim import heightmap
from Hydra.utils import texture, model
from Hydra import common
import bpy.types
import math
from datetime import datetime

# --------------------------------------------------------- Flow

def generate_flow(obj: bpy.types.Image | bpy.types.Object)->bpy.types.Image:
	"""Simulates a flow map on the specified entity.
	
	:param obj: Object or image to simulate on.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`
	:return: Flow map.
	:rtype: :class:`bpy.types.Image`"""
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
	
	flow = texture.create_texture(size)

	planet = hyd.tiling == "planet"
	tile_x = hyd.get_tiling_x()
	tile_y = hyd.get_tiling_y()

	BIND_FLOW = 2

	if planet:
		height_org = height
		height_rot = texture.clone(height)
		heightmap.rotate_equirect_to(height, height_rot, 1, sampler_use=2, backwards=False)
		height = height_rot

	height_sampler = ctx.sampler(texture=height, repeat_x=tile_x, repeat_y=tile_y)
	height.use(1)
	height_sampler.use(1)

	prog = data.shaders["flow"]
	prog["height_sampler"] = 1
	flow.bind_to_image(BIND_FLOW, read=True, write=True)
	prog["flow"].value = BIND_FLOW

	prog["tile_mult"] = (1 / size[0], 1 / size[1])
	prog["tile_size"] = (math.ceil(size[0] / 32), math.ceil(size[1] / 32))
	prog["planet"] = planet

	# map to aesthetic range 0.0003-0.2
	prog["strength"] = 0.2*math.exp(-6.61*(1 - hyd.flow_brightness / 100))

	prog["acceleration"] = hyd.part_acceleration / 100
	prog["lifetime"] = hyd.part_lifetime
	prog["drag"] = 1-(hyd.part_drag / 100)	# multiplicative factor

	time = datetime.now()

	if planet:
		prog["iterations"] = hyd.flow_iter_num // 2
		prog.run(group_x=1, group_y=1)

		height.release()
		height = height_org
		height.use(1)

		flow_rot = texture.clone(flow)
		heightmap.rotate_equirect_to(flow, flow_rot, 1, sampler_use=2, backwards=True)
		flow.release()
		flow = flow_rot
		flow.bind_to_image(BIND_FLOW, read=True, write=True)

		prog.run(group_x=1, group_y=1)
	else:
		prog["iterations"] = hyd.flow_iter_num
		prog.run(group_x=1, group_y=1)

	ctx.finish()

	final_amount = texture.create_texture(flow.size)
	final_amount.bind_to_image(3, read=True, write=True)
	prog = data.shaders["plug"]
	prog["inMap"].value = 2
	prog["outMap"].value = 3

	prog.run(group_x=size[0], group_y=size[1])

	print((datetime.now() - time).total_seconds())

	img_name = f"HYD_{obj.name}_Flow"
	ret, _ = texture.write_image(img_name, final_amount)
	flow.release()
	final_amount.release()
	
	return ret

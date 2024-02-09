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
	amount = texture.create_texture(size)

	subdiv = int(hyd.flow_subdiv)

	prog = data.shaders["flow"]
	height.bind_to_image(1, read=True, write=False)
	prog["img"].value = 1
	amount.bind_to_image(2, read=True, write=True)
	prog["flow"].value = 2
	prog["squareSize"] = subdiv
	prog["interpolate"] = hyd.interpolate_flow

	prog["strength"] = 0.2*math.exp(-6.61*hyd.flow_contrast)	#map to aesthetic range 0.0003-0.2

	prog["acceleration"] = hyd.part_acceleration
	prog["iterations"] = hyd.part_lifetime
	prog["drag"] = 1-hyd.part_drag	#multiplicative factor

	groupsX = math.ceil(size[0]/(subdiv * 32))
	groupsY = math.ceil(size[1]/(subdiv * 32))

	time = datetime.now()
	for y in range(subdiv):
		for x in range(subdiv):
			prog["off"] = (x,y)
			prog.run(group_x=groupsX, group_y=groupsY)
	ctx.finish()

	finalAmount = texture.create_texture(amount.size)
	finalAmount.bind_to_image(3, read=True, write=True)
	prog = data.shaders["plug"]
	prog["inMap"].value = 2
	prog["outMap"].value = 3
	prog.run(group_x=size[0], group_y=size[1])

	print((datetime.now() - time).total_seconds())

	imgName = f"HYD_{obj.name}_Flow"
	ret = texture.write_image(imgName, finalAmount)
	amount.release()
	finalAmount.release()
	return ret
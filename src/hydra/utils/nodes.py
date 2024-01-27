import bpy
from Hydra import common

# -------------------------------------------------- Node Utils

def minimize_node(node):
	"""Hides unused inputs and minimizes the specified node.
	
	:param node: Node to minimize."""
	node.hide = True
	for n in node.inputs:
		n.hide = True
	for n in node.outputs:
		n.hide = True

def setup_vector_node(nodes, node: bpy.types.ShaderNode)->bpy.types.ShaderNode:
	"""Creates a Z Normal node and connects it to the specified node.
	
	:param nodes: Node graph.
	:param node: Node to connect to.
	:type node: :class:`bpy.types.ShaderNode`
	:return: Created node.
	:rtype: :class:`bpy.types.ShaderNode`"""
	norm = nodes.nodes.new("ShaderNodeNormal")
	norm.name = "HYD_norm"
	norm.label = "Z Normal"
	nodes.links.new(node.inputs["Normal"], norm.outputs["Normal"])
	minimize_node(norm)
	return norm
	
def setup_image_node(nodes, name:str, imageSrc:str)->tuple[bpy.types.ShaderNode, bpy.types.ShaderNode]:
	"""Creates an Image Texture node and connects it to generated coordinates.
	
	:param nodes: Node graph.
	:param name: Image node title.
	:type name: :class:`str`
	:param imageSrc: Image source name.
	:type imageSrc: :class:`str`
	:return: Created nodes.
	:rtype: :class:`tuple[bpy.types.ShaderNode, bpy.types.ShaderNode]`"""
	img = nodes.nodes.new("ShaderNodeTexImage")
	img.name = name
	img.label = name
	img.image = imageSrc
	img.extension = 'EXTEND'
	img.interpolation = 'Cubic'
	coords = nodes.nodes.new("ShaderNodeTexCoord")
	nodes.links.new(img.inputs["Vector"], coords.outputs["Generated"])
	minimize_node(coords)
	return (img, coords)
	
def stagger_nodes(baseNode:bpy.types.ShaderNode, *args, forwards:bool=False):
	"""Spaces and shifts specified nodes around.
	
	:param baseNode: Rightmost node.
	:type baseNode: :class:`bpy.types.ShaderNode`
	:param args: Node arguments to be shifted.
	:type args: :class:`bpy.types.ShaderNode`
	:param forwards: Shift direction. `True` shifts `baseNode` forward.
	:type forwards: :class:`bool`"""
	x = baseNode.location[0]
	baseY = baseNode.location[1] - baseNode.height
	if forwards:
		for layer in args[::-1]:
			maxwidth = 0
			y = baseY
			for node in layer:
				node.location[0] = x
				maxwidth = max(maxwidth, node.width)
				node.location[1] = y
				y -= node.height + 10
			x += maxwidth + 20
		baseNode.location[0] = x
	else:
		for layer in args:
			maxwidth = 0
			y = baseY
			for node in layer:
				node.location[0] = x - node.width - 20
				maxwidth = max(maxwidth, node.width)
				node.location[1] = y
				y -= node.height + 10
			x -= maxwidth + 20
			
def make_bsdf(nodes)->bpy.types.ShaderNode:
	"""Creates a Principled BSDF node.
	
	:param nodes: Node graph.
	:return: Created node.
	:rtype: :class:`bpy.types.ShaderNode`"""
	ret = nodes.nodes.new("ShaderNodeBsdfPrincipled")
	ret.inputs["Roughness"].default_value = 0.8
	
	if "Specular IOR Level" in ret.inputs:	# Blender 4.0
		ret.inputs["Specular IOR Level"].default_value = 0.2
	elif "Specular":	# Older versions
		ret.inputs["Specular"].default_value = 0.2

	return ret

def get_or_make_output_node(nodes):
	"""Finds or creates an Output node.
	
	:param nodes: Node graph.
	:return: Created node.
	:rtype: :class:`bpy.types.ShaderNode`"""
	out = nodes.get_output_node('ALL')
	if out is None:
		out = nodes.get_output_node('CYCLES')

	if out is None:
		out = nodes.get_output_node('EEVEE')

	if out is None:
		out = nodes.nodes.new("ShaderNodeOutputMaterial")
	
	return out

def get_or_make_displace_group(name, image: bpy.types.Image=None):
	if name in bpy.data.node_groups:
		g = bpy.data.node_groups[name]
		sockets = g.interface.items_tree

		if not any(i for i in g.nodes if i.type == "IMAGE_TEXTURE" and i.name == "HYD_Displacement"):
			n_image = g.nodes.new("GeometryNodeImageTexture")
			n_image.label = "Displacement"
			n_image.name = "HYD_Displacement"
			n_image.extension = "EXTEND"
			n_image.interpolation = "Cubic"
			n_image.inputs[0].default_value = image
			common.data.add_message(f"Existing group {name} was missing HYD_Displacement image node. It has been added, but hasn't been connected.", error=True)
		elif not any(i for i in sockets if i.in_out == "OUTPUT" and i.socket_type == "NodeSocketGeometry") or\
			not any(i for i in sockets if i.in_out == "INPUT" and i.socket_type == "NodeSocketGeometry"):
			common.data.add_message(f"Updated existing group {name}, but it doesn't have Geometry input/output!", error=True)
		else:
			common.data.add_message(f"Updated existing group {name}.")
		return g
	else:
		g = bpy.data.node_groups.new(name, type='GeometryNodeTree')
		common.data.add_message(f"Created new group {name}.")

		g.is_modifier = True
		g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
		i_scale = g.interface.new_socket("Scale", in_out="INPUT", socket_type="NodeSocketFloat")
		i_scale.default_value = 1
		i_scale.min_value = 0
		i_scale.max_value = 2
		i_scale.force_non_field = False
		g.interface.new_socket("Displaced", in_out="OUTPUT", socket_type="NodeSocketGeometry")

		nodes = g.nodes

		n_input = nodes.new("NodeGroupInput")
		n_output = nodes.new("NodeGroupOutput")

		n_bounds = nodes.new("GeometryNodeBoundBox")
		n_bounds.name = "HYD_Bounds"
		n_pos = nodes.new("GeometryNodeInputPosition")
		n_pos.name = "HYD_Position"

		n_subpos = nodes.new("ShaderNodeVectorMath")
		n_subpos.label = "Remove Offset"
		n_subpos.name = "HYD_Get_Offset"
		n_subpos.operation = "SUBTRACT"

		n_subbound = nodes.new("ShaderNodeVectorMath")
		n_subbound.label = "Width and Height"
		n_subpos.name = "HYD_Get_Dimensions"
		n_subbound.operation = "SUBTRACT"

		n_normalize = nodes.new("ShaderNodeVectorMath")
		n_normalize.label = "Normalize"
		n_subpos.name = "HYD_Normalize"
		n_normalize.operation = "DIVIDE"

		n_image = nodes.new("GeometryNodeImageTexture")
		n_image.label = "Displacement"
		n_image.name = "HYD_Displacement"
		n_image.extension = "EXTEND"
		n_image.interpolation = "Cubic"
		n_image.inputs[0].default_value = image

		n_scale = nodes.new("ShaderNodeMath")
		n_scale.label = "Scale"
		n_scale.name = "HYD_Scale"
		n_scale.operation = "MULTIPLY"
		n_scale.inputs[1].default_value = 1

		n_combine = nodes.new("ShaderNodeCombineXYZ")
		n_combine.label = "Z Only"
		n_combine.name = "HYD_Z_Only"
		n_displace = nodes.new("GeometryNodeSetPosition")
		n_displace.label = "Displace"

		links = g.links

		links.new(n_input.outputs["Geometry"], n_bounds.inputs[0])

		links.new(n_pos.outputs[0], n_subpos.inputs[0])
		links.new(n_bounds.outputs["Min"], n_subpos.inputs[1])

		links.new(n_bounds.outputs["Max"], n_subbound.inputs[0])
		links.new(n_bounds.outputs["Min"], n_subbound.inputs[1])

		links.new(n_subpos.outputs[0], n_normalize.inputs[0])
		links.new(n_subbound.outputs[0], n_normalize.inputs[1])

		links.new(n_normalize.outputs[0], n_image.inputs["Vector"])

		links.new(n_image.outputs["Color"], n_scale.inputs[0])
		links.new(n_input.outputs["Scale"], n_scale.inputs[1])

		links.new(n_scale.outputs[0], n_combine.inputs["Z"])

		links.new(n_input.outputs["Geometry"], n_displace.inputs["Geometry"])
		links.new(n_combine.outputs[0], n_displace.inputs["Offset"])

		links.new(n_displace.outputs["Geometry"], n_output.inputs["Displaced"])

		stagger_nodes(n_output, [n_displace], [n_combine], [n_scale], [n_image], [n_normalize], [n_subpos, n_subbound], [n_pos, n_bounds], [n_input], forwards=False)

		return g
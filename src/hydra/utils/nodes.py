import bpy
from Hydra import common
import math

# -------------------------------------------------- Constants

COLOR_DISPLACE = (0.1,0.393,0.324)
COLOR_VECTOR = (0.172,0.172,0.376)
COLOR_INPUT = (0.406, 0.152, 0.229)

# -------------------------------------------------- Node Utils

def minimize_node(node, collapse_node:bool=True)->None:
	"""Hides unused inputs and minimizes the specified node.
	
	:param node: Node to minimize.
	:param collapse_node: Whether to collapse the node.
	:type collapse_node: :class:`bool`"""
	if collapse_node:
		node.hide = True
	
	for n in node.inputs:
		n.hide = True
	# Only hide outputs if at least one is connected
	if any((x.is_linked for x in node.outputs)):
		for n in node.outputs:
			n.hide = True

def stagger_nodes(baseNode:bpy.types.ShaderNode, *args, forwards:bool=False)->None:
	"""Spaces and shifts specified nodes around.
	
	:param baseNode: Rightmost node.
	:type baseNode: :class:`bpy.types.ShaderNode`
	:param args: Node arguments to be shifted.
	:type args: :class:`bpy.types.ShaderNode`
	:param forwards: Shift direction. `True` shifts `baseNode` forward.
	:type forwards: :class:`bool`"""
	baseY = baseNode.location[1] - baseNode.height
	if forwards:
		x = baseNode.location[0]
		for layer in args[::-1]:
			maxwidth = 0
			y = baseY
			for node in layer:
				node.location[0] = x
				maxwidth = max(maxwidth, node.width)
				node.location[1] = y
				y -= node.height + 40
			x += maxwidth + 20
		baseNode.location[0] = x + 20
	else:
		x = baseNode.location[0] - 20
		for layer in args:
			maxwidth = 0
			y = baseY
			for node in layer:
				node.location[0] = x - node.width - 20
				maxwidth = max(maxwidth, node.width)
				node.location[1] = y
				y -= node.height + 40
			x -= maxwidth + 20

class Node:
	def __init__(self, name, type, label=None, operation=None, link=None, minimize=False, **kwargs):
		self.name = name
		self.type = type
		self.link = link
		self.label = label
		self.operation = operation
		self.other = kwargs
		self.minimize = minimize
		self.width = 0
		self.height = 0

	def __repr__(self):
		return f"{self.name}: {self.x}/{self.y} [{self.parent}]"

class Frame:
	def __init__(self, label=None, color:tuple[int,int,int]=None, nodes=None):
		self.label = label
		self.color = color
		self.nodes = nodes
		self.width = 0
		self.height = 0

	def __repr__(self):
		return f"{self.title}"

def extract(node, node_dict, nodes, frame):
	if node is None:
		return
	tp = type(node)
	if tp is Node:
		n = nodes.new(node.type)
		n.name = node.name
		n.parent = frame
		if node.label is not None:
			n.label = node.label
		if node.operation:
			n.operation = node.operation
		for k,v in node.other.items():
			if hasattr(n, k):
				setattr(n, k, v)

		node_dict[node.name] = (n, node)
	elif tp is tuple or tp is list:
		for i in node:
			extract(i, node_dict, nodes, frame)
	elif tp is Frame:
		f = nodes.new("NodeFrame")
		f.label = node.label
		f.parent = frame
		if node.color is not None:
			f.color = node.color
			f.use_custom_color = True

		extract(node.nodes, node_dict, nodes, f)
	else:
		raise ValueError(f"Invalid node type {type(node)}")

def stagger(node, pos, node_dict:dict[str, Node]):
	if node is None:
		return pos
	tp = type(node)
	if tp is Node:
		n = node_dict[node.name][0]
		n.location[0] = pos[0]
		n.location[1] = pos[1]
		return (pos[0] + node.width + 20, pos[1] - node.height - 10)
	elif tp is tuple:
		npos = pos
		width = 0
		height = 0
		for i in node:
			next_pos = stagger(i, npos, node_dict)
			width = max(width, next_pos[0])
			height = min(height, next_pos[1])
			npos = (npos[0], next_pos[1])
		return (width, height)
	elif tp is list:
		npos = pos
		width = 0
		height = 0
		for i in node:
			next_pos = stagger(i, npos, node_dict)
			width = max(width, next_pos[0])
			height = min(height, next_pos[1])
			npos = (next_pos[0], npos[1])
		return (width, height)
	elif tp is Frame:
		ret = stagger(node.nodes, (pos[0] + 20, pos[1] - 40), node_dict)
		return (ret[0] + 40, ret[1] - 40)
	else:
		raise ValueError(f"Invalid node type {type(node)}")

def link_nodes(links, a, b, a_out, b_in):
	if len(a.outputs) == 0 or len(b.inputs) == 0:
		return
	if a_out is None:
		outs = [o for o in a.outputs if o.enabled]
		a_out = outs[0].name
	if b_in is None:
		ins = [i for i in b.inputs if i.enabled]
		b_in = ins[0].name
	links.new(a.outputs[a_out], b.inputs[b_in])

def set_value(node, at, value):
	if at is None:
		at = 0
	try:
		node.inputs[at].default_value = value
	except Exception as e:
		print(f"Failed to set value for: {node.name}[{node.type}] due to {e}")

HEIGHT_DICT = {
	"ShaderNodeVectorMath": 1,
	"ShaderNodeMath": 2,
	"GeometryNodeImageTexture": 2,
	"ShaderNodeMapRange": 3,
}

def create_tree(nodes, links, node_definition):
	node_dict = {}
	extract(node_definition, node_dict, nodes, None)

	last_item = None
	for v, node_def in node_dict.values():
		link = node_def.link
		if link is None:
			if last_item is None:
				last_item = v
				continue
			else:
				link = last_item
		
		if type(link) is list:
			values = enumerate(link)
		elif type(link) is dict:
			values = link.items()
		else:
			values = [(None, link)]

		for i,val in values:
			tp = type(val)
			if tp is tuple:
				ntp = type(val[0])
				if ntp is str:	# output selection
					link_nodes(links, node_dict[val[0]][0], v, val[1], i)
				elif isinstance(ntp, bpy.types.Node):
					link_nodes(links, val[0], v, val[1], i)
				else: #direct input
					set_value(v, i, val)
			elif tp is str: # from node_dict
				link_nodes(links, node_dict[val][0], v, None, i)
			elif isinstance(val, bpy.types.Node):	# object
				link_nodes(links, val, v, None, i)
			else: # value
				set_value(v, i, val)
		
		last_item = v

	# Only minimize after all links are created
	for v, node_def in node_dict.values():
		if node_def.minimize:
			minimize_node(v, collapse_node=False)

		if v.hide:
			height = 50
		else:
			height = 25 + (HEIGHT_DICT[node_def.type] if node_def.type in HEIGHT_DICT else 0) * 20
			for i in v.inputs:
				if not i.hide and i.enabled:
					if i.is_linked or i.hide_value:
						height += 20
					elif hasattr(i, "default_value") and hasattr(i.default_value, "__len__"):
						height += 20 + 20 * len(i.default_value)
					else:
						height += 20
			height += 15
			height += 20 * len([i for i in v.outputs if not i.hide and i.enabled])
		
		node_def.height = height
		node_def.width = v.width

	stagger(node_definition, (0,0), node_dict)

def space_nodes(*args, forwards:bool=False)->None:
	"""Spaces specified nodes apart.
	
	:param args: Node arguments to be spaced.
	:type args: :class:`bpy.types.ShaderNode`
	:param forwards: Shift direction. `True` shifts towards the root of the node tree.
	:type forwards: :class:`bool`"""
	offset = 50
	for n in args[::-1 if forwards else 1]:
		if forwards:
			n.location.x += offset
		else:
			n.location.x -= offset
		offset += 50 # spacing stacks

def frame_nodes(nodes, *args, label:str|None = None, color:tuple[float,float,float]|None=None)->bpy.types.ShaderNode:
	"""Creates a frame node and parents specified nodes to it.
	
	:param nodes: Node graph.
	:param args: Nodes to parent.
	:type args: :class:`bpy.types.ShaderNode`
	:param label: Frame label.
	:type label: :class:`str`
	:param color: Frame color.
	:type color: :class:`tuple[float,float,float]`
	:return: Created frame node.
	:rtype: :class:`bpy.types.ShaderNode`"""
	frame = nodes.new("NodeFrame")
	frame.label = label
	if color is not None:
		frame.color = color
		frame.use_custom_color = True
	
	for n in args:
		n.parent = frame
	return frame

# -------------------------------------------------- Node Setup

def setup_vector_node(nodes, node: bpy.types.ShaderNode, planet: bool = False)->bpy.types.ShaderNode:
	"""Creates a Z Normal node and connects it to the specified node.
	
	:param nodes: Node graph.
	:param node: Node to connect to.
	:type node: :class:`bpy.types.ShaderNode`
	:return: Created node.
	:rtype: :class:`bpy.types.ShaderNode`"""
	if planet:
		norm = nodes.nodes.new("ShaderNodeTexCoord")
		norm.name = "HYD_norm"
		norm.label = "Sphere Normal"
		nodes.links.new(node.inputs["Normal"], norm.outputs["Object"])
		minimize_node(norm, collapse_node=False)
	else:
		norm = nodes.nodes.new("ShaderNodeNormal")
		norm.name = "HYD_norm"
		norm.label = "Z Normal"
		nodes.links.new(node.inputs["Normal"], norm.outputs["Normal"])
		minimize_node(norm)
	return norm
	
def setup_image_node(tree:bpy.types.NodeTree, name:str, imageSrc:str, planet: bool = False)->\
		tuple[bpy.types.ShaderNode, bpy.types.ShaderNode]|tuple[bpy.types.ShaderNode, bpy.types.ShaderNode, bpy.types.ShaderNode]:
	"""Creates an Image Texture node and connects it to generated coordinates.
	
	:param nodes: Node graph.
	:param name: Image node title.
	:type name: :class:`str`
	:param imageSrc: Image source name.
	:type imageSrc: :class:`str`
	:return: Created nodes.
	:rtype: :class:`tuple[bpy.types.ShaderNode, bpy.types.ShaderNode]`"""
	img = tree.nodes.new("ShaderNodeTexImage")
	img.name = name
	img.label = name
	img.image = imageSrc
	img.extension = 'EXTEND'
	img.interpolation = 'Cubic'
	img.projection = "SPHERE" if planet else "FLAT"
	coords = tree.nodes.new("ShaderNodeTexCoord")

	if planet:
		sub = tree.nodes.new("ShaderNodeVectorMath")
		sub.operation = "ADD"
		sub.inputs[1].default_value = (0.5, 0.5, 0.5)
		tree.links.new(sub.inputs[0], coords.outputs["Object"])
		tree.links.new(img.inputs["Vector"], sub.outputs[0])
		minimize_node(coords, collapse_node=False)
		return (img, sub, coords)
	else:
		tree.links.new(img.inputs["Vector"], coords.outputs["Generated"])
		minimize_node(coords, collapse_node=False)
		return (img, coords)

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

def get_or_make_output_node(nodes)->bpy.types.ShaderNode:
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

def make_or_update_displace_group(name, image: bpy.types.Image=None, tiling: bool = False)->bpy.types.NodeGroup:
	"""Finds or creates a displacement node group.

	:param name: Node group name.
	:type name: :class:`str`
	:param image: Image to use for displacement.
	:type image: :class:`bpy.types.Image`
	:return: Displacement node group.
	:rtype: :class:`bpy.types.NodeGroup`"""
	if name in bpy.data.node_groups:
		g = bpy.data.node_groups[name]
		sockets = g.interface.items_tree

		if g.users == 0:
			bpy.data.node_groups.remove(g)
		else:
			if not any(i for i in g.nodes if i.type == "IMAGE_TEXTURE" and i.name == "HYD_Displacement"):
				n_image = g.nodes.new("GeometryNodeImageTexture")
				n_image.label = "Displacement"
				n_image.name = "HYD_Displacement"
				n_image.extension = "REPEAT" if tiling else "EXTEND"
				n_image.interpolation = "Cubic"
				n_image.inputs[0].default_value = image
				common.data.add_message(f"Existing group {name} was missing HYD_Displacement image node. It has been added, but hasn't been connected.", error=True)
			elif not any(i for i in sockets if i.in_out == "OUTPUT" and i.socket_type == "NodeSocketGeometry") or\
				not any(i for i in sockets if i.in_out == "INPUT" and i.socket_type == "NodeSocketGeometry"):
				common.data.add_message(f"Updated existing group {name}, but it doesn't have Geometry input/output!", error=True)
			else:
				# Update image
				n_image = next(i for i in g.nodes if i.type == "IMAGE_TEXTURE" and i.name == "HYD_Displacement")
				n_image.inputs[0].default_value = image
				n_image.extension = "REPEAT" if tiling else "EXTEND"
				common.data.add_message(f"Updated existing group {name}.")
			return g

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
	links = g.links

	create_tree(nodes, links, [
		Node("Group Input", "NodeGroupInput"),
		Frame("Texture Coordinates", color=COLOR_VECTOR, nodes=[
			(
				[
					Node("HYD_Position", "GeometryNodeInputPosition"),
					Node("HYD_Relative_Coords", "ShaderNodeVectorMath", label="Remove Offset", operation="SUBTRACT", link=[
						"HYD_Position", ("HYD_Bounds", 1)
					]),
				],
				[
					Node("HYD_Bounds", "GeometryNodeBoundBox", link="Group Input"),
					Node("HYD_Sizes", "ShaderNodeVectorMath", label="Width and Height", operation="SUBTRACT", link=[
						("HYD_Bounds", 2), ("HYD_Bounds", 1)
					]),
				],
			),
			Node("HYD_Texture_Coords", "ShaderNodeVectorMath", label="Normalize", operation="DIVIDE", link=[
				"HYD_Relative_Coords", "HYD_Sizes"
			]),
		]),
		Frame("Displacement", color=COLOR_DISPLACE, nodes=[
			Node("HYD_Displacement", "GeometryNodeImageTexture", label="Displacement", link={
				0: image,
				"Vector": "HYD_Texture_Coords"
			}, extension="REPEAT" if tiling else "EXTEND", interpolation="Cubic"),
			Node("HYD_Scale", "ShaderNodeMath", label="Scale", operation="MULTIPLY", link=["HYD_Displacement", ("Group Input", "Scale")]),
			Node("HYD_Z_Only", "ShaderNodeCombineXYZ", label="Z Only", link={2: "HYD_Scale"}),
			Node("HYD_Displace", "GeometryNodeSetPosition", label="Displace", link={0: "Group Input", 3: "HYD_Z_Only"}),
		]),
		Node("Group Output", "NodeGroupOutput", link="HYD_Displace")
	])

	return g

def make_or_update_planet_group(name, image: bpy.types.Image=None, sub_cube: bool = False)->bpy.types.NodeGroup:
	if name in bpy.data.node_groups:
		g = bpy.data.node_groups[name]
		sockets = g.interface.items_tree

		if g.users == 0:
			bpy.data.node_groups.remove(g)
		else:
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
				# Update image
				n_image = next(i for i in g.nodes if i.type == "IMAGE_TEXTURE" and i.name == "HYD_Displacement")
				n_image.inputs[0].default_value = image
				common.data.add_message(f"Updated existing group {name}.")
			return g

	g = bpy.data.node_groups.new(name, type='GeometryNodeTree')
	g.is_modifier = True
	g.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
	i_scale = g.interface.new_socket("Scale", in_out="INPUT", socket_type="NodeSocketFloat")
	i_scale.default_value = 1
	i_scale.min_value = 0
	i_scale.max_value = 2
	i_scale.force_non_field = False
	g.interface.new_socket("Displaced", in_out="OUTPUT", socket_type="NodeSocketGeometry")

	nodes = g.nodes
	links = g.links

	create_tree(nodes, links, [
		Node("Group Input", "NodeGroupInput"),
		(
			Frame("Texture Coordinates", color=COLOR_VECTOR, nodes=[
				Node("HYD_Position", "GeometryNodeInputPosition"),
				Node("HYD_Get_Normalized", "ShaderNodeVectorMath", label="Normalize", operation="NORMALIZE"),
				Node("HYD_Rotate", "FunctionNodeRotateVector", label="Rotate to +Y", link=[
					"HYD_Get_Normalized",
					# slightly misaligned to avoid floating point errors
					(0, 0, -math.pi / 2 + 1e-5)
				]),
				Node("HYD_Get_Components", "ShaderNodeSeparateXYZ", label="Spherical Components"),
				(
					Node("HYD_Get_X", "ShaderNodeMath", operation="ARCTAN2", label="X Coordinate",
						link=[("HYD_Get_Components", 1), ("HYD_Get_Components", 0)]),
					Node("HYD_Get_Y", "ShaderNodeMath", operation="ARCSINE", label="Y Coordinate",
						link=("HYD_Get_Components", 2)),
				),
				Node("HYD_Equirect", "ShaderNodeCombineXYZ", label="Equirectangular XY", link=["HYD_Get_X", "HYD_Get_Y"]),
				Node("HYD_Texture_Coords", "ShaderNodeMapRange", label="UV Coordinates", link={
						6: "HYD_Equirect",
						7: (-math.pi, -math.pi/2, 0),
						8: (math.pi, math.pi / 2, 1),
					}, data_type="FLOAT_VECTOR", minimize=True),
			]),
			# ---------------------- Sub cube
			Frame("Cube Subtraction", color=COLOR_INPUT, nodes=[
				Node("HYD_Absolute", "ShaderNodeVectorMath", operation="ABSOLUTE", link="HYD_Get_Normalized"),
				Node("HYD_Abs_Components", "ShaderNodeSeparateXYZ", label="Absolute Components"),
				Node("HYD_Max_XY", "ShaderNodeMath", operation="MAXIMUM", label="Max X/Y", link=[
					("HYD_Abs_Components", 0), ("HYD_Abs_Components", 1)
				]),
				Node("HYD_Max_XYZ", "ShaderNodeMath", operation="MAXIMUM", label="Max X/Y/Z", link=[
					"HYD_Max_XY", ("HYD_Abs_Components", 2)
				]),
				Node("HYD_Divide", "ShaderNodeMath", operation="DIVIDE", label="Distance to Cube", link={0: 1.0, 1: "HYD_Max_XYZ"}),
			]) if sub_cube else None
			# ----------------------
		),
		Frame("Displacement", color=COLOR_DISPLACE, nodes=[
			Node("HYD_Displacement", "GeometryNodeImageTexture", label="Displacement", link={
				0: image,
				"Vector": "HYD_Texture_Coords"
			}, extension="EXTEND"), # REPEAT creates seams at the poles
			Node("HYD_Scale", "ShaderNodeMath", label="Scale", operation="MULTIPLY", link=["HYD_Displacement", ("Group Input", "Scale")]),
			Node("HYD_Subtract_Cube", "ShaderNodeMath", label="Subtract Cube", operation="SUBTRACT", link=["HYD_Scale", "HYD_Divide"])
				if sub_cube else None,
			Node("HYD_Offset", "ShaderNodeVectorMath", label="Offset Vector", operation="SCALE", link={
				0: "HYD_Get_Normalized", 3: "HYD_Subtract_Cube" if sub_cube else "HYD_Scale"
			}),
			Node("HYD_Displace", "GeometryNodeSetPosition", label="Displace", link={0: "Group Input", 3: "HYD_Offset"}),
		]),
		Node("Group Output", "NodeGroupOutput", link="HYD_Displace")
	])

	return g

def make_snow_nodes(tree: bpy.types.ShaderNodeTree, image: bpy.types.Image):
	nodes = tree.nodes

	ramp = nodes.new("ShaderNodeValToRGB")
	ramp.name = "HYD_Snow_Ramp"
	ramp.label = "Snow Ramp"

	ramp.color_ramp.elements[0].color = (0.5,0.5,0.5,1)
	ramp.color_ramp.elements[1].position = 0.5

	img, coords = setup_image_node(nodes, "HYD_Snow_Texture", image)

	tree.links.new(img.outputs["Color"], ramp.inputs["Fac"])
	stagger_nodes(ramp, [img], [coords], forwards=False)

def add_planet_shader_uv_nodes(nodes, links):
	create_tree(nodes, links, [
		Frame("Sphere Coordinates", color=COLOR_VECTOR, nodes=[
			Node("HYD_Obj_Coords", "ShaderNodeTexCoord", minimize=True),
			Node("HYD_Relative_Coords", "ShaderNodeVectorMath", operation="ADD", link=[
				("HYD_Obj_Coords", "Object"), (0.5,0.5,0.5)
			]),
		])
	])

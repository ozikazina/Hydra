"""Module responsible for applying heightmaps, previews and modifiers."""

import bpy, bpy.types, bpy_extras
import numpy as np
from Hydra import common
from Hydra.utils import texture
import moderngl as mgl

def minimizeNode(node):
	"""Hides unused inputs and minimizes the specified node.
	
	:param node: Node to minimize."""
	node.hide = True
	for n in node.inputs:
		n.hide = True
	for n in node.outputs:
		n.hide = True

def setupVectorNode(nodes, node: bpy.types.ShaderNode)->bpy.types.ShaderNode:
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
	minimizeNode(norm)
	return norm
	
def setupImageNode(nodes, name:str, imageSrc:str)->tuple[bpy.types.ShaderNode, bpy.types.ShaderNode]:
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
	minimizeNode(coords)
	return (img, coords)
	
def staggerNodes(baseNode:bpy.types.ShaderNode, *args, forwards:bool=False):
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
				print(node.dimensions)
				maxwidth = max(maxwidth, node.width)
				node.location[1] = y
				y -= node.height + 10
			x -= maxwidth + 20
			
def makeBSDF(nodes)->bpy.types.ShaderNode:
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

def getOrMakeOutputNode(nodes):
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

# --------------------------------------------------

H_NAME_BUMP = "Hydra Bump"
"""Bump map node name."""

def addBump(obj: bpy.types.Object, src: mgl.Texture):
	"""Adds a Bump map for the given texture in the specified object's material.
	Creates a material if needed, otherwise selects the first material slot.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	img = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)

	mats = obj.material_slots
	if len(mats) == 0:
		name = "HYD_" + obj.name
		if name in bpy.data.materials:
			mat = bpy.data.materials[name]
		else:
			mat = bpy.data.materials.new(name=name)
		obj.data.materials.append(mat)
	else:
		mat = mats[0].material
	
	if not mat.use_nodes:
		mat.use_nodes = True
	nodes = mat.node_tree
	
	if H_NAME_BUMP in nodes.nodes: #already updated
		nodes.nodes[H_NAME_BUMP].image = img
		return
	
	out = getOrMakeOutputNode(nodes)
		
	if not out.inputs["Surface"].is_linked:
		shader = makeBSDF(nodes)
		nodes.links.new(out.inputs["Surface"], shader.outputs["BSDF"])
	else:
		shader = out.inputs["Surface"].links[0].from_node
	if "Normal" not in shader.inputs:
		data.error += ["Material doesn't have normals input.\n"]
		return
		
	if shader.inputs["Normal"].is_linked:
		bump = shader.inputs["Normal"].links[0].from_node
		if bump.bl_idname != "ShaderNodeBump":
			data.error += ["Material already implements a different bump map.\n"]
			return
	else:
		bump = nodes.nodes.new("ShaderNodeBump")
		nodes.links.new(shader.inputs["Normal"], bump.outputs["Normal"])
	
	if bump.inputs["Height"].is_linked:
		data.error += ["Material already implements a different bump map.\n"]
		return
	
	bump.inputs["Distance"].default_value = 0.2
	
	imgNode,coords = setupImageNode(nodes, "Bumpmap", img)
	nodes.links.new(bump.inputs["Height"], imgNode.outputs["Color"])
	minimizeNode(imgNode)
	staggerNodes(shader, [bump], [imgNode], [coords])

H_NAME_DISP = "Hydra Displacement"
"""Displacement map node name."""

def addDisplacement(obj: bpy.types.Object, src: mgl.Texture):
	"""Adds a Displacement map for the given texture in the specified object's material.
	Creates a material if needed, otherwise selects the first material slot.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	img = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)

	mats = obj.material_slots
	if len(mats) == 0:
		name = "HYD_" + obj.name
		if name in bpy.data.materials:
			mat = bpy.data.materials[name]
		else:
			mat = bpy.data.materials.new(name=name)
			mat.cycles.displacement_method = "DISPLACEMENT"
		obj.data.materials.append(mat)
	else:
		mat = mats[0].material
	
	if not mat.use_nodes:
		mat.use_nodes = True
	nodes = mat.node_tree
	
	if H_NAME_DISP in nodes.nodes:	#Image node already exists
		nodes.nodes[H_NAME_DISP].image = img
		return
	
	out = getOrMakeOutputNode(nodes)

	if not out.inputs["Displacement"].is_linked:
		disp = nodes.nodes.new("ShaderNodeDisplacement")
		disp.inputs["Midlevel"].default_value = 0
		disp.inputs["Scale"].default_value = 1
		nodes.links.new(out.inputs["Displacement"], disp.outputs["Displacement"])
		norm = setupVectorNode(nodes, disp)
	else:
		disp = out.inputs["Displacement"].links[0].from_node
		if disp.bl_idname != "ShaderNodeDisplacement":
			data.error += ["Material already implements a different displacement map."]
			return
	
	if disp.inputs["Height"].is_linked:
		data.error += ["Material already implements a different displacement map."]
		return
	
	imgNode, coords = setupImageNode(nodes, H_NAME_DISP, img)
	nodes.links.new(disp.inputs["Height"], imgNode.outputs["Color"])
	minimizeNode(imgNode)
	
	staggerNodes(out, [disp], [imgNode, norm], [coords], forwards=True)

def addModifier(obj: bpy.types.Object, src: mgl.Texture):
	"""Adds a Displace modifier to the specified object.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	img = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)

	if len(obj.modifiers) == 0:
		mod = obj.modifiers.new("HYD_" + obj.name, "DISPLACE")
	elif obj.modifiers[-1].name.startswith("HYD_"):
		if obj.modifiers[-1].type == "DISPLACE":
			mod = obj.modifiers[-1]
		else:
			obj.modifiers.remove(obj.modifiers[-1])
			mod = obj.modifiers.new("HYD_" + obj.name, "DISPLACE")
	else:
		mod = obj.modifiers[-1]
	
	if mod.name in bpy.data.textures:
		txt = bpy.data.textures[mod.name]
		data.info += ["Updated existing displacement."]
	else:
		txt = bpy.data.textures.new(mod.name, "IMAGE")
		data.info += ["Created new displacement."]

	txt.image = img
	mod.texture = txt
	mod.direction = 'Z'
	mod.texture_coords = "OBJECT"
	mod.strength = 1
	mod.mid_level = 0
	
	coll = obj.users_collection[0]	#always exists
	emptyName = "HYD_" + obj.name + "_Guide"
	if emptyName in bpy.data.objects:
		empty = bpy.data.objects[emptyName]
	else:
		empty = bpy.data.objects.new(emptyName, None)
		coll.objects.link(empty)
	empty.parent = obj
	
	ar = np.array(obj.bound_box)
	# bounding box center
	cx = (ar[4][0] + ar[0][0]) * 0.5
	cy = (ar[2][1] + ar[0][1]) * 0.5
	cz = (ar[1][2] + ar[0][2]) * 0.5
	# bounding box size
	sx = 0.5*(ar[4][0] - ar[0][0])
	sy = 0.5*(ar[2][1] - ar[0][1])
	# Z scale is handled by texture

	empty.location = (cx,cy,cz)
	empty.scale = (sx,sy,1)
	mod.texture_coords_object = empty

# -------------------------------------------------- Previews

P_MOD_NAME = "HYD_Preview_Modifier"
"""Preview modifier name."""
P_IMG_NAME = "HYD_Preview_Image"
"""Preview temporary image name."""
P_VIEW_NAME = "HYD_Image_Preview"	#different from object preview heightmap
"""Image preview name."""
P_GEO_NAME = "HYD_Preview"
"""Geometry Nodes group name."""

def showGenModifier(obj: bpy.types.Object, visible: bool):
	"""Internal. Shows or hides the first modifier created by Hydra belonging to the specified object.
	
	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param visible: Modifier visibility.
	:type visible: :class:`bool`"""
	mod = next((x for x in obj.modifiers if x.name.startswith("HYD_")), None)
	if mod and mod.name != P_MOD_NAME:
		mod.show_viewport = visible

def addImagePreview(src: mgl.Texture)->bpy.types.Image:
	"""Writes the specified texture as a temporary image.
	
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`
	:return: Created image.
	:rtype: :class:`bpy.types.Image`"""
	return texture.writeImage(P_VIEW_NAME, src)

def removeImagePreview():
	"""Removes the temporary preview Image."""
	if P_VIEW_NAME in bpy.data.images:
		img = bpy.data.images[P_VIEW_NAME]
		bpy.data.images.remove(img)

def addPreview(obj: bpy.types.Object, src: mgl.Texture):
	"""Previews the specified texture as a geometry node on the specified object.
	
	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	if data.lastPreview and data.lastPreview in bpy.data.objects:
		last = bpy.data.objects[data.lastPreview]
		if last != obj and P_MOD_NAME in last.modifiers:
			last.modifiers.remove(last.modifiers[P_MOD_NAME])

	if data.lastPreview != obj.name and P_GEO_NAME in bpy.data.node_groups:
		g = bpy.data.node_groups[P_GEO_NAME]
		bpy.data.node_groups.remove(g)

	showGenModifier(obj, False)

	if P_MOD_NAME in obj.modifiers:
		mod = obj.modifiers[P_MOD_NAME]
		common.data.info += ["Updated existing preview."]
	else:
		mod = obj.modifiers.new(P_MOD_NAME, "NODES")
		common.data.info += ["Created preview modifier."]
	
	img = texture.writeImage(P_IMG_NAME, src)
	mod.node_group = getOrMakeDisplaceGroup(P_GEO_NAME, img)

	common.data.lastPreview = obj.name

def removePreview():
	"""Removes the preview modifier from the last previewed object."""
	data = common.data
	if str(data.lastPreview) in bpy.data.objects:
		last = bpy.data.objects[data.lastPreview]
		if P_MOD_NAME in last.modifiers:
			last.modifiers.remove(last.modifiers[P_MOD_NAME])
		showGenModifier(last, True)
	elif data.lastPreview: #invalid data
		previewed = [i for i in bpy.data.objects if P_MOD_NAME in i.modifiers]
		for i in previewed:
			i.modifiers.remove(i.modifiers[P_MOD_NAME])
			showGenModifier(i, True)

	if P_MOD_NAME in bpy.data.textures:
		txt = bpy.data.textures[P_MOD_NAME]
		bpy.data.textures.remove(txt)
	
	if P_IMG_NAME in bpy.data.images:
		img = bpy.data.images[P_IMG_NAME]
		bpy.data.images.remove(img)

	if P_GEO_NAME in bpy.data.node_groups:
		g = bpy.data.node_groups[P_GEO_NAME]
		bpy.data.node_groups.remove(g)

	data.lastPreview = ""


P_LAND_TEMP_NAME = "HYD_TEMP_DISPLACE"

def configureLandscape(obj: bpy.types.Object, src: mgl.Texture):
	"""Shapes the specified grid object using the input heightmap texture.
	
	:param obj: Object to shape.
	:type obj: :class:`bpy.types.Object`
	:param src: Heightmap texture.
	:type src: :class:`moderngl.Texture`"""
	img = texture.writeImage(P_LAND_TEMP_NAME, src)
	mod = obj.modifiers.new(P_LAND_TEMP_NAME, "NODES")

	
	mod.node_group = getOrMakeDisplaceGroup(P_LAND_TEMP_NAME)
	mod["Socket_1"] = img

	bpy.ops.object.mode_set(mode="OBJECT")	# modifiers can't be applied in EDIT mode
	bpy.ops.object.modifier_apply(modifier=P_LAND_TEMP_NAME)
	
	bpy.data.images.remove(img)
	bpy.data.node_groups.remove(bpy.data.node_groups[P_LAND_TEMP_NAME])

# -------------------------------------------------- Geometry Nodes

def getOrMakeDisplaceGroup(name, image: bpy.types.Image=None, insert: bool=False):
	if name in bpy.data.node_groups:
		g = bpy.data.node_groups[name]
		sockets = g.interface.items_tree
		if any(i for i in sockets if i.in_out == "OUTPUT" and i.socket_type == "NodeSocketGeometry") and\
			any(i for i in sockets if i.in_out == "INPUT" and i.socket_type == "NodeSocketGeometry"):
			common.data.addMessage("Using existing nodes.")
		else:
			common.data.addMessage("Can't apply: Existing node group is invalid.", error=True)
		return g
	else:
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

		n_input = nodes.new("NodeGroupInput")
		n_output = nodes.new("NodeGroupOutput")

		n_bounds = nodes.new("GeometryNodeBoundBox")
		n_pos = nodes.new("GeometryNodeInputPosition")

		n_subpos = nodes.new("ShaderNodeVectorMath")
		n_subpos.label = "Remove Offset"
		n_subpos.operation = "SUBTRACT"
		n_subbound = nodes.new("ShaderNodeVectorMath")
		n_subbound.label = "Width and Height"
		n_subbound.operation = "SUBTRACT"
		n_normalize = nodes.new("ShaderNodeVectorMath")
		n_normalize.label = "Normalize"
		n_normalize.operation = "DIVIDE"

		n_image = nodes.new("GeometryNodeImageTexture")
		n_image.label = "Displacement"
		n_image.extension = "EXTEND"
		n_image.interpolation = "Cubic"
		n_image.inputs[0].default_value = image

		n_scale = nodes.new("ShaderNodeMath")
		n_scale.label = "Scale"
		n_scale.operation = "MULTIPLY"
		n_scale.inputs[1].default_value = 1

		n_combine = nodes.new("ShaderNodeCombineXYZ")
		n_combine.label = "Z Only"
		n_displace = nodes.new("GeometryNodeSetPosition")
		n_displace.label = "Displace"

		n_reroute = nodes.new("NodeReroute")
		

		links = g.links

		links.new(n_input.outputs["Geometry"], n_reroute.inputs[0])

		links.new(n_input.outputs["Geometry"], n_bounds.inputs[0])

		links.new(n_pos.outputs[0], n_subpos.inputs[0])
		links.new(n_bounds.outputs["Min"], n_subpos.inputs[1])

		links.new(n_bounds.outputs["Max"], n_subbound.inputs[0])
		links.new(n_bounds.outputs["Min"], n_subbound.inputs[1])

		links.new(n_subpos.outputs[0], n_normalize.inputs[0])
		links.new(n_subbound.outputs[0], n_normalize.inputs[1])

		# links.new(n_input.outputs["Displacement"], n_image.inputs["Image"])
		links.new(n_normalize.outputs[0], n_image.inputs["Vector"])

		links.new(n_image.outputs["Color"], n_scale.inputs[0])
		links.new(n_input.outputs["Scale"], n_scale.inputs[1])

		links.new(n_scale.outputs[0], n_combine.inputs["Z"])

		links.new(n_input.outputs["Geometry"], n_displace.inputs["Geometry"])
		links.new(n_combine.outputs[0], n_displace.inputs["Offset"])

		links.new(n_displace.outputs["Geometry"], n_output.inputs["Displaced"])

		staggerNodes(n_output, [n_displace], [n_combine], [n_scale], [n_image], [n_normalize], [n_subpos, n_subbound], [n_pos, n_bounds], [n_input], forwards=False)

		return g

def addGeometryNode(obj: bpy.types.Object, src: mgl.Texture):
	"""Adds a Geometry Nodes modifier to the specified object.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	img = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)

	if len(obj.modifiers) == 0:
		mod = obj.modifiers.new("HYD_" + obj.name, "NODES")
	elif obj.modifiers[-1].name.startswith("HYD_"):
		if obj.modifiers[-1].type == "NODES":
			mod = obj.modifiers[-1]
		else:
			obj.modifiers.remove(obj.modifiers[-1])
			mod = obj.modifiers.new("HYD_" + obj.name, "NODES")
	else:
		mod = obj.modifiers[-1]
	
	mod.node_group = getOrMakeDisplaceGroup(f"HYD_{obj.name}", img)

def addIntoGeometryNodes(obj: bpy.types.Object, src: mgl.Texture):
	"""Adds the texture into an existing Geometry Nodes modifier.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	img = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)

	mod = None
	for m in obj.modifiers:
		if m.type == "NODES":
			mod = m

	if mod is None or not mod.node_group:
		data.error += ["No Geometry Nodes found."]
		return
	
	links = mod.node_group.links
	nodes = mod.node_group.nodes
	outputs = [node for node in nodes if node.type == "GROUP_OUTPUT"]
	outputs.sort(key=lambda x: x.name)
	if len(outputs) == 0:
		output = nodes.new("NodeGroupOutput")
	else:
		output = outputs[0]

	displace_group = getOrMakeDisplaceGroup("HYD_Displace")

	connected = None
	if output.inputs[0].is_linked:
		connected = output.inputs[0].links[0].from_node

		if connected.type == "GROUP" and connected.node_tree == displace_group:
			connected.inputs[1].default_value = img
			connected.inputs[2].default_value = 1
			data.info += ["Updated existing displacement."]
			return
	
	g = nodes.new("GeometryNodeGroup")
	g.node_tree = displace_group
	g.inputs[1].default_value = img
	g.inputs[2].default_value = 1

	links.new(g.outputs[0], output.inputs[0])

	if connected:
		links.new(connected.outputs[0], g.inputs[0])

	staggerNodes(output, [g], forwards=True)

def onlyUpdate(obj: bpy.types.Object, src: mgl.Texture):
	"""Only writes the specified texture to a Blender Image used by other methods.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	_ = texture.writeImage(f"HYD_{obj.name}_DISPLACE", src)
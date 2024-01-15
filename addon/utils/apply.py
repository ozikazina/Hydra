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
		disp.inputs["Scale"].default_value = obj.hydra_erosion.org_scale * 0.5
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

	if len(obj.modifiers) == 0 or not obj.modifiers[-1].name.startswith("HYD_"):
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
	mod.strength = obj.hydra_erosion.org_scale
	
	coll = obj.users_collection[0]	#always exists
	emptyName = "HYD_" + obj.name + "_Guide"
	if emptyName in bpy.data.objects:
		empty = bpy.data.objects[emptyName]
	else:
		empty = bpy.data.objects.new(emptyName, None)
		coll.objects.link(empty)
	empty.parent = obj
	
	ar = np.array(obj.bound_box)
	cx = (ar[4][0] + ar[0][0]) * 0.5
	cy = (ar[2][1] + ar[0][1]) * 0.5
	cz = (ar[1][2] + ar[0][2]) * 0.5
	sx = 0.5*(ar[4][0] - ar[0][0])
	sy = 0.5*(ar[2][1] - ar[0][1])
	empty.location = (cx,cy,cz)
	empty.scale = (sx,sy,1)
	mod.texture_coords_object = empty

# --------------------------------------------------

P_MOD_NAME = "HYD_Preview_Modifier"
"""Preview modifier name."""
P_GUIDE_NAME = "HYD_Preview_Guide"
"""Preview guide Empty object name."""
P_IMG_NAME = "HYD_Preview_Image"
"""Preview temporary image name."""
P_VIEW_NAME = "HYD_Image_Preview"	#different from object preview heightmap
"""Image preview name."""

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
	"""Previews the specified texture as a modifier on the specified object.
	
	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	if data.lastPreview and data.lastPreview in bpy.data.objects:
		last = bpy.data.objects[data.lastPreview]
		if P_MOD_NAME in last.modifiers:
			last.modifiers.remove(last.modifiers[P_MOD_NAME])

	showGenModifier(obj, False)

	if P_MOD_NAME in obj.modifiers:
		mod = obj.modifiers[P_MOD_NAME]
	else:
		mod = obj.modifiers.new(P_MOD_NAME, "DISPLACE")
	
	if P_MOD_NAME in bpy.data.textures:
		txt = bpy.data.textures[P_MOD_NAME]
		common.data.info += ["Updated existing displacement."]
	else:
		txt = bpy.data.textures.new(P_MOD_NAME, "IMAGE")
		common.data.info += ["Created new displacement."]

	img = texture.writeImage(P_IMG_NAME, src)

	txt.image = img
	mod.texture = txt
	mod.direction = 'Z'
	mod.texture_coords = "OBJECT"
	mod.strength = obj.hydra_erosion.org_scale
	
	coll = obj.users_collection[0]	#always exists

	if P_GUIDE_NAME in bpy.data.objects:
		empty = bpy.data.objects[P_GUIDE_NAME]
	else:
		empty = bpy.data.objects.new(P_GUIDE_NAME, None)
		coll.objects.link(empty)
	empty.parent = obj
	
	ar = np.array(obj.bound_box)
	cx = (ar[4][0] + ar[0][0]) * 0.5
	cy = (ar[2][1] + ar[0][1]) * 0.5
	cz = (ar[1][2] + ar[0][2]) * 0.5
	sx = 0.5*(ar[4][0] - ar[0][0])
	sy = 0.5*(ar[2][1] - ar[0][1])
	empty.location = (cx,cy,cz)
	empty.scale = (sx,sy,1)
	mod.texture_coords_object = empty

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
	
	if P_GUIDE_NAME in bpy.data.objects:
		guide = bpy.data.objects[P_GUIDE_NAME]
		bpy.data.objects.remove(guide)
	
	if P_IMG_NAME in bpy.data.images:
		img = bpy.data.images[P_IMG_NAME]
		bpy.data.images.remove(img)

	data.lastPreview = ""


P_LAND_TEMP_NAME = "HYD_TEMP_DISPLACE"

def configureLandscape(obj: bpy.types.Object, src: mgl.Texture):
	"""Shapes the specified grid object using the input heightmap texture.
	
	:param obj: Object to shape.
	:type obj: :class:`bpy.types.Object`
	:param src: Heightmap texture.
	:type src: :class:`moderngl.Texture`"""
	img = texture.writeImage(P_LAND_TEMP_NAME, src)
	mod = obj.modifiers.new(P_LAND_TEMP_NAME, "DISPLACE")
	txt = bpy.data.textures.new(P_LAND_TEMP_NAME, "IMAGE")

	txt.image = img
	mod.texture = txt
	mod.direction = 'Z'
	mod.texture_coords = "OBJECT"

	bpy.ops.object.modifier_apply(modifier=P_LAND_TEMP_NAME)

	bpy.data.textures.remove(txt)
	bpy.data.images.remove(img)
"""Module responsible for applying heightmaps, previews and modifiers."""

import bpy
import numpy as np
from Hydra import common
from Hydra.sim import heightmap
from Hydra.utils import texture, nav, nodes
import math

# -------------------------------------------------- Previews

PREVIEW_MOD_NAME = "HYD_Preview_Modifier"
"""Preview modifier name."""
PREVIEW_DISP_NAME = "HYDP_Preview_Displacement"
"""Preview temporary image name."""
PREVIEW_IMG_NAME = "HYDP_Image_Preview"	#different from object preview heightmap
"""Image preview name."""
PREVIEW_GEO_NAME = "HYDP_Preview"
"""Geometry Nodes group name."""

def show_gen_modifier(obj: bpy.types.Object, visible: bool):
	"""Internal. Shows or hides the first modifier created by Hydra belonging to the specified object.
	
	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param visible: Modifier visibility.
	:type visible: :class:`bool`"""
	mod = next((x for x in obj.modifiers if x.name.startswith("HYD_")), None)
	if mod and mod.name != PREVIEW_MOD_NAME:
		mod.show_viewport = visible

def add_preview(target: bpy.types.Object|bpy.types.Image):
	"""Previews the specified texture as a geometry node on the specified object, or as an image.
	
	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data
	hyd = target.hydra_erosion

	if not common.data.has_map(hyd.map_result):
		return

	if isinstance(target, bpy.types.Image):
		img = texture.write_image(PREVIEW_IMG_NAME, data.maps[hyd.map_result].texture)
		nav.goto_image(img)
	else:
		if data.lastPreview and data.lastPreview in bpy.data.objects:
			last = bpy.data.objects[data.lastPreview]
			if last != target and PREVIEW_MOD_NAME in last.modifiers:
				last.modifiers.remove(last.modifiers[PREVIEW_MOD_NAME])

		if data.lastPreview != target.name and PREVIEW_GEO_NAME in bpy.data.node_groups:
			g = bpy.data.node_groups[PREVIEW_GEO_NAME]
			bpy.data.node_groups.remove(g)

		show_gen_modifier(target, False)

		if PREVIEW_MOD_NAME in target.modifiers:
			mod = target.modifiers[PREVIEW_MOD_NAME]
			common.data.add_message("Updated existing preview.")
		else:
			mod = target.modifiers.new(PREVIEW_MOD_NAME, "NODES")
			common.data.add_message("Created preview modifier.")
		
		img = heightmap.get_displacement(target, PREVIEW_DISP_NAME)
		mod.node_group = nodes.get_or_make_displace_group(PREVIEW_GEO_NAME, img)

		common.data.lastPreview = target.name

		nav.goto_modifier()

def remove_preview():
	"""Removes the preview modifier from the last previewed object and deletes last preview image."""
	data = common.data
	if str(data.lastPreview) in bpy.data.objects:
		last = bpy.data.objects[data.lastPreview]
		if PREVIEW_MOD_NAME in last.modifiers:
			last.modifiers.remove(last.modifiers[PREVIEW_MOD_NAME])
		show_gen_modifier(last, True)
	elif data.lastPreview: #invalid data
		previewed = [i for i in bpy.data.objects if PREVIEW_MOD_NAME in i.modifiers]
		for i in previewed:
			i.modifiers.remove(i.modifiers[PREVIEW_MOD_NAME])
			show_gen_modifier(i, True)

	if PREVIEW_MOD_NAME in bpy.data.textures:
		txt = bpy.data.textures[PREVIEW_MOD_NAME]
		bpy.data.textures.remove(txt)
	
	if PREVIEW_DISP_NAME in bpy.data.images:
		img = bpy.data.images[PREVIEW_DISP_NAME]
		bpy.data.images.remove(img)

	if PREVIEW_IMG_NAME in bpy.data.images:
		img = bpy.data.images[PREVIEW_IMG_NAME]
		bpy.data.images.remove(img)

	if PREVIEW_GEO_NAME in bpy.data.node_groups:
		g = bpy.data.node_groups[PREVIEW_GEO_NAME]
		bpy.data.node_groups.remove(g)

	data.lastPreview = ""

# -------------------------------------------------- Shaders

H_NAME_BUMP = "Hydra Bump"
"""Bump map node name."""

def add_bump(obj: bpy.types.Object, img: bpy.types.Image):
	"""Adds a Bump map for the given texture in the specified object's material.
	Creates a material if needed, otherwise selects the first material slot.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data

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
	tree = mat.node_tree
	
	if H_NAME_BUMP in tree.nodes: #already updated
		tree.nodes[H_NAME_BUMP].image = img
		return
	
	out = nodes.get_or_make_output_node(tree)
		
	if not out.inputs["Surface"].is_linked:
		shader = nodes.make_bsdf(tree)
		tree.links.new(out.inputs["Surface"], shader.outputs["BSDF"])
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
		bump = tree.nodes.new("ShaderNodeBump")
		tree.links.new(shader.inputs["Normal"], bump.outputs["Normal"])
	
	if bump.inputs["Height"].is_linked:
		data.error += ["Material already implements a different bump map.\n"]
		return
	
	bump.inputs["Distance"].default_value = 0.2
	
	imgNode,coords = nodes.setup_image_node(tree, "Bumpmap", img)
	tree.links.new(bump.inputs["Height"], imgNode.outputs["Color"])
	nodes.minimize_node(imgNode)
	nodes.stagger_nodes(shader, [bump], [imgNode], [coords])

H_NAME_DISP = "Hydra Displacement"
"""Displacement map node name."""

def add_displacement(obj: bpy.types.Object, img: bpy.types.Image):
	"""Adds a Displacement map for the given texture in the specified object's material.
	Creates a material if needed, otherwise selects the first material slot.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data

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
	tree = mat.node_tree
	
	if H_NAME_DISP in tree.nodes:	#Image node already exists
		tree.nodes[H_NAME_DISP].image = img
		return
	
	out = nodes.get_or_make_output_node(tree)

	if not out.inputs["Displacement"].is_linked:
		disp = tree.nodes.new("ShaderNodeDisplacement")
		disp.inputs["Midlevel"].default_value = 0
		disp.inputs["Scale"].default_value = 1
		tree.links.new(out.inputs["Displacement"], disp.outputs["Displacement"])
		norm = nodes.setup_vector_node(tree, disp)
	else:
		disp = out.inputs["Displacement"].links[0].from_node
		if disp.bl_idname != "ShaderNodeDisplacement":
			data.error += ["Material already implements a different displacement map."]
			return
	
	if disp.inputs["Height"].is_linked:
		data.error += ["Material already implements a different displacement map."]
		return
	
	imgNode, coords = nodes.setup_image_node(tree, H_NAME_DISP, img)
	tree.links.new(disp.inputs["Height"], imgNode.outputs["Color"])
	nodes.minimize_node(imgNode)
	
	nodes.stagger_nodes(out, [disp], [imgNode, norm], [coords], forwards=True)

# -------------------------------------------------- Modifier

def add_modifier(obj: bpy.types.Object, img: bpy.types.Image):
	"""Adds a Displace modifier to the specified object.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data

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
		data.add_message("Updated existing displacement.")
	else:
		txt = bpy.data.textures.new(mod.name, "IMAGE")
		data.add_message("Created new displacement.")

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

# -------------------------------------------------- Landscape

def add_landscape(img: bpy.types.Image):
	hyd = img.hydra_erosion

	resX = math.ceil(img.size[0] / hyd.gen_subscale)
	resY = math.ceil(img.size[1] / hyd.gen_subscale)

	bpy.ops.mesh.primitive_grid_add(x_subdivisions=resX, y_subdivisions=resY, location=bpy.context.scene.cursor.location)
	act = bpy.context.active_object

	if "." in img.name:
		name = img.name[:img.name.rfind(".")]
	else:
		name = img.name

	act.name = f"HYD_Gen_{name}"
	act.hydra_erosion.is_generated = True
	act.scale[1] = img.size[1] / img.size[0]

	for polygon in act.data.polygons:
		polygon.use_smooth = True

	mod = act.modifiers.new(PREVIEW_MOD_NAME, "NODES")
	
	mod.node_group = nodes.get_or_make_displace_group(PREVIEW_MOD_NAME, image=img)

	bpy.ops.object.mode_set(mode="OBJECT")	# modifiers can't be applied in EDIT mode

	bpy.ops.object.transform_apply(scale=True, location=False, rotation=False, properties=False, isolate_users=False)
	bpy.ops.object.modifier_apply(modifier=PREVIEW_MOD_NAME)
	
	bpy.data.node_groups.remove(bpy.data.node_groups[PREVIEW_MOD_NAME])

	nav.goto_object(act)

# -------------------------------------------------- Geometry Nodes

def add_geometry_nodes(obj: bpy.types.Object, img: bpy.types.Image):
	"""Adds a Geometry Nodes modifier to the specified object.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""

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
	
	mod.node_group = nodes.get_or_make_displace_group(f"HYD_{obj.name}", img)

def add_into_geometry_nodes(obj: bpy.types.Object, img: bpy.types.Image):
	"""Adds the texture into an existing Geometry Nodes modifier.

	:param obj: Object to add to.
	:type obj: :class:`bpy.types.Object`
	:param src: Source texture to add.
	:type src: :class:`moderngl.Texture`"""
	data = common.data

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

	displace_group = nodes.get_or_make_displace_group("HYD_Displace")

	connected = None
	if output.inputs[0].is_linked:
		connected = output.inputs[0].links[0].from_node

		if connected.type == "GROUP" and connected.node_tree == displace_group:
			connected.inputs[1].default_value = img
			connected.inputs[2].default_value = 1
			data.add_message("Updated existing displacement.")
			return
	
	g = nodes.new("GeometryNodeGroup")
	g.node_tree = displace_group
	g.inputs[1].default_value = img
	g.inputs[2].default_value = 1

	links.new(g.outputs[0], output.inputs[0])

	if connected:
		links.new(connected.outputs[0], g.inputs[0])

	nodes.stagger_nodes(output, [g], forwards=True)
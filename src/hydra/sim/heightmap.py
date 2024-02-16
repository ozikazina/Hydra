"""Module responsible for heightmap generation."""

import moderngl as mgl
from Hydra.utils import texture, model
from Hydra import common
import bpy
import bpy.types
import numpy as np
import platform

def generate_heightmap(obj: bpy.types.Object, normalized: bool=False, world_scale: bool=False, local_scale: bool=False)->mgl.Texture:
	"""Creates a heightmap for the specified object and returns it.
	
	:param obj: Object to generate from.
	:type obj: :class:`bpy.types.Object`
	:return: Generated heightmap.
	:rtype: :class:`moderngl.Texture`"""
	print("Preparing heightmap generation.")
	
	data = common.data
	ctx = data.context
	mesh, verts = model.evaluate_mesh(obj)

	if platform.system() != "Windows" or common.get_preferences().skip_indexing:
		print("Skipping vertex indexing.")
		verts = [i.co for face in mesh.faces for i in face.verts]
		vao = model.create_vao(ctx, data.programs["heightmap"], vertices=verts)
	else:
		verts = [i.co for i in verts]
		inds = [i.index for face in mesh.faces for i in face.verts]
		vao = model.create_vao(ctx, data.programs["heightmap"], vertices=verts, indices=inds)

	size = obj.hydra_erosion.get_size()
	txt = ctx.texture(size, 1, dtype="f4")
	depth = ctx.depth_texture(size)

	model.recalculate_scales(obj)
	resize_matrix = model.get_resize_matrix(obj)

	if normalized:
		scale = 1
	elif world_scale:
		scale = obj.hydra_erosion.org_scale * obj.scale.z
	elif local_scale:
		scale = obj.hydra_erosion.org_scale
	else:
		scale = obj.hydra_erosion.height_scale

	fbo = ctx.framebuffer(color_attachments=(txt), depth_attachment=depth)

	with ctx.scope(fbo, mgl.DEPTH_TEST):
		fbo.clear(depth=2.0)
		vao.program["resize_matrix"].value = resize_matrix
		vao.program["scale"] = scale
		vao.render()
		ctx.finish()

	depth.release()
	fbo.release()
	vao.release()

	print("Generation finished.")
	return txt

def generate_heightmap_from_image(img:bpy.types.Image)->mgl.Texture:
	"""Creates a heightmap for the specified image and returns it.
	
	:param img: Image to generate from.
	:type img: :class:`bpy.types.Image`
	:return: Generated heightmap.
	:rtype: :class:`moderngl.Texture`"""
	pixels = np.array(img.pixels).astype('f4')[::4].copy()#has to be contiguous in memory
	txt = common.data.context.texture(tuple(img.size), 1, dtype='f4', data=pixels)
	if img.colorspace_settings.name == "sRGB":
		prog: mgl.ComputeShader = common.data.shaders["linear"]
		txt.bind_to_image(1, read=True, write=True)
		prog["map"].value = 1
		prog.run(txt.width, txt.height)	# txt = linearize(txt)
	return txt

def prepare_heightmap(obj: bpy.types.Image | bpy.types.Object):
	"""Creates or replaces a base map for the given Image or Object. Also creates a source map if needed.

	:param obj: Object or image to generate from.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	hyd = obj.hydra_erosion
	data = common.data

	reload = not data.has_map(hyd.map_base)	#no base or invalid data -> reload completely

	data.try_release_map(hyd.map_base)

	if type(obj) == bpy.types.Image:
		hyd.img_size = obj.size
		txt = generate_heightmap_from_image(obj)
	else:
		txt = generate_heightmap(obj)

	hmid = data.create_map("Base map", txt)
	hyd.map_base = hmid

	if reload:	#source is invalid too
		data.try_release_map(hyd.map_source)
	
	if not data.has_map(hyd.map_source):	#freed or not defined in the first place
		txt = texture.clone(txt)
		hmid = data.create_map("Base map", txt)
		hyd.map_source = hmid

def subtract(modified: mgl.Texture, base: mgl.Texture, scale: float=1.0)->mgl.Texture:
	"""Subtracts given textures and returns difference relative to `base` as a result. Also scales result if needed.
	
	:param modified: Current heightmap. Minuend.
	:type modified: :class:`moderngl.Texture`
	:param base: Base heightmap. Subtrahend.
	:type base: :class:`moderngl.Texture`
	:return: A texture equal to (modified - base).
	:rtype: :class:`moderngl.Texture`"""
	txt = texture.clone(modified)
	prog: mgl.ComputeShader = common.data.shaders["diff"]
	txt.bind_to_image(1, read=True, write=True)
	prog["A"].value = 1
	base.bind_to_image(2, read=True, write=False)
	prog["B"].value = 2
	prog["factor"] = 1.0
	#A=A-B
	prog.run(base.width, base.height)

	if scale != 1.0:
		prog = common.data.shaders["scaling"]
		prog["A"].value = 1
		prog["scale"] = scale
		#A *= scale
		prog.run(base.width, base.height)
	
	common.data.context.finish()
	return txt

def get_displacement(obj: bpy.types.Object, name:str)->bpy.types.Image:
	"""Creates a heightmap difference as a Blender Image.

	:param obj: Object to apply to.
	:type obj: :class:`bpy.types.Object`
	:param current: Current heightmap to preview.
	:type current: :class:`common.Heightmap`
	:param base: Base heightmap for difference calculation.
	:type base: :class:`common.Heightmap`"""
	data = common.data
	hyd = obj.hydra_erosion

	target = subtract(data.get_map(hyd.map_result).texture,
		data.get_map(hyd.map_base).texture,
		scale=obj.hydra_erosion.org_scale/obj.hydra_erosion.height_scale)

	ret = texture.write_image(name, target)
	target.release()

	return ret

def set_result_as_source(obj: bpy.types.Object | bpy.types.Image, as_base: bool = False):
	"""Applies the Result map as a Source map.

	:param obj: Object or image to modify.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`
	:param asBase: Applies as base as well if `True`.
	:type asBase: :class:`bool`"""
	common.data.try_release_map(obj.hydra_erosion.map_source)
	obj.hydra_erosion.map_source = obj.hydra_erosion.map_result
	obj.hydra_erosion.map_result = ""
	if as_base:
		common.data.try_release_map(obj.hydra_erosion.map_base)
		src = common.data.get_map(obj.hydra_erosion.map_source)
		target = texture.clone(src.texture)
		obj.hydra_erosion.map_base = common.data.create_map(src.name, target)

def nuke_gui():
	"""Gives an authentic developer experience."""
	ctx = common.data.context

	# using a frame buffer without scope sets the number of channels permanently
	fbo = ctx.simple_framebuffer((512,512), 1, dtype="f4")
	fbo.use()
	fbo.clear()
	fbo.release()
	# only the red channel will change from now on

	# ctx.enable(mgl.CULL_FACE) # makes buttons disappear

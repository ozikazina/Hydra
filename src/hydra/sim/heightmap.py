"""Module responsible for heightmap generation."""

import moderngl as mgl
from Hydra.utils import texture, model, apply
from Hydra import common
import bpy
import bpy.types
import numpy as np
import platform

def genHeightmap(obj: bpy.types.Object, normalized: bool=False, world_scale: bool=False, local_scale: bool=False)->mgl.Texture:
	"""Creates a heightmap for the specified object and returns it.
	
	:param obj: Object to generate from.
	:type obj: :class:`bpy.types.Object`
	:return: Generated heightmap.
	:rtype: :class:`moderngl.Texture`"""
	print("Preparing heightmap generation.")
	
	data = common.data
	ctx = data.context
	mesh, verts = model.evaluateMesh(obj)

	if platform.system() != "Windows" or common.getPreferences().skip_indexing:
		print("Skipping vertex indexing.")
		verts = [i.co for face in mesh.faces for i in face.verts]
		vao = model.createVAO(ctx, data.programs["heightmap"], vertices=verts)
	else:
		verts = [i.co for i in verts]
		inds = [i.index for face in mesh.faces for i in face.verts]
		vao = model.createVAO(ctx, data.programs["heightmap"], vertices=verts, indices=inds)

	size = obj.hydra_erosion.getSize()
	txt = ctx.texture(size, 1, dtype="f4")
	depth = ctx.depth_texture(size)

	model.recalculateScales(obj)
	resize_matrix = model.getResizeMatrix(obj)

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

def genHeightmapFromImage(img:bpy.types.Image)->mgl.Texture:
	"""Creates a heightmap for the specified image and returns it.
	
	:param img: Image to generate from.
	:type img: :class:`bpy.types.Image`
	:return: Generated heightmap.
	:rtype: :class:`moderngl.Texture`"""
	pixels = np.array(img.pixels).astype('f4')[::4].copy()#has to be contiguous in memory
	txt = common.data.context.texture(tuple(img.size), 1, dtype='f4', data=pixels)
	if not img.is_float:
		prog: mgl.ComputeShader = common.data.shaders["linear"]
		txt.bind_to_image(1, read=True, write=True)
		prog["map"].value = 1
		prog.run(txt.width, txt.height)	# txt = linearize(txt)
	return txt

def prepareHeightmap(obj: bpy.types.Image | bpy.types.Object):
	"""Creates or replaces a base map for the given Image or Object. Also creates a source map if needed.

	:param obj: Object or image to generate from.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`"""
	hyd = obj.hydra_erosion
	data = common.data

	reload = not data.hasMap(hyd.map_base)	#no base or invalid data -> reload completely

	data.releaseMap(hyd.map_base)

	if type(obj) == bpy.types.Image:
		hyd.img_size = obj.size
		txt = genHeightmapFromImage(obj)
	else:
		txt = genHeightmap(obj)

	hmid = data.createMap("Base map", txt)
	hyd.map_base = hmid

	if reload:	#source is invalid too
		data.releaseMap(hyd.map_source)
	
	if not data.hasMap(hyd.map_source):	#freed or not defined in the first place
		txt = texture.clone(txt)
		hmid = data.createMap("Base map", txt)
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

def preview(obj: bpy.types.Object, current: common.Heightmap, base: common.Heightmap):
	"""Creates a heightmap difference and previews it.

	:param obj: Object to apply to.
	:type obj: :class:`bpy.types.Object`
	:param current: Current heightmap to preview.
	:type current: :class:`common.Heightmap`
	:param base: Base heightmap for difference calculation.
	:type base: :class:`common.Heightmap`"""
	target = subtract(current.texture, base.texture, scale=obj.hydra_erosion.org_scale/obj.hydra_erosion.height_scale)
	apply.addPreview(obj, target)
	target.release()

def setCurrentAsSource(obj: bpy.types.Object | bpy.types.Image, asBase: bool = False):
	"""Applies the current map as a source map.

	:param obj: Object or image to modify.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`
	:param asBase: Applies as base as well if `True`.
	:type asBase: :class:`bool`"""
	common.data.releaseMap(obj.hydra_erosion.map_source)
	obj.hydra_erosion.map_source = obj.hydra_erosion.map_current
	obj.hydra_erosion.map_current = ""
	if asBase:
		common.data.releaseMap(obj.hydra_erosion.map_base)
		src = common.data.maps[obj.hydra_erosion.map_source]
		target = texture.clone(src.texture)
		obj.hydra_erosion.map_base = common.data.createMap(src.name, target)
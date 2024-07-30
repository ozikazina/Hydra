"""Module responsible for heightmap generation."""

import moderngl as mgl
from Hydra.utils import texture, model
from Hydra import common
import bpy
import bpy.types
import numpy as np
import math

def _generate_heightmap_flat(obj: bpy.types.Object, size:tuple[int,int]|None = None, normalized: bool=False, world_scale: bool=False, local_scale: bool=False):
	resize_matrix = model.get_resize_matrix(obj)

	ctx = common.data.context

	vao = model.create_vaos(ctx, [common.data.programs["heightmap"]], obj)[0]

	if normalized:
		scale = 1
	elif world_scale:
		scale = obj.hydra_erosion.org_scale * obj.scale.z
	elif local_scale:
		scale = obj.hydra_erosion.org_scale
	else:
		scale = obj.hydra_erosion.height_scale

	txt = ctx.texture(size, 1, dtype="f4")
	depth = ctx.depth_texture(size)
	fbo = ctx.framebuffer(color_attachments=(txt), depth_attachment=depth)

	with ctx.scope(fbo, mgl.DEPTH_TEST):
		fbo.clear(depth=256.0)
		vao.program["resize_matrix"].value = resize_matrix
		vao.program["scale"] = scale
		vao.render()
		ctx.finish()

	depth.release()
	fbo.release()
	vao.release()

	return txt

def _generate_heightmap_equirect(obj: bpy.types.Object, size:tuple[int,int]|None = None, normalized: bool=False, world_scale: bool=False, local_scale: bool=False):
	ctx = common.data.context
	
	vao_polar, vao_equirect = model.create_vaos(ctx, [common.data.programs["polar"], common.data.programs["equirect"]], obj)

	equirect_txt = ctx.texture(size, 1, dtype="f4")
	equirect_txt.bind_to_image(1, read=True, write=True)
	depth = ctx.depth_texture(size)

	fbo = ctx.framebuffer(color_attachments=(equirect_txt), depth_attachment=depth)

	resize_matrix = model.get_resize_matrix(obj, planet=True, with_scale=world_scale)

	with ctx.scope(fbo, mgl.DEPTH_TEST | mgl.CULL_FACE):
		fbo.clear(depth=256.0)
		rmatrix = list(resize_matrix)
		vao_equirect.program["resize_matrix"].value = rmatrix
		vao_equirect.program["offset_x"] = -0.5
		vao_equirect.render()

		rmatrix = list(resize_matrix)
		rmatrix[0] = -rmatrix[0]
		rmatrix[4 + 1] = -rmatrix[4 + 1] # 180 degree rotation around Z axis
		vao_equirect.program["resize_matrix"].value = rmatrix
		vao_equirect.program["offset_x"] = 0.5
		vao_equirect.render()
		ctx.finish()

	vao_equirect.release()
	fbo.release()
	depth.release()
	
	polar_size = min(size[0], size[1])
	polar_size = (polar_size, polar_size)

	polar = ctx.texture(polar_size, 1, dtype="f4")
	depth = ctx.depth_texture(polar_size)

	polar_sampler = ctx.sampler(texture=polar, repeat_x=False, repeat_y=False)
	polar_sampler.use(1)
	polar.use(1)

	# Mapping from polar to equirectangular
	equi_mapping = common.data.shaders["to_equirect"]
	groups = (math.ceil(size[0] / 32), math.ceil(0.25 * size[1] / 32))	# only half the hemisphere is mapped from polar, one hemisphere at a time
	equi_mapping["in_height"] = 1 # sampler
	equi_mapping["out_height"].value = 1 # equirect_txt
	equi_mapping["tile_mult"] = (1 / size[0], 1 / size[1])

	fbo = ctx.framebuffer(color_attachments=(polar), depth_attachment=depth)
	with ctx.scope(fbo, mgl.DEPTH_TEST):
		# Upper polar projection
		fbo.clear(depth=256.0)
		rmatrix = list(resize_matrix)
		rmatrix[0] = -rmatrix[0]
		rmatrix[4 + 1] = -rmatrix[4 + 1] # 180 degree rotation around Z axis
		vao_polar.program["resize_matrix"].value = rmatrix
		vao_polar.render()
		ctx.finish()

		equi_mapping["offset_y"] = math.ceil(3 * size[1] / 4)
		equi_mapping["flip_y"] = True
		equi_mapping.run(groups[0], groups[1])
		ctx.finish()

		# Lower polar projection
		fbo.clear(depth=256.0)
		rmatrix = list(resize_matrix)
		rmatrix[4 + 1] = -rmatrix[4 + 1] # 180 degree rotation around Z axis
		rmatrix[8 + 2] = -rmatrix[8 + 2] # 180 degree rotation around Y axis
		vao_polar.program["resize_matrix"].value = rmatrix
		vao_polar.render()
		ctx.finish()

		equi_mapping["offset_y"] = 0
		equi_mapping["flip_y"] = False
		equi_mapping.run(groups[0], groups[1])
		ctx.finish()
	
	vao_polar.release()
	fbo.release()
	depth.release()
	polar_sampler.release()
	polar.release()

	if normalized:
		# Reduction
		mn, mx = texture.get_min_max(equirect_txt)
		scale = 1 / max(mx - mn, 1e-5)
		offset = -mn
		texture.scale(equirect_txt, scale, offset)
	elif world_scale:
		scale = 1 / min([resize_matrix[0], resize_matrix[4 + 1], resize_matrix[8 + 2]])
		texture.scale(equirect_txt, scale)
	elif local_scale:
		scale = 1 / resize_matrix[0]
		texture.scale(equirect_txt, scale)

	return equirect_txt

def generate_heightmap(obj: bpy.types.Object, size:tuple[int,int]|None = None, normalized: bool=False, world_scale: bool=False, local_scale: bool=False, equirect: bool=False)->mgl.Texture:
	"""Creates a heightmap for the specified object and returns it.
	
	:param obj: Object to generate from.
	:type obj: :class:`bpy.types.Object`
	:param normalized: If `True`, the heightmap will be normalized.
	:type normalized: :class:`bool`
	:param world_scale: If `True`, the heightmap will have local-space heights.
	:type world_scale: :class:`bool`
	:param local_scale: If `True`, the heightmap will have world-space heights.
	:type local_scale: :class:`bool`
	:return: Generated heightmap.
	:rtype: :class:`moderngl.Texture`"""
	print("Preparing heightmap generation.")

	if size is None:
		if not common.get_preferences().direct_resolution:
			if equirect:
				size = obj.hydra_erosion.get_size()
				size = (2 * size[1], size[1])
				obj.hydra_erosion.img_size = size
			else:
				ar = list(bpy.context.active_object.bound_box)
				dx = ar[4][0] - ar[0][0]
				dy = ar[2][1] - ar[0][1]
				val = obj.hydra_erosion.x_img_res

				try:
					if dy > dx:
						size = (val, math.ceil(val * dy / dx))
					else:
						size = (math.ceil(val * dx / dy), val)
				except ZeroDivisionError:
					size = (16, 16)
				obj.hydra_erosion.img_size = size
		else:
			size = obj.hydra_erosion.get_size()

	model.recalculate_scales(obj)

	if equirect:
		txt = _generate_heightmap_equirect(obj, size, normalized, world_scale, local_scale)
	else:
		txt = _generate_heightmap_flat(obj, size, normalized, world_scale, local_scale)

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

def prepare_heightmap(obj: bpy.types.Image | bpy.types.Object)->None:
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
		txt = generate_heightmap(obj, equirect = hyd.tiling=="planet")

	hmid = data.create_map("Base map", txt)
	hyd.map_base = hmid

	if reload:	#source is invalid too
		data.try_release_map(hyd.map_source)
	
	if not data.has_map(hyd.map_source):	#freed or not defined in the first place
		txt = texture.clone(txt)
		hmid = data.create_map("Base map", txt)
		hyd.map_source = hmid

def subtract(modified: mgl.Texture, base: mgl.Texture, factor: float = 1.0, scale: float = 1.0)->mgl.Texture:
	"""Subtracts given textures and returns difference relative to `base` as a result. Also scales result if needed.
	
	:param modified: Current heightmap. Minuend.
	:type modified: :class:`moderngl.Texture`
	:param base: Base heightmap. Subtrahend.
	:type base: :class:`moderngl.Texture`
	:param scale: Scale factor for the result.
	:type scale: :class:`float`
	:param factor: Multiplication factor for the second texture.
	:type factor: :class:`float`
	:return: A texture equal to (scale * (modified - factor * base)).
	:rtype: :class:`moderngl.Texture`"""
	return add(modified, base, -factor, scale)

def add(A: mgl.Texture, B: mgl.Texture, factor: float = 1.0, scale: float = 1.0, )->mgl.Texture:
	"""Adds given textures and returns the result as a new texture.
	
	:param A: First texture.
	:type A: :class:`moderngl.Texture`
	:param B: Second texture.
	:type B: :class:`moderngl.Texture`
	:param scale: Scale factor for the result.
	:type scale: :class:`float`
	:param factor: Multiplication factor for the second texture.
	:type factor: :class:`float`
	:return: A texture equal to (scale * (A + factor * B)).
	:rtype: :class:`moderngl.Texture`"""
	txt = texture.clone(A)
	prog: mgl.ComputeShader = common.data.shaders["scaled_add"]
	txt.bind_to_image(1, read=True, write=True)
	prog["A"].value = 1
	B.bind_to_image(2, read=True, write=False)
	prog["B"].value = 2
	prog["factor"] = factor
	prog["scale"] = scale
	# A = scale * (A + factor * B)
	prog.run(A.width, A.height)
	
	common.data.context.finish()
	return txt

def get_displacement(obj: bpy.types.Object, name:str)->bpy.types.Image:
	"""Creates a heightmap difference as a Blender Image.

	:param obj: Object to apply to.
	:type obj: :class:`bpy.types.Object`
	:param name: Name of the created image.
	:type name: :class:`str`
	:return: Created image.
	:rtype: :class:`bpy.types.Image`"""
	data = common.data
	hyd = obj.hydra_erosion

	if obj.hydra_erosion.height_scale != 0:
		scale = obj.hydra_erosion.org_scale / obj.hydra_erosion.height_scale
	else:
		scale = 1.0

	target = subtract(data.get_map(hyd.map_result).texture,
		data.get_map(hyd.map_base).texture,
		scale=scale)

	ret, _ = texture.write_image(name, target)
	target.release()

	return ret

def set_result_as_source(obj: bpy.types.Object | bpy.types.Image, as_base: bool = False)->None:
	"""Applies the Result map as a Source map.

	:param obj: Object or image to modify.
	:type obj: :class:`bpy.types.Object` or :class:`bpy.types.Image`
	:param asBase: Applies as base as well if `True`.
	:type asBase: :class:`bool`"""
	hyd = obj.hydra_erosion
	if hyd.map_result == hyd.map_source:
		hyd.map_result = ""
		return
	
	common.data.try_release_map(hyd.map_source)
	hyd.map_source = hyd.map_result
	hyd.map_result = ""
	if as_base:
		common.data.try_release_map(hyd.map_base)
		src = common.data.get_map(hyd.map_source)
		target = texture.clone(src.texture)
		hyd.map_base = common.data.create_map(src.name, target)

def resize_texture(texture: mgl.Texture, target_size: tuple[int, int])->mgl.Texture:
	"""Resizes a texture to the specified size.

	:param texture: Texture to resize.
	:type texture: :class:`moderngl.Texture`
	:param target_size: New size.
	:type target_size: :class:`tuple`
	:return: Resized texture.
	:rtype: :class:`moderngl.Texture`"""
	prog: mgl.Program = common.data.programs["resize"]
	ctx: mgl.Context = common.data.context

	ret = ctx.texture(target_size, 1, dtype='f4')
	sampler = ctx.sampler(texture=texture, repeat_x=False, repeat_y=False)
	fbo = ctx.framebuffer(color_attachments=(ret))

	vao = model.create_vao(ctx, prog)

	with ctx.scope(fbo):
		fbo.clear()
		texture.use(1)
		sampler.use(1)
		vao.program["in_texture"] = 1
		vao.render()
		ctx.finish()

	sampler.release()
	vao.release()
	fbo.release()

	return ret

def add_subres(height: mgl.Texture, height_prior: mgl.Texture, height_prior_fullres: mgl.Texture)->mgl.Texture:
	"""Adds a resized difference to the original heightmap.

	Releases height_prior and height.

	:param height: Resulting heightmap to add.
	:type height: :class:`moderngl.Texture`
	:param height_prior: Previous heightmap for difference calculation.
	:type height_prior: :class:`moderngl.Texture`
	:param height_prior_fullres: Full resolution previous heightmap to add to.
	:type height_prior_fullres: :class:`moderngl.Texture`
	:return: New heightmap.
	:rtype: :class:`moderngl.Texture`"""
	
	dif = subtract(height, height_prior) # get difference
	height_prior.release()
	height.release()

	height = resize_texture(dif, height_prior_fullres.size) # resize difference
	dif.release()

	nh = add(height, height_prior_fullres) # add difference to original
	height.release()

	return nh

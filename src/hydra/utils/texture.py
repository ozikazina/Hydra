"""Module responsible for handling ModernGL textures and Blender images."""

import bpy, bpy.types
import numpy as np
import moderngl as mgl
from Hydra.utils import model
from Hydra import common

def get_or_make_image(size: 'tuple[int,int]', name: str)->'tuple[bpy.types.Image, bool]':
	"""Gets or creates an image of the specified name. If sizes are different, then it gets scaled to `size`.
	
	:param size: Resolution tuple.
	:type size: :class:`tuple[int,int]`
	:param name: Name of created image.
	:type name: :class:`str`
	:return: Created image. If the image was updated, returns `True` as the second value.
	:rtype: :class:`bpy.types.Image`"""
	updated = False

	if name not in bpy.data.images:
		img = bpy.data.images.new(name, size[0], size[1], alpha=False, float_buffer=True, is_data=True)
	else:
		img = bpy.data.images[name]
		img.colorspace_settings.name = "Non-Color"
		updated = True
	
	if tuple(img.size) != size:
		try:
			img.scale(size[0], size[1])
		except Exception:
			bpy.data.images.remove(img)
			img = bpy.data.images.new(name, size[0], size[1], alpha=False, float_buffer=True, is_data=True)

	img.hydra_erosion.is_generated = True
	return img, updated

def write_image(name: str, texture: mgl.Texture)->'tuple[bpy.types.Image, bool]':
	"""Writes texture to an `Image` of the specified name.
	
	:param name: Image name.
	:type name: :class:`str`
	:param txt: Texture to be read.
	:type txt: :class:`moderngl.Texture`
	:return: Created image.
	:rtype: :class:`bpy.types.Image`"""
	image, updated = get_or_make_image(texture.size, name)

	if texture.components == 1:
		pixels = np.frombuffer(texture.read(), dtype=np.float32).repeat(4)
		pixels[3::4] = 1.0
		image.pixels.foreach_set(pixels)
	elif texture.components == 2 or texture.components == 3:
		raise ValueError("Two or three channel fill isn't supported.")
	elif texture.components == 4:
		image.pixels.foreach_set(np.frombuffer(texture.read(), dtype=np.float32))
	
	image.update()
	image.pack()
	return image, updated

def create_texture(size: 'tuple[int,int]', pixels: bytes|None = None, image: bpy.types.Image|None = None, channels: int = 1)->mgl.Texture:
	"""Creates a :class:`moderngl.Texture` of the specified size.
	
	:param size: Resolution tuple.
	:type size: :class:`tuple[int,int]`
	:param pixels: Pixel data.
	:type pixels: :class:`bytes`
	:param image: Image to be used as a source.
	:type image: :class:`bpy.types.Image`
	:param channels: Channel count.
	:type channels: :class:`int`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""

	if channels < 1 or channels > 4:
		raise ValueError("Invalid channel count")
	if image is not None and pixels is not None:
		raise ValueError("Only one of image and pixels can be specified")

	data = common.data
	ctx = data.context

	if image is not None:
		pixels = np.empty(image.size[0] * image.size[1] * 4, dtype='f4')
		image.pixels.foreach_get(pixels)

		color = ctx.texture(tuple(image.size), 4, dtype="f4", data=pixels.tobytes())
		
		dest = ctx.texture(size, channels, dtype="f4")
		
		vao = model.create_vao(ctx, data.programs["redraw"])
		fbo = ctx.framebuffer(color_attachments=(dest))
		scope = ctx.scope(fbo)
		with scope:
			color.use(location=0)
			vao.program["source"].value = 0
			vao.program["linearize"] = not image.is_float
			vao.render()
		
		fbo.release()
		vao.release()
		color.release()
		return dest
	else:
		if pixels is None:	#pixels have to be cleared to zero if not specified!
			pixels = np.zeros(size[0] * size[1] * channels, dtype='f4').tobytes()
		return ctx.texture(size, channels, dtype="f4", data=pixels)
	
def clone(txt: mgl.Texture)->mgl.Texture:
	"""Clones a :class:`moderngl.Texture`.
	
	:param txt: Texture to be cloned.
	:type txt: :class:`mgl.Texture`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""
	return common.data.context.texture(txt.size, txt.components, dtype="f4", data=txt.read())

"""Module responsible for handling ModernGL textures and Blender images."""

import bpy, bpy.types
import numpy as np
import moderngl as mgl
from Hydra.utils import model
from Hydra import common

def getOrMakeImage(size: tuple[int,int], name: str)->bpy.types.Image:
	"""Gets or creates an image of the specified name. If sizes are different, then it gets scaled to `size`.
	
	:param size: Resolution tuple.
	:type size: :class:`tuple[int,int]`
	:param name: Name of created image.
	:type name: :class:`str`
	:return: Created image.
	:rtype: :class:`bpy.types.Image`"""
	if name not in bpy.data.images:
		img = bpy.data.images.new(name, size[0], size[1], alpha=False, float_buffer=True)
	else:
		img = bpy.data.images[name]
	
	img.use_generated_float = True
	if tuple(img.size) != size:
		img.scale(size[0], size[1])
	img.hydra.is_generated = True

	return img

def writeImage(name: str, txt: mgl.Texture)->bpy.types.Image:
	"""Writes texture to an `Image` of the specified name.
	
	:param name: Image name.
	:type name: :class:`str`
	:param txt: Texture to be read.
	:type txt: :class:`moderngl.Texture`
	:return: Created image.
	:rtype: :class:`bpy.types.Image`"""
	img = getOrMakeImage(txt.size, name)
	if txt.components == 1:
		fillImageMono(img, txt)
	else:
		fillImage(img, txt)
	img.pack()
	return img

def fillImageMono(image: bpy.types.Image, texture: mgl.Texture):
	"""Writes single channel texture data to an image.
	
	:param image: Image to be written to.
	:type image: :class:`bpy.types.Image`
	:param texture: Texture to be read.
	:type texture: :class:`moderngl.Texture`"""
	pixels = np.frombuffer(texture.read(), dtype=np.float32)
	pixels = [x for p in pixels for x in (p,p,p,1)]
	image.pixels = pixels

def fillImage(image: bpy.types.Image, texture: mgl.Texture):
	"""Writes four channel texture data to an image.
	
	:param image: Image to be written to.
	:type image: :class:`bpy.types.Image`
	:param texture: Texture to be read.
	:type texture: :class:`moderngl.Texture`"""
	image.pixels = np.frombuffer(texture.read(), dtype=np.float32)

def createTexture(size: tuple[int,int], pixels: bytes|None = None)->mgl.Texture:
	"""Creates a single channel :class:`moderngl.Texture` of the specified size.
	
	:param size: Resolution tuple.
	:type size: :class:`tuple[int,int]`
	:param pixels: Optional texture data.
	:type pixels: :class:`bytes` or :class:`None`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""
	if pixels is None:
		pixels = np.zeros(size[0]*size[1], dtype="f4").tobytes()
	return common.data.context.texture(size, 1, dtype="f4", data=pixels)

def createTextureFull(size: tuple[int,int])->mgl.Texture:
	"""Creates a four channel :class:`moderngl.Texture` of the specified size.
	
	:param size: Resolution tuple.
	:type size: :class:`tuple[int,int]`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""
	return common.data.context.texture(size, 4, dtype="f4")

def createColorTexture(size: tuple[int,int], image: bpy.types.Image)->mgl.Texture:
	"""Creates a four channel :class:`moderngl.Texture` from the specified image. Redraws to new size if needed.
	
	:param size: Final resolution tuple.
	:type size: :class:`tuple[int,int]`
	:param image: Image to be read.
	:type image: :class:`bpy.types.Image`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""
	data = common.data
	data.floatColor = image.is_float
	pixels = np.array(image.pixels).astype('f4').tobytes()
	color = data.context.texture(tuple(image.size), 4, dtype="f4", data=pixels)
	
	ctx = data.context
	dest = ctx.texture(size, 4, dtype="f4")
	
	vao = model.createVAO(ctx, data.programs["redraw"])
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

def clone(txt: mgl.Texture)->mgl.Texture:
	"""Clones a :class:`moderngl.Texture`.
	
	:param txt: Texture to be cloned.
	:type txt: :class:`mgl.Texture`
	:return: Created texture.
	:rtype: :class:`moderngl.Texture`"""
	return common.data.context.texture(txt.size, txt.components, dtype="f4", data=txt.read())

"""Global data and common functions module. Also defines :class:`Heightmap` class."""

import moderngl as mgl
import bpy, bpy.types

import uuid, re

class Heightmap:
	"""A wrapper around ModernGL textures."""
	def __init__(self, name: str, txt: mgl.Texture):
		"""Constructor method.

		:param name: Display name of the stored texture.
		:type name: :class:`str`
		:param txt: Texture to wrap.
		:type txt: :class:`moderngl.Texture:"""
		self.name = name
		self.texture = txt
	
	def release(self):
		"""Releases the stored texture."""
		self.texture.release()
	
	def read(self)->bytes:
		"""Reads the ModernGL texture.

		:return: Pixel data :class:`bytes`.
		:rtype: :class:`bytes`"""
		return self.texture.read()

	def get_size(self)->tuple[int,int]:
		"""Stored texture size property getter.

		:return: Texture size :class:`tuple`.
		:rtype: :class:`tuple`"""
		return tuple(self.texture.size)
	
	size = property(get_size)
	"""Texture size :class:`tuple` property."""

class HydraData(object):
	"""Global data object. Stores all ModernGL resources, including the context."""

	def __init__(self):
		"""Constructor method."""

		self.context: mgl.Context = None
		"""Addon's ModernGL context. Attached to Blender's OpenGL context."""

		self.maps: dict[str, Heightmap] = {}
		"""Heightmap dictionary. Uses UUID strings as keys."""

		self.active: list[mgl.Texture | None] = []
		"""List of temporary textures for erosion simulations."""

		self.programs: dict[str, mgl.Program] = {}
		"""Compiled ModernGL program list."""

		self.shaders: dict[str, mgl.ComputeShader] = {}
		"""Compiled ModernGL compute shader list."""

		self.scope: mgl.Scope = None
		"""Temporary ModernGL scope."""

		self.fbo: mgl.Framebuffer = None
		"""Temporary ModernGL Frame Buffer Object."""

		self.running: bool = False	#for progress bar if implemented
		"""Unused. Allows erosion to be terminated."""
		self.progress: float = 0.0
		"""Unused. Erosion progress."""
		self.iteration: int = 0
		"""Unused. Erosion iteration."""
		
		self.lastPreview: str | None = None
		"""Name of last previewed object."""

		self.info: list[str] = []
		"""Info message list."""
		self.error: list[str] = []
		"""Error message list."""
	
	def initContext(self):
		"""Creates and saves the attached ModernGL :attr:`context`."""
		self.context = mgl.create_context()	#standalone crashes blender

	def hasMap(self, id: str | None)->bool:
		"""Checks if map exists.

		:return: `True` if map exists in the :attr:`maps` list. `False` otherwise.
		:rtype: :class:`bool`"""
		return id in self.maps

	def releaseMap(self, id: str | None):
		"""Release specified map. Does nothing on invalid `id`.

		:param id: Map ID.
		:type id: :class:`str` or :class:`None`"""
		if id in self.maps:
			self.maps[id].release()
			del self.maps[id]
	
	def createMap(self, name: str, txt: mgl.Texture)->str:
		"""Creates and adds a heightmap into maps. Returns map ID.

		:param name: Name of created map.
		:type name: :class:`str`
		:param txt: Texture to be added.
		:type txt: :class:`moderngl.Texture`
		:return: New map UUID string.
		:rtype: :class:`str`"""
		id = str(uuid.uuid4())
		self.maps[id] = Heightmap(name, txt)
		return id

	def releaseActive(self):
		"""Releases all temporary textures from the :attr:`active` list."""
		for i in self.active:
			if i:
				i.release()
		self.active = []
		
	def clear(self):
		"""Clears :attr:`info` and :attr:`error` messages."""
		self.running = False
		self.progress = 0.0
		self.iteration = 0
		self.info = []
		self.error = []
	
	def report(self, caller, callerName:str="Hydra"):
		"""Shows either stored error or info messages.

		:param caller: `Operation` calling this function.
		:param callerName: Message box title.
		:type callerName: :class:`str`"""
		if len(self.error) != 0:
			showMessage(";".join(self.error), title=callerName, icon="ERROR")
		if len(self.info) != 0:
			caller.report({"INFO"}, ";".join(self.info))
	
	def freeAll(self):
		"""Frees all allocated textures."""
		for i in self.maps.values():
			i.release()
		self.maps = {}
		self.releaseActive()

	def addMessage(self, message: str, error: bool=False):
		"""Adds an info message.

		:param message: Message to be added.
		:type message: :class:`str`"""
		if error:
			self.error.append(message)
		else:
			self.info.append(message)

#-------------------------------------------- Extra

def showMessage(message: str, title:str="Hydra", icon:str='INFO'):
	"""Displays a message as popup.

	:param message: Message to be shown.
	:type message: :class:`str`
	:param title: Popup title.
	:type title: :class:`str`
	:param icon: Blender icon ID for the popup.
	:type icon: :class:`str`"""
	draw = lambda s,_: s.layout.label(text=message)
	bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def getPreferences():
	"""Returns Hydra Blender preferences.

	:returns: Blender preferences for the Hydra addon."""
	return bpy.context.preferences.addons["Hydra"].preferences

_R_NUMBER: re.Pattern = re.compile(r"\d+$")
"""Ending number RegEx."""
def incrementLayer(name: str, default: str)->str:
	"""Increments given layer name.

	:param name: Layer name to be incremented.
	:type name: :class:`str`
	:param default: Default layer name if incrementation fails.
	:type default: :class:`str`
	:returns: Incremented layer name."""
	if g := _R_NUMBER.search(name):
		num = str(int(g.group(0))+1)
		return _R_NUMBER.sub(num, default)
	else:
		return default

_R_OWNER: re.Pattern = re.compile(r"HYD_(.+?)_\w+$")
"""Hydra naming convention RegEx. Groups original owner name."""
def getOwner(name: str, previewName: str)->str | None:
	"""Gets the original object, which generated the given name.

	:param name: Name, which was generated by other object.
	:type name: :class:`str`
	:param previewName: Name for a corresponding preview object.
	:type previewName: :class:`str`
	:returns: Name of the original object. `None` if not found or if `name` is a preview.
	:rtype: :class:`str` or :class:`None`"""
	if name == previewName:
		return None
	if m := _R_OWNER.match(name):
		return m.group(1)
	return None

#-------------------------------------------- Vars

data: HydraData = HydraData()
"""Global data variable for the whole project."""
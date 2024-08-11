"""Global data and common functions module. Also defines :class:`Heightmap` class."""

import moderngl as mgl
import bpy, bpy.types
from pathlib import Path

import uuid, re

class Heightmap:
	"""A wrapper around ModernGL textures."""
	def __init__(self, name: str, txt: mgl.Texture, logarithmic: bool=False):
		"""Constructor method.

		:param name: Display name of the stored texture.
		:type name: :class:`str`
		:param txt: Texture to wrap.
		:type txt: :class:`moderngl.Texture:`"""
		self.name = name
		self.texture = txt
		self.logarithmic = logarithmic
	
	def release(self)->None:
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

class ShaderBank:
	def __init__(self):
		"""Sets the GLSL files path."""
		self.source_path = Path(__file__).resolve().parent.joinpath("GLSL")

	def __getitem__(self, key: str)->mgl.ComputeShader:
		"""Lazy-loads and returns the specified compute shader.
		Raises `KeyError` if not found."""
		if key not in data._shaders_:
			path = self.source_path.joinpath(key + ".glsl")
			if path.exists():
				comp = path.read_text("utf-8")
				data._shaders_[key] = data.context.compute_shader(comp)
			else:
				raise KeyError(f"Shader '{key}' not found.")
		
		return data._shaders_[key]

class HydraData(object):
	"""Global data object. Stores all ModernGL resources, including the context."""

	def __init__(self):
		"""Constructor method."""

		self.context: mgl.Context = None
		"""Addon's ModernGL context. Attached to Blender's OpenGL context."""

		self._maps_: dict[str, Heightmap] = {}
		"""Heightmap dictionary. Uses UUID strings as keys."""
		self._graveyard_: list[tuple[str, Heightmap]] = []
		"""List of deleted maps for undo support."""

		self.programs: dict[str, mgl.Program] = {}
		"""Compiled ModernGL program list."""

		self.shaders: ShaderBank = ShaderBank()
		"""Lazy-loaded ModernGL compute shader dictionary."""

		self._shaders_: dict[str, mgl.ComputeShader] = {}
		"""Compiled ModernGL compute shader list."""
		
		self.last_preview: str | None = None
		"""Name of last previewed object."""

		self._info_: list[str] = []
		"""Info message list."""
		self._error_: list[str] = []
		"""Error message list."""
	
	def init_context(self):
		"""Creates and saves the attached ModernGL :attr:`context`."""
		self.context = mgl.get_context()	#standalone crashes blender; create_context doesn't work with wayland

	def has_map(self, id: str | None)->bool:
		"""Checks if map exists.

		:return: `True` if map exists in the :attr:`maps` list. `False` otherwise.
		:rtype: :class:`bool`"""
		return id in self._maps_ or any(hmid == id for hmid,_ in self._graveyard_)

	def get_map(self, id: str | None)->Heightmap | None:
		"""Returns map by ID. Returns `None` if not found."""
		if id in self._maps_:
			return self._maps_[id]
		elif any(hmid == id for hmid,_ in self._graveyard_):
			for i,(hmid,hm) in enumerate(self._graveyard_):
				if hmid == id:
					del self._graveyard_[i]
					# reinstate map
					self._maps_[hmid] = hm
					return hm
		else:
			return None


	def try_release_map(self, id: str | None):
		"""Release specified map. Does nothing on invalid `id`.

		:param id: Map ID.
		:type id: :class:`str` or :class:`None`"""
		if id in self._maps_:
			self._graveyard_.append((id, self._maps_[id]))
			if len(self._graveyard_) > get_preferences().history_length:
				self._graveyard_[0][1].release()
				del self._graveyard_[0]

			del self._maps_[id]
	
	def create_map(self, name: str, txt: mgl.Texture, logarithmic: bool=False, base: Heightmap|None=None)->str:
		"""Creates and adds a heightmap into maps. Returns map ID.

		:param name: Name of created map.
		:type name: :class:`str`
		:param txt: Texture to be added.
		:type txt: :class:`moderngl.Texture`
		:return: New map UUID string.
		:rtype: :class:`str`"""
		id = str(uuid.uuid4())
		logarithmic = base.logarithmic if base is not None else logarithmic
		self._maps_[id] = Heightmap(name, txt, logarithmic)
		return id
	
	def report(self, caller, callerName:str="Hydra")->None:
		"""Shows either stored error or info messages and clears them.

		:param caller: `Operation` calling this function.
		:type caller: :class:`set`
		:param callerName: Message box title.
		:type callerName: :class:`str`"""
		if len(self._error_) != 0:
			show_message(" ".join(self._error_), title=callerName, icon="ERROR")
		if len(self._info_) != 0:
			caller.report({"INFO"}, " ".join(self._info_))

		self._info_ = []
		self._error_ = []
	
	def free_all(self)->None:
		"""Frees all allocated maps."""
		for i in self._maps_.values():
			i.release()
		self._maps_ = {}

	def add_message(self, message: str, error: bool=False)->None:
		"""Adds an info message.

		:param message: Message to be added.
		:type message: :class:`str`
		:param error: `True` if message is an error.
		:type error: :class:`bool`"""
		if error:
			self._error_.append(message)
		else:
			self._info_.append(message)

	def release_shaders(self)->None:
		"""Releases all stored shaders."""
		for i in self._shaders_.values():
			i.release()
		self._shaders_ = {}

#-------------------------------------------- Extra

def show_message(message: str, title:str="Hydra", icon:str='INFO')->None:
	"""Displays a message as popup.

	:param message: Message to be shown.
	:type message: :class:`str`
	:param title: Popup title.
	:type title: :class:`str`
	:param icon: Blender icon ID for the popup.
	:type icon: :class:`str`"""
	draw = lambda s,_: s.layout.label(text=message)
	bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)

def get_preferences()->None:
	"""Returns Hydra Blender preferences.

	:returns: Blender preferences for the Hydra addon."""
	return bpy.context.preferences.addons["Hydra"].preferences

_R_NUMBER: re.Pattern = re.compile(r"\d+$")
"""Ending number RegEx."""
def increment_layer(name: str, default: str)->str:
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

_SPACE_OBJECT = "VIEW_3D"
_SPACE_IMAGE = "IMAGE_EDITOR"

#-------------------------------------------- Vars

data: HydraData = HydraData()
"""Global data variable for the whole project."""
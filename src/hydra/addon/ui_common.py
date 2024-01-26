import bpy, bpy.types
from Hydra import common

class HydraPanel(bpy.types.Panel):
	bl_region_type = 'UI'
	bl_category = "Hydra"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def is_space_type(cls, name: str)->bool:
		return cls.bl_space_type == name

class ImagePanel(HydraPanel):
	bl_space_type = 'IMAGE_EDITOR'

	def get_settings(self, ctx):
		return ctx.area.spaces.active.image.hydra_erosion

	def draw_size_fragment(self, container, ctx, settings):
		split = container.split(factor=0.5)
		split.label(text=f"Size:")
		split.label(text=f"{tuple(ctx.area.spaces.active.image.size)}")

	@classmethod
	def poll(cls, ctx):
		img = ctx.area.spaces.active.image
		if not img or tuple(img.size) == (0,0):
			return False
		return not img.hydra_erosion.is_generated

class ObjectPanel(HydraPanel):
	bl_space_type = 'VIEW_3D'
	bl_context = "objectmode"

	def get_settings(self, ctx):
		return ctx.object.hydra_erosion

	def draw_size_fragment(self, container, ctx, settings):
		if common.data.has_map(settings.map_base):
			split = container.split(factor=0.5)
			split.label(text=f"Size:")
			split.label(text=f"{tuple(settings.img_size)}")
		else:
			container.prop(settings, "img_size")

	@classmethod
	def poll(cls, ctx):
		ob = ctx.object
		if not ob:
			return
		if ob.hydra_erosion.is_generated:
			return False
		return ob.type == "MESH" and len(ob.data.vertices) != 0

#-------------------------------------------- Flow

class FlowPanel():
	bl_label = "Hydra - Flow"
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		col = self.layout.column()

		if self.is_space_type(common._SPACE_IMAGE):
			col.operator('hydra.flow_img', text="Generate Flowmap", icon="MATFLUID")
		else:
			col.operator('hydra.flow', text="Generate Flowmap", icon="MATFLUID")

		col.separator()
		self.draw_size_fragment(col, ctx, hyd)

		col.separator()
		box = col.box()
		box.prop(hyd, "flow_contrast", slider=True)
		box.prop(hyd, "interpolate_flow")
		split = box.split()
		split.label(text="Chunk size")
		split.prop(hyd, "flow_subdiv", text="")
		
		col.separator()
		col.label(text="Particle settings")
		box = col.box()
		box.prop(hyd, "part_lifetime")
		box.prop(hyd, "part_acceleration", slider=True)
		box.prop(hyd, "part_drag", slider=True)

#-------------------------------------------- Exports
	
def get_exports():
	return []
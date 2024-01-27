import bpy, bpy.types
from Hydra import common

class HydraPanel(bpy.types.Panel):
	bl_region_type = 'UI'
	bl_category = "Hydra"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def is_space_type(cls, name: str)->bool:
		return cls.bl_space_type == name
	
	@classmethod
	def get_op_name(cls, name: str)->str:
		if cls.is_space_type(common._SPACE_IMAGE):
			return f"hydra.{name}_img"
		return f"hydra.{name}"

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

#-------------------------------------------- Erosion

class ErosionPanel():
	bl_label = "Hydra - Erosion"
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout.column()
		if hyd.out_color and hyd.color_src not in bpy.data.images:
			box = col.box()
			box.operator(self.get_op_name("erode"), text="No color source", icon="RNDCURVE")
			box.enabled = False
		else:
			col.operator(self.get_op_name("erode"), text="Erode", icon="RNDCURVE")

		self.draw_size_fragment(col.box(), ctx, hyd)

		col.prop(hyd, "erosion_solver", text="Solver")

#-------------------------------------------- Flow

class FlowPanel():
	bl_label = "Hydra - Flow"
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		col = self.layout.column()

		col.operator(self.get_op_name("flow"), text="Generate Flowmap", icon="MATFLUID")

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

#-------------------------------------------- Thermal

class ThermalPanel():
	bl_label = "Hydra - Thermal"
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout.column()
		col.operator(self.get_op_name("thermal"), text="Erode", icon="RNDCURVE")

		self.draw_size_fragment(col.box(), ctx, hyd)

		col.separator()
		col.label(text="Erosion settings")

		box = col.box()
		box.prop(hyd, "thermal_iter_num")
		box.prop(hyd, "thermal_strength", slider=True)
		box.prop(hyd, "thermal_angle", slider=True)
		split = box.split(factor=0.4)
		split.label(text="Direction: ")
		split.prop(hyd, "thermal_solver", text="")

#-------------------------------------------- Exports
	
def get_exports():
	return []
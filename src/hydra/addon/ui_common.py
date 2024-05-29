import bpy, bpy.types
from Hydra import common
from Hydra.utils import nav

#-------------------------------------------- Base classes

class HydraPanel(bpy.types.Panel):
	bl_region_type = 'UI'
	bl_category = "Hydra"
	bl_options = {'DEFAULT_CLOSED'}

	@classmethod
	def is_space_type(cls, name: str)->bool:
		return cls.bl_space_type == name
	
	@classmethod
	def get_target(cls, ctx):
		if cls.is_space_type(common._SPACE_IMAGE):
			return ctx.area.spaces.active.image
		else:
			return ctx.object
		
	def draw_nav_fragment(self, container, name, label):
		if name in bpy.data.images:
			split = container.split()
			split.label(text=label)
			split.operator('hydra.nav_img', text="", icon="TRIA_RIGHT_BAR").target = name

class ImagePanel(HydraPanel):
	bl_space_type = 'IMAGE_EDITOR'

	@classmethod
	def get_settings(cls, ctx):
		img = ctx.area.spaces.active.image
		if not img or tuple(img.size) == (0,0):
			return None
		return img.hydra_erosion

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

	@classmethod
	def get_settings(cls, ctx):
		ob = ctx.object
		if not ob:
			return None
		
		try:
			return ob.hydra_erosion
		except AttributeError:
			return None

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
			return False
		if ob.type != "MESH" or len(ob.data.vertices) == 0:
			return False
		
		try:
			return not ob.hydra_erosion.is_generated
		except AttributeError:
			return False

#-------------------------------------------- Erosion

class ErosionPanel():
	bl_label = "Hydra - Erosion"
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout.column()

		if hyd.out_color and hyd.color_src not in bpy.data.images:
			box = col.box()
			box.operator("hydra.erode", text="No color source", icon="RNDCURVE")
			box.enabled = False
		else:
			grid = col.grid_flow(columns=1, align=True)
			grid.operator("hydra.erode", text="Erode", icon="RNDCURVE").apply = False
			if common.data.has_map(hyd.map_result):
				grid.operator("hydra.erode", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd)

		col.prop(hyd, "erosion_solver", text="Solver")

		if hyd.erosion_solver == "particle":
			col.separator()
			col.label(text="Simulation resolution:")
			col.prop(hyd, "erosion_subres", text="", slider=True)

#-------------------------------------------- Thermal

class ThermalPanel():
	bl_label = "Hydra - Thermal"
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout.column()

		grid = col.grid_flow(columns=1, align=True)
		grid.operator("hydra.thermal", text="Erode", icon="RNDCURVE").apply = False
		if common.data.has_map(hyd.map_result):
			grid.operator("hydra.thermal", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd)

#-------------------------------------------- Snow

class SnowPanel():
	bl_label = "Hydra - Snow"
	bl_description = "Erosion settings for snow simulation"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout.column()

		grid = col.grid_flow(columns=1, align=True)
		
		grid.operator("hydra.snow", text="Simulate", icon="RNDCURVE")
		if hyd.snow_output != "texture" and common.data.has_map(hyd.map_result):
			grid.operator("hydra.snow", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd)

		col.separator()
		split = col.split(factor=0.4)
		split.label(text="Output: ")
		split.prop(hyd, "snow_output", text="")

		col.separator()
		col.label(text="Erosion settings")

		box = col.box()
		box.prop(hyd, "snow_add", slider=True)
		box.prop(hyd, "mei_scale")

		box = col.box()
		box.prop(hyd, "snow_iter_num")
		box.prop(hyd, "snow_angle", slider=True)


#-------------------------------------------- Flow

class FlowPanel():
	bl_label = "Hydra - Flow"
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		col = self.layout.column()

		col.operator("hydra.flow", text="Generate Flowmap", icon="MATFLUID")

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

#-------------------------------------------- Heightmap System

class HeightmapSystemPanel():
	bl_label = "Heightmaps"
	bl_options = set()

	def draw(self, ctx):
		col = self.layout.column()
		hyd = self.get_settings(ctx)
		target = self.get_target(ctx)

		has_any = False

		if common.data.has_map(hyd.map_base):
			has_any = True
			col.operator('hydra.hm_clear', icon="CANCEL")
			col.separator()

		if common.data.has_map(hyd.map_result):
			has_any = True
			name = common.data.get_map(hyd.map_result).name

			if isinstance(target, bpy.types.Image):
				box = col.box()
				split = box.split(factor=0.5)
				split.label(text="Current:")
				split.label(text=name)
				cols = box.column_flow(columns=3, align=True)
				cols.operator('hydra.hm_preview', text="", icon="HIDE_OFF")
				cols.operator('hydra.hm_move', text="", icon="TRIA_DOWN_BAR")
				cols.operator('hydra.hm_delete', text="", icon="PANEL_CLOSE")

				cols = box.column_flow(columns=2, align=True)
				op = cols.operator('hydra.hm_apply_img', text="", icon="IMAGE_DATA")
				op.save_target = hyd.map_result
				op.name = f"HYD_{target.name}_Eroded"
				cols.operator('hydra.override_original', text="", icon="IMAGE_REFERENCE")
			else:
				box = col.box()
				split = box.split(factor=0.5)
				split.label(text="Result:")
				split.label(text=name)
				cols = box.column_flow(columns=3, align=True)
				if common.data.lastPreview == target.name:
					cols.operator('hydra.hm_remove_preview', text="", icon="HIDE_ON")
				else:
					cols.operator('hydra.hm_preview', text="", icon="HIDE_OFF")
				cols.operator('hydra.hm_move', text="", icon="TRIA_DOWN_BAR")
				cols.operator('hydra.hm_delete', text="", icon="PANEL_CLOSE")

				grid = box.grid_flow(columns=1, align=True)

				cols = grid.column_flow(columns=2, align=True)
				op = cols.operator('hydra.hm_apply_img', text="", icon="IMAGE_DATA")
				op.save_target = hyd.map_result
				op.name = f"HYD_{target.name}_Eroded"

				cols.operator('hydra.hm_apply_geo', text="", icon="GEOMETRY_NODES")

				cols = grid.column_flow(columns=3, align=True)
				cols.operator('hydra.hm_apply_mod', text="", icon="MOD_DISPLACE")
				cols.operator('hydra.hm_apply_disp', text="", icon="RNDCURVE")
				cols.operator('hydra.hm_apply_bump', text="", icon="MOD_NOISE")
				
				m = next((m for m in target.modifiers if m.name.startswith("HYD_")), None)
				if m:
					if m.type == "DISPLACE":
						cols = box.column_flow(columns=2, align=True)
						cols.operator('hydra.hm_merge', text="", icon="MESH_DATA")
						cols.operator('hydra.hm_merge_shape', text="", icon="SHAPEKEY_DATA")
					else:
						box.operator('hydra.hm_merge', text="", icon="MESH_DATA")

		if common.data.has_map(hyd.map_source):
			has_any = True
			name = common.data.get_map(hyd.map_source).name
			box = col.box()
			split = box.split(factor=0.5)
			split.label(text="Source:")
			split.label(text=name)
			cols = box.column_flow(columns=3, align=True)
			cols.operator('hydra.hm_force_reload', text="", icon="GRAPH")
			cols.operator('hydra.hm_move_back', text="", icon="TRIA_UP_BAR")
			cols.operator('hydra.hm_reload', text="", icon="FILE_REFRESH")

		if not has_any:
			col.label(text="No maps have been cached yet.")

#-------------------------------------------- Subpanels

class ThermalSettingsPanel():
	bl_label = "Erosion settings"
	bl_options = set()

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		col = self.layout.column()

		box = col.box()
		box.prop(hyd, "thermal_iter_num")
		box.prop(hyd, "thermal_strength", slider=True)
		box.prop(hyd, "thermal_angle", slider=True)
		
		split = box.split(factor=0.4)
		split.label(text="Direction: ")
		split.prop(hyd, "thermal_solver", text="")

class ThermalAdvancedPanel():
	bl_label = "Advanced"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		col = self.layout.column()

		box = col.box()
		box.prop(hyd, "part_maxjump")
		box.prop(hyd, "thermal_stride")
		box.prop(hyd, "thermal_stride_grad")

class ErosionSettingsPanel(bpy.types.Panel):
	"""Subpanel for water erosion particle settings."""
	bl_label = "Erosion settings"
	bl_options = set()

	def draw(self, ctx):
		p = self.layout.box()
		hyd = self.get_settings(ctx)
		if hyd.erosion_solver == "particle":
			p.prop(hyd, "part_iter_num")
			p.prop(hyd, "part_lifetime")
			p.prop(hyd, "part_acceleration", slider=True)
			p.prop(hyd, "part_drag", slider=True)
			
			p.prop(hyd, "part_fineness", slider=True)
			p.prop(hyd, "part_deposition", slider=True)
			p.prop(hyd, "part_capacity", slider=True)
		else:
			split = p.split(factor=0.4)
			split.label(text="Direction: ")
			split.prop(hyd, "mei_direction", text="")

			p.prop(hyd, "mei_iter_num")
			p.prop(hyd, "mei_scale")
			p.prop(hyd, "mei_dt")
			p.prop(hyd, "mei_rain", slider=True)
			p.prop(hyd, "mei_evaporation", slider=True)
			p.prop(hyd, "mei_capacity", slider=True)
			p.prop(hyd, "mei_deposition", slider=True)
			p.prop(hyd, "mei_erosion", slider=True)
			p.prop(hyd, "mei_min_alpha")

class ErosionExtrasPanel():
	"""Subpanel for water erosion extra settings."""
	bl_label = "Extras"

	@classmethod
	def poll(cls, ctx):
		return cls.get_settings(ctx).erosion_solver == "particle"

	def draw(self, ctx):
		p = self.layout.box()
		target = self.get_target(ctx)
		hyd = self.get_settings(ctx)

		p.prop(hyd, "out_color")
		if (hyd.out_color):
			p.prop_search(hyd, "color_src", bpy.data, "images")
			p.prop(hyd, "interpolate_color")
			p.prop(hyd, "color_mixing", slider=True)

		p.prop(hyd, "out_depth")
		if (hyd.out_depth):
			p.prop(hyd, "depth_contrast", slider=True)

		p.prop(hyd, "out_sediment")
		if (hyd.out_sediment):
			p.prop(hyd, "sed_contrast", slider=True)
		
		self.draw_nav_fragment(p, f"HYD_{target.name}_Color", "Color")
		self.draw_nav_fragment(p, f"HYD_{target.name}_Depth", "Depth")
		self.draw_nav_fragment(p, f"HYD_{target.name}_Sediment", "Sediment")

class ErosionAdvancedPanel():
	"""Subpanel for water erosion advanced settings."""
	bl_label = "Advanced"

	@classmethod
	def poll(cls, ctx):
		return cls.get_settings(ctx).erosion_solver == "particle"
	
	def draw(self, ctx):
		p = self.layout.box()
		hyd = ctx.object.hydra_erosion
		p.prop(hyd, "interpolate_erosion")
		split = p.split()
		split.label(text="Chunk size")
		split.prop(hyd, "part_subdiv", text="")
		p.prop(hyd, "part_maxjump")

#-------------------------------------------- Info
		
class InfoPanel():
	bl_label = "Hydra - Info"

	def draw(self, ctx):
		col = self.layout.column()

		col.separator()
		col.operator('hydra.decouple', icon="DUPLICATE")

		target = self.get_target(ctx)

		if owner := nav.get_owner(target.name):
			col.separator()
			col.label(text="Owner:")
			box = col.box()
			split = box.split()
			split.label(text=owner)
			if owner in bpy.data.objects:
				split.operator('hydra.nav_obj', text="", icon="TRIA_RIGHT_BAR").target = owner
			elif owner in bpy.data.images:
				split.operator('hydra.nav_img', text="", icon="TRIA_RIGHT_BAR").target = owner
			else:
				split.label(text="Not found")

	@classmethod
	def poll(cls, ctx):
		hyd = cls.get_settings(ctx)
		if not hyd:
			return False
		return hyd.is_generated

#-------------------------------------------- Exports
	
def get_exports():
	return []

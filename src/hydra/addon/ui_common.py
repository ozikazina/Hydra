"""Module for common UI panels used in the Hydra addon."""

import bpy, bpy.types
from Hydra import common
from Hydra.utils import nav, apply
import math

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

	def draw_size_fragment(self, container, ctx, settings, draw_subres:bool = False):
		g = container.grid_flow(columns=1, align=True)
		split = g.split(factor=0.5)
		split.label(text=f"Resolution:")
		r = split.row()
		size = ctx.area.spaces.active.image.size
		r.label(text=f"({size[0]}, {size[1]}) px")
		r.alignment = "RIGHT"
		split.enabled = False

		if draw_subres:
			g.prop(settings, "erosion_subres", text="Simulation")

	def draw_tiling_fragment(self, container, hyd):
		if hyd.advanced:
			container.prop(hyd, "tiling")

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

	def draw_size_fragment(self, container, ctx, settings, draw_subres:bool = False):
		g = container.grid_flow(columns=1, align=True)

		if common.data.has_map(settings.map_base):
			split = g.split(factor=0.42)
			split.label(text=f"Resolution:")
			c = split.row()
			c.label(text=f"({settings.img_size[0]}, {settings.img_size[1]}) px")
			c.alignment = "RIGHT"
			c.enabled = False
		else:
			split = g.split(factor=0.42)
			split.label(text=f"Resolution:")
			if common.get_preferences().direct_resolution:
				g.prop(settings, "x_img_size_x", text="X")
				g.prop(settings, "x_img_size_y", text="Y")
			else:
				c = split.row()
				if settings.tiling == "planet":
					c.label(text=f"({2 * settings.img_size[1]}, {settings.img_size[1]}) px")
				else:
					c.label(text=f"({settings.img_size[0]}, {settings.img_size[1]}) px")

				c.enabled=False
				c.alignment = "RIGHT"
				g.prop(settings, "x_img_res", text="Heightmap")

		if draw_subres:
			g.prop(settings, "erosion_subres", text="Simulation")

	def draw_tiling_fragment(self, container, hyd):
		if hyd.advanced:
			if common.data.has_map(hyd.map_base):
				container = container.row()
				container.enabled = False

			container.prop(hyd, "tiling")

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
		
		col = self.layout

		grid = col.grid_flow(columns=1, align=True)
		grid.operator("hydra.erode", text="Erode", icon="RNDCURVE").apply = False
		if common.data.has_map(hyd.map_result):
			grid.operator("hydra.erode", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd, draw_subres=True)

		col.prop(hyd, "erosion_solver", text="Solver")
		col.prop(hyd, "advanced")

		self.draw_tiling_fragment(col, hyd)


#-------------------------------------------- Thermal

class ThermalPanel():
	bl_label = "Hydra - Thermal"
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout

		grid = col.grid_flow(columns=1, align=True)
		grid.operator("hydra.thermal", text="Erode", icon="RNDCURVE").apply = False
		if common.data.has_map(hyd.map_result):
			grid.operator("hydra.thermal", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd)

		col.prop(hyd, "advanced")

		self.draw_tiling_fragment(col, hyd)


#-------------------------------------------- Snow

class SnowPanel():
	bl_label = "Hydra - Snow"
	bl_description = "Erosion settings for snow simulation"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		
		col = self.layout

		grid = col.grid_flow(columns=1, align=True)
		
		grid.operator("hydra.snow", text="Simulate", icon="RNDCURVE").apply = False
		if hyd.snow_output != "texture" and common.data.has_map(hyd.map_result):
			grid.operator("hydra.snow", text="Set & Continue", icon="ANIM").apply = True

		self.draw_size_fragment(col.box(), ctx, hyd)

		split = col.split(factor=0.4)
		split.label(text="Output: ")
		split.prop(hyd, "snow_output", text="")

		col.prop(hyd, "advanced")

		self.draw_tiling_fragment(col, hyd)

		col.separator()
		col.label(text="Erosion settings")

		col.prop(hyd, "snow_add", slider=True)
		col.prop(hyd, "snow_iter_num")
		col.prop(hyd, "snow_angle", slider=True)


#-------------------------------------------- Flow

class ExtrasPanel():
	bl_label = "Hydra - Extras"
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		target = self.get_target(ctx)
		p = self.layout

		p.prop(hyd, "extras_type")
		p.separator()

		if hyd.extras_type == "flow":
			p.operator("hydra.flow", text="Generate Flowmap", icon="MATFLUID")
		elif hyd.extras_type == "color":
			if hyd.color_src in bpy.data.images:
				p.operator("hydra.color", text="Transport Color", icon="COLOR")
			else:
				box = p.box()
				box.operator("hydra.color", text="No color source", icon="COLOR")
				box.enabled = False
		
		self.draw_size_fragment(p.box(), ctx, hyd)

		if hyd.extras_type == "flow":
			p.label(text="Settings:")
			p.prop(hyd, "flow_brightness", slider=True)
			
			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "flow_iter_num")
			g.prop(hyd, "part_lifetime")
			g.prop(hyd, "part_drag", slider=True)
		elif hyd.extras_type == "color":
			p.prop(hyd, "color_solver")
			p.prop_search(hyd, "color_src", bpy.data, "images")
			
			p.prop(hyd, "advanced")
			self.draw_tiling_fragment(p, hyd)

			p.label(text="Settings:")
			p.prop(hyd, "color_mixing", slider=True)

			if hyd.color_solver == "particle":
				g = p.grid_flow(columns=1, align=True)
				g.prop(hyd, "color_iter_num")
				g.prop(hyd, "color_lifetime")

				g = p.grid_flow(columns=1, align=True)
				g.prop(hyd, "color_acceleration", slider=True)
				if hyd.advanced:
					g.prop(hyd, "part_lateral_acceleration")
				g.prop(hyd, "color_detail", slider=True)

			elif hyd.color_solver == "pipe":
				p.prop(hyd, "color_iter_num")

				g = p.grid_flow(columns=1, align=True)
				g.prop(hyd, "color_detail", slider=True)
				g.prop(hyd, "color_speed", slider=True)

				g = p.grid_flow(columns=1, align=True)
				g.prop(hyd, "color_rain", slider=True)
				g.prop(hyd, "color_evaporation")

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
			col.operator('hydra.hm_clear', icon="CANCEL", text="Clear")
			col.separator()

		if common.data.has_map(hyd.map_result):
			has_any = True
			name = common.data.get_map(hyd.map_result).name

			if isinstance(target, bpy.types.Image):
				box = col.box()
				split = box.split(factor=0.5)
				split.label(text="Result:")
				split.label(text=name)
				cols = box.column_flow(columns=3, align=True)
				if apply.PREVIEW_IMG_NAME in bpy.data.objects or apply.PREVIEW_IMG_NAME in bpy.data.images:
					cols.operator('hydra.hm_remove_preview', text="", icon="HIDE_ON")
				else:
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

class ErosionSettingsPanel(bpy.types.Panel):
	"""Subpanel for water erosion particle settings."""
	bl_label = "Settings"
	bl_options = set()

	def draw(self, ctx):
		p = self.layout
		hyd = self.get_settings(ctx)

		if hyd.erosion_solver == "particle":
			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "part_iter_num")
			g.prop(hyd, "part_lifetime")

			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "part_fineness", slider=True)
			g.prop(hyd, "part_deposition", slider=True)
			g.prop(hyd, "part_capacity", slider=True)

			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "part_acceleration", slider=True)
			if hyd.advanced:
				g.prop(hyd, "part_lateral_acceleration")
			g.prop(hyd, "part_drag", slider=True)

			if hyd.advanced:
				p.prop(hyd, "part_max_change")

				box = p.box()
				box.prop_search(hyd, "erosion_hardness_src", bpy.data, "images")
				box.prop(hyd, "erosion_invert_hardness")
		else:
			p.prop(hyd, "mei_iter_num")

			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "mei_hardness", slider=True)
			if hyd.advanced:
				g.prop(hyd, "mei_deposition", slider=True)
			g.prop(hyd, "mei_capacity", slider=True)

			g = p.grid_flow(columns=1, align=True)
			g.prop(hyd, "mei_rain", slider=True)
			if hyd.advanced:
				g.prop(hyd, "mei_max_depth")

				# p.prop(hyd, "mei_randomize")

				box = p.box()
				box.prop_search(hyd, "erosion_hardness_src", bpy.data, "images")
				box.prop(hyd, "erosion_invert_hardness")
				box.prop_search(hyd, "mei_water_src", bpy.data, "images")


class ThermalSettingsPanel():
	bl_label = "Settings"
	bl_options = set()

	def draw(self, ctx):
		hyd = self.get_settings(ctx)
		p = self.layout
		
		if hyd.advanced:
			split = p.split(factor=0.4)
			split.label(text="Direction: ")
			split.prop(hyd, "thermal_solver", text="")
			p.separator()

		p.prop(hyd, "thermal_iter_num")
		p.prop(hyd, "thermal_strength", slider=True)
		p.prop(hyd, "thermal_angle", slider=True)

		if hyd.advanced:
			p.prop(hyd, "thermal_stride")
			p.prop(hyd, "thermal_stride_grad")


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

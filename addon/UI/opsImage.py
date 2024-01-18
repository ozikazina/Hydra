"""Module responsible for image UI elements and operators."""

import bpy
from bpy.props import BoolProperty

from Hydra import common, startup
from Hydra.sim import thermal, flow, erosion, heightmap
from Hydra.utils import nav, apply, model

class DefaultPanel:
	"""Default panel defining a poll method for other UI elements."""
	@classmethod
	def poll(cls, ctx):
		"""Poll function to hide panel for invalid objects."""
		img = ctx.area.spaces.active.image
		if startup.invalid or not img or tuple(img.size) == (0,0):
			return False
		return not img.hydra_erosion.is_generated

class DefaultHeightmapPanel:
	"""Heightmap subpanel for displaying the heightmap stack."""
	def draw(self, ctx):
		container = self.layout.column()
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
		hasAny = False

		if common.data.hasMap(hyd.map_base):
			hasAny = True
			container.operator('hydra.hmclear', icon="CANCEL").useImage = True
			container.separator()

		if common.data.hasMap(hyd.map_current):
			hasAny = True
			name = common.data.maps[hyd.map_current].name
			box = container.box()
			split = box.split(factor=0.5)
			split.label(text="Current:")
			split.label(text=name)
			cols = box.column_flow(columns=3, align=True)
			cols.operator('hydra.hmpreview', text="", icon="HIDE_OFF").target = hyd.map_current
			cols.operator('hydra.hmmove', text="", icon="TRIA_DOWN_BAR").useImage = True
			cols.operator('hydra.hmdelete', text="", icon="PANEL_CLOSE").useImage = True
			op = box.operator('hydra.hmapplyimg', text="", icon="IMAGE_DATA")
			op.save_target = hyd.map_current
			op.name = f"HYD_{act.name}_Eroded"

		if common.data.hasMap(hyd.map_source):
			hasAny = True
			name = common.data.maps[hyd.map_source].name
			box = container.box()
			split = box.split(factor=0.5)
			split.label(text="Source:")
			split.label(text=name)
			cols = box.column_flow(columns=3, align=True)
			cols.operator('hydra.hmforcereload', text="", icon="RNDCURVE").useImage = True
			cols.operator('hydra.hmback', text="", icon="TRIA_UP_BAR").useImage = True
			cols.operator('hydra.hmreload', text="", icon="FILE_REFRESH").useImage = True
		
		if not hasAny:
			container.label(text="No maps have been cached yet.")

def fragmentSize(container):
	"""UI function for displaying size info.
	
	:param container: Containing UI element."""
	split = container.split(factor=0.5)
	split.label(text=f"Size:")
	split.label(text=f"{tuple(bpy.context.area.spaces.active.image.size)}")

def fragmentNav(container, name:str, label:str):
	"""UI function for displaying a navigation button.
	
	:param container: Containing UI element.
	:param name: Navigation target name.
	:type name: :class:`str`
	:param label: Display label.
	:type label: :class:`str`"""
	if name in bpy.data.images:
		split = container.split()
		split.label(text=f"{label}:")
		split.operator('hydra.nav', text="", icon="IMAGE_DATA").target = name

#-------------------------------------------- Flow

class FlowPanel(bpy.types.Panel, DefaultPanel):
	"""Panel for flowmap generation."""
	bl_category = "Hydra"
	bl_label = "Hydra - Flow"
	bl_idname = "HYDRA_PT_imgflowpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion

		col = self.layout.column()
		col.operator('hydra.imggenflow', text="Generate Flowmap", icon="MATFLUID")

		col.separator()
		fragmentSize(col.box())
		
		fragmentNav(col, f"HYD_{img.name}_Flow", "Flow")

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

class FlowOp(bpy.types.Operator):
	"""Flowmap generation operator."""
	bl_idname = "hydra.imggenflow"
	bl_label = "Generate Flow"
	bl_description = "Generates a map of flow concentration using particle erosion. Uses eroded heightmaps, if they exist"
	bl_options = {'REGISTER'}
	
	def invoke(self, ctx, event):
		common.data.clear()
		img = ctx.area.spaces.active.image
		img.hydra_erosion.img_size = img.size
		img = flow.genFlow(img)
		nav.gotoImage(img)
		self.report({"INFO"}, f"Successfuly created image: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Erosion

class ErodePanel(bpy.types.Panel, DefaultPanel):
	"""Panel for water erosion."""
	bl_category = "Hydra"
	bl_label = "Hydra - Erosion"
	bl_idname = "HYDRA_PT_imgerodepanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		layout = self.layout
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
		
		main = layout.column()
		
		if hyd.out_color and hyd.color_src not in bpy.data.images:
			box = main.box()
			box.operator('hydra.imgerode', text="No color source", icon="RNDCURVE")
			box.enabled = False
		else:
			main.operator('hydra.imgerode', text="Erode", icon="RNDCURVE")
		
		fragmentSize(main.box())

class ErodeHeightPanel(bpy.types.Panel, DefaultHeightmapPanel):
	"""Subpanel for water erosion heightmap stack. Uses :class:`DefaultHeightmapPanel`"""
	bl_label = "Heightmaps"
	bl_parent_id = "HYDRA_PT_imgerodepanel"
	bl_idname = "HYDRA_PT_imgerodeheightpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"

class ErodeExtraPanel(bpy.types.Panel):
	"""Subpanel for water erosion extra settings."""
	bl_label = "Extra"
	bl_parent_id = "HYDRA_PT_imgerodepanel"
	bl_idname = "HYDRA_PT_imgerodeextrapanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		p = self.layout.box()
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
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
		
		fragmentNav(p, f"HYD_{act.name}_Color", "Color")
		fragmentNav(p, f"HYD_{act.name}_Depth", "Depth")
		fragmentNav(p, f"HYD_{act.name}_Sediment", "Sediment")

class ErodeParticlePanel(bpy.types.Panel):
	"""Subpanel for water erosion particle settings."""
	bl_label = "Particle settings"
	bl_parent_id = "HYDRA_PT_imgerodepanel"
	bl_idname = "HYDRA_PT_imgerodepartpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"

	def draw(self, ctx):
		p = self.layout.box()
		hyd = ctx.area.spaces.active.image.hydra_erosion
		p.prop(hyd, "part_iter_num")
		p.prop(hyd, "part_lifetime")
		p.prop(hyd, "part_acceleration", slider=True)
		p.prop(hyd, "part_drag", slider=True)
		
		p.prop(hyd, "part_fineness", slider=True)
		p.prop(hyd, "part_deposition", slider=True)
		p.prop(hyd, "part_capacity", slider=True)

class ErodeAdvancedPanel(bpy.types.Panel):
	"""Subpanel for water erosion advanced settings."""
	bl_label = "Advanced"
	bl_parent_id = "HYDRA_PT_imgerodepanel"
	bl_idname = "HYDRA_PT_imgerodeadvpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		p = self.layout.box()
		hyd = ctx.area.spaces.active.image.hydra_erosion
		p.prop(hyd, "interpolate_erosion")
		split = p.split()
		split.label(text="Chunk size")
		split.prop(hyd, "part_subdiv", text="")
		p.prop(hyd, "part_maxjump")

class ErodeOp(bpy.types.Operator):
	"""Water erosion operator."""
	bl_idname = "hydra.imgerode"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion
		data = common.data
		data.clear()
		data.running = True
		
		erosion.erosionPrepare(img)
		erosion.erosionRun(img)
		_ = erosion.erosionFinish(img)

		img = apply.addImagePreview(data.maps[hyd.map_current].texture)
		nav.gotoImage(img)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Thermal

class ThermalPanel(bpy.types.Panel, DefaultPanel):
	"""Panel for thermal erosion."""
	bl_category = "Hydra"
	bl_label = "Hydra - Thermal"
	bl_idname = "HYDRA_PT_imgthermalpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
		
		col = self.layout.column()
		box = col.box()
		box.operator('hydra.imgthermal', text="Erode", icon="RNDCURVE")

		fragmentSize(col.box())

		col.separator()
		col.label(text="Erosion settings")

		box = col.box()
		box.prop(hyd, "thermal_iter_num")
		box.prop(hyd, "thermal_strength", slider=True)
		box.prop(hyd, "thermal_angle", slider=True)
		split = box.split(factor=0.4)
		split.label(text="Direction: ")
		split.prop(hyd, "thermal_solver", text="")

class ThermalHeightPanel(bpy.types.Panel, DefaultHeightmapPanel):
	"""Subpanel for thermal erosion heightmap stack. Uses :class:`DefaultHeightmapPanel`."""
	bl_label = "Heightmaps"
	bl_parent_id = "HYDRA_PT_imgthermalpanel"
	bl_idname = "HYDRA_PT_imgThermalHeightPanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"

class ThermalOp(bpy.types.Operator):
	"""Thermal erosion operator."""
	bl_idname = "hydra.imgthermal"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		data.clear()
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion

		thermal.thermalPrepare(img)
		thermal.thermalRun(img)
		thermal.thermalFinish(img)

		img = apply.addImagePreview(data.maps[hyd.map_current].texture)
		nav.gotoImage(img)
		data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Normalize

class CleanupPanel(bpy.types.Panel):
	"""Panel for cleanup operations. Uses Object cleanup operator, as they are the same."""
	bl_category = "Hydra"
	bl_label = "Hydra - Cleanup"
	bl_idname = "HYDRA_PT_imgcleanpanel"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		col = self.layout.column()
		col.operator('hydra.clean', text="Clear cache", icon="SHADING_BBOX")
	
	@classmethod
	def poll(cls, ctx):
		return not startup.invalid


class InfoPanel(bpy.types.Panel):
	"""Image info panel."""
	bl_category = "Hydra"
	bl_label = "Hydra - Info"
	bl_idname = "HYDRA_PT_imginfo"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		img = ctx.area.spaces.active.image
		col = self.layout.column()
		fragmentSize(col.box())

		col.separator()
		col.operator('hydra.instantiate', icon="DUPLICATE")

		if owner := common.getOwner(img.name, apply.P_VIEW_NAME):
			if owner in bpy.data.objects:
				col.separator()
				col.label(text="Owner:")
				box = col.box()
				split = box.split()
				split.label(text=owner)
				op = split.operator('hydra.nav', text="", icon="IMAGE_DATA")
				op.target = owner
				op.object = True
			elif owner in bpy.data.images:
				col.separator()
				col.label(text="Original:")
				box = col.box()
				split = box.split()
				split.label(text=owner)
				split.operator('hydra.nav', text="", icon="IMAGE_DATA").target = owner
	
	@classmethod
	def poll(cls, ctx):
		img = ctx.area.spaces.active.image
		if startup.invalid or not img:
			return False
		return img.hydra_erosion.is_generated

#-------------------------------------------- Generate

class LandscapePanel(bpy.types.Panel, DefaultPanel):
	"""Panel for landscape generation."""
	bl_category = "Hydra"
	bl_label = "Hydra - Generate"
	bl_idname = "HYDRA_PT_imggenerate"
	bl_space_type = "IMAGE_EDITOR"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
		
		col = self.layout.column()
		col.prop(hyd, "gen_subscale")
		col.operator('hydra.landscape', text="Generate", icon="RNDCURVE")


class LandscapeOp(bpy.types.Operator):
	"""Landscape generation operator."""
	bl_idname = "hydra.landscape"
	bl_label = "Generate"
	bl_description = "Generate a landscape using this heightmap"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		img = ctx.area.spaces.active.image
		hyd = img.hydra_erosion

		if not data.hasMap(hyd.map_base):
			heightmap.prepareHeightmap(img)
		
		txt = data.maps[hyd.map_base].texture
		obj = model.createLandscape(txt, img.name, subscale=hyd.gen_subscale)
		apply.configureLandscape(obj, txt)
		nav.gotoObject(obj)
		return {'FINISHED'}

#-------------------------------------------- Exports
	
EXPORTS = (
	InfoPanel,
	ErodeOp,
	ErodePanel,
	ErodeParticlePanel,
	ErodeHeightPanel,
	ErodeExtraPanel,
	ErodeAdvancedPanel,
	ThermalOp,
	ThermalPanel,
	ThermalHeightPanel,
	FlowOp,
	FlowPanel,
	LandscapeOp,
	LandscapePanel,
	CleanupPanel
)
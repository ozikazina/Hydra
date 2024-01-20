"""Module responsible for object UI elements and operators."""

import bpy, bpy.types

from Hydra import common, startup
from Hydra.sim import erosion, flow, heightmap, thermal
from Hydra.utils import nav, texture, apply

class DefaultPanel:
	"""Default panel defining a poll method for other UI elements."""
	@classmethod
	def poll(cls, ctx):
		"""Poll function to hide panel for invalid objects."""
		if startup.invalid:
			return False
		ob = bpy.context.active_object
		if not ob:
			return
		if ob.hydra_erosion.is_generated:
			return False
		return ob.type == "MESH" and len(ob.data.vertices) != 0

class DefaultHeightmapPanel:
	"""Heightmap subpanel for displaying the heightmap stack."""
	def draw(self, ctx):
		container = self.layout.column()
		act = ctx.object
		hyd = act.hydra_erosion
		hasAny = False

		if common.data.hasMap(hyd.map_base):
			hasAny = True
			container.operator('hydra.hmclear', icon="CANCEL")
			container.separator()

		if common.data.hasMap(hyd.map_current):
			hasAny = True
			name = common.data.maps[hyd.map_current].name
			box = container.box()
			split = box.split(factor=0.5)
			split.label(text="Result:")
			split.label(text=name)
			cols = box.column_flow(columns=3, align=True)
			if common.data.lastPreview == act.name:
				op = cols.operator('hydra.hmnoview', text="", icon="HIDE_ON")
			else:
				op = cols.operator('hydra.hmpreview', text="", icon="HIDE_OFF")
				op.target = hyd.map_current
				op.base = hyd.map_base
			cols.operator('hydra.hmmove', text="", icon="TRIA_DOWN_BAR")
			cols.operator('hydra.hmdelete', text="", icon="PANEL_CLOSE")

			grid = box.grid_flow(columns=1, align=True)

			cols = grid.column_flow(columns=2, align=True)
			op = cols.operator('hydra.hmapplyimg', text="", icon="IMAGE_DATA")
			op.save_target = hyd.map_current
			op.name = f"HYD_{act.name}_Eroded"
			cols.operator('hydra.hmapplygeo', text="", icon="GEOMETRY_NODES")
			# cols.operator('hydra.hmapplygeoinsert', text="", icon="OUTLINER_DATA_POINTCLOUD")
			# op = cols.operator('hydra.hmapplyupdate', text="", icon="IMAGE_REFERENCE")

			cols = grid.column_flow(columns=3, align=True)
			cols.operator('hydra.hmapplymod', text="", icon="MOD_DISPLACE")
			cols.operator('hydra.hmapplydisp', text="", icon="RNDCURVE")
			cols.operator('hydra.hmapplybump', text="", icon="MOD_NOISE")
			
			if any(m.name.startswith("HYD_") for m in act.modifiers):
				cols = box.column_flow(columns=2, align=True)
				cols.operator('hydra.hmmerge', text="", icon="MESH_DATA")
				cols.operator('hydra.hmmergeshape', text="", icon="SHAPEKEY_DATA")

		if common.data.hasMap(hyd.map_source):
			hasAny = True
			name = common.data.maps[hyd.map_source].name
			box = container.box()
			split = box.split(factor=0.5)
			split.label(text="Source:")
			split.label(text=name)
			cols = box.column_flow(columns=3, align=True)
			cols.operator('hydra.hmforcereload', text="", icon="GRAPH")
			cols.operator('hydra.hmback', text="", icon="TRIA_UP_BAR")
			cols.operator('hydra.hmreload', text="", icon="FILE_REFRESH")
		
		if not hasAny:
			container.label(text="No maps have been cached yet.")

def fragmentSize(container, obj: bpy.types.Object):
	"""UI function for displaying size settings and size locked message.
	
	:param container: Containing UI element.
	:param obj: Object the settings apply to.
	:type obj: :class:`bpy.types.Object`"""
	hyd = obj.hydra_erosion
	if common.data.hasMap(hyd.map_base):
		split = container.split(factor=0.5)
		split.label(text=f"Size:")
		split.label(text=f"{tuple(hyd.img_size)}")
	else:
		container.prop(hyd, "img_size")

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

#-------------------------------------------- Heightmap

class HeightmapPanel(bpy.types.Panel, DefaultPanel):
	"""Panel for standalone heightmap generation."""
	bl_category = "Hydra"
	bl_label = "Hydra - Heightmap"
	bl_idname = "HYDRA_PT_heightPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}
	bl_description = "Generate heightmap into an image"

	def draw(self, ctx):
		obj = ctx.object
		data = common.data
		hyd = obj.hydra_erosion
		
		col = self.layout.column()
		col.operator('hydra.genheight', text="Generate", icon="SEQ_HISTOGRAM")
		
		col.label(text="Heightmap type:")
		col.prop(hyd, "heightmap_gen_type", text="")

		col.prop(hyd, "heightmap_gen_size")

		col.separator()

		if data.hasMap(hyd.map_base):
			col.separator()
			size = data.maps[hyd.map_base].size
			split = col.split()
			split.label(text="Cached:")
			split.label(text=str(size))
			box = col.box()	#shared; if other heighmaps exist, then so does map_base
			split = box.split()
			split.label(text="Mesh")
			split.operator('hydra.hmapplyimg', text="", icon="IMAGE_DATA").save_target = hyd.map_base
		
		if data.hasMap(hyd.map_source):
			col.separator()
			split = box.split()
			name = data.maps[hyd.map_source].name
			split.label(text=name)
			split.operator('hydra.hmapplyimg', text="", icon="IMAGE_DATA").save_target = hyd.map_source
		
		if data.hasMap(hyd.map_current):
			col.separator()
			split = box.split()
			name = data.maps[hyd.map_current].name
			split.label(text=name)
			split.operator('hydra.hmapplyimg', text="", icon="IMAGE_DATA").save_target = hyd.map_current

class HeightmapOp(bpy.types.Operator):
	"""Standalone heightmap operator."""
	bl_idname = "hydra.genheight"
	bl_label = "Heightmap"
	bl_description = "Generate heightmap into an image"

	def invoke(self, ctx, event):
		common.data.clear()
		act = ctx.object

		size = tuple(act.hydra_erosion.img_size)
		act.hydra_erosion.img_size = tuple(act.hydra_erosion.heightmap_gen_size)

		normalized = act.hydra_erosion.heightmap_gen_type == "normalized"
		proportional = act.hydra_erosion.heightmap_gen_type == "proportional"
		txt = heightmap.genHeightmap(act, normalized=normalized, proportional=proportional)

		img = texture.writeImage(f"HYD_{act.name}_Heightmap", txt)
		txt.release()
		act.hydra_erosion.img_size = size
		nav.gotoImage(img)
		self.report({'INFO'}, f"Successfuly created heightmap: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Erosion

class ErodePanel(bpy.types.Panel, DefaultPanel):
	"""Panel for water erosion."""
	bl_category = "Hydra"
	bl_label = "Hydra - Erosion"
	bl_idname = "HYDRA_PT_erodePanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		layout = self.layout
		act = ctx.object
		hyd = act.hydra_erosion
		
		main = layout.column()
		
		if hyd.out_color and hyd.color_src not in bpy.data.images:
			box = main.box()
			box.operator('hydra.erode', text="No color source", icon="RNDCURVE")
			box.enabled = False
		else:
			main.operator('hydra.erode', text="Erode", icon="RNDCURVE")
		
		fragmentSize(main.box(), act)

class ErodeHeightPanel(bpy.types.Panel, DefaultHeightmapPanel):
	"""Subpanel for water erosion heightmap stack. Uses :class:`DefaultHeightmapPanel`"""
	bl_label = "Heightmaps"
	bl_parent_id = "HYDRA_PT_erodePanel"
	bl_idname = "HYDRA_PT_erodeHeightPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

class ErodeExtraPanel(bpy.types.Panel):
	"""Subpanel for water erosion extra settings."""
	bl_label = "Extra"
	bl_parent_id = "HYDRA_PT_erodePanel"
	bl_idname = "HYDRA_PT_erodeExtraPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		p = self.layout.box()
		act = ctx.object
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
	bl_parent_id = "HYDRA_PT_erodePanel"
	bl_idname = "HYDRA_PT_erodePartPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

	def draw(self, ctx):
		p = self.layout.box()
		hyd = ctx.object.hydra_erosion
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
	bl_parent_id = "HYDRA_PT_erodePanel"
	bl_idname = "HYDRA_PT_erodeAdvPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		p = self.layout.box()
		hyd = ctx.object.hydra_erosion
		p.prop(hyd, "interpolate_erosion")
		split = p.split()
		split.label(text="Chunk size")
		split.prop(hyd, "part_subdiv", text="")
		p.prop(hyd, "part_maxjump")

class ErodeOp(bpy.types.Operator):
	"""Water erosion operator."""
	bl_idname = "hydra.erode"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		hyd = ctx.object.hydra_erosion
		data = common.data
		data.clear()
		data.running = True

		erosion.erosionPrepare(ctx.object)
		erosion.erosionRun(ctx.object)
		imgs = erosion.erosionFinish(ctx.object)
		
		heightmap.preview(ctx.object, data.maps[hyd.map_current], data.maps[hyd.map_base])
		nav.gotoModifier()
		if hyd.out_color:
			nav.gotoImage(imgs[2])
		elif hyd.out_sediment:
			nav.gotoImage(imgs[1])
		elif hyd.out_depth:
			nav.gotoImage(imgs[0])
		common.data.report(self, callerName="Erosion")
		return {'FINISHED'}

#-------------------------------------------- Flow

class FlowPanel(bpy.types.Panel, DefaultPanel):
	"""Panel for flowmap generation."""
	bl_category = "Hydra"
	bl_label = "Hydra - Flow"
	bl_idname = "HYDRA_PT_flowpanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}
	bl_description = "Generate flow data into an image"

	def draw(self, ctx):
		hyd = ctx.object.hydra_erosion
		
		col = self.layout.column()
		col.operator('hydra.genflow', text="Generate Flowmap", icon="MATFLUID")
	
		fragmentSize(col.box(), ctx.object)
		
		name = f"HYD_{ctx.object.name}_Flow"
		if name in bpy.data.images:
			col.separator()
			col.label(text="Generated:")
			box = col.box()
			split = box.split()
			split.label(text=name)
			op = split.operator('hydra.nav', text="", icon="IMAGE_DATA")
			op.target = name

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
	bl_idname = "hydra.genflow"
	bl_label = "Generate Flow"
	bl_description = "Generates a map of flow concentration using particle erosion. Uses eroded heightmaps, if they exist"
	bl_options = {'REGISTER'}
	
	def invoke(self, ctx, event):
		common.data.clear()
		obj = ctx.object
		img = flow.genFlow(obj)
		nav.gotoImage(img)
		self.report({"INFO"}, f"Successfuly created image: {img.name}")
		return {'FINISHED'}

#-------------------------------------------- Thermal

class ThermalPanel(bpy.types.Panel, DefaultPanel):
	"""Panel for thermal erosion."""
	bl_category = "Hydra"
	bl_label = "Hydra - Thermal"
	bl_idname = "HYDRA_PT_thermalPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}
	bl_description = "Erosion settings for material transport"

	def draw(self, ctx):
		act = ctx.object
		hyd = act.hydra_erosion
		
		col = self.layout.column()
		col.operator('hydra.thermal', text="Erode", icon="RNDCURVE")

		fragmentSize(col.box(), act)

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
	bl_parent_id = "HYDRA_PT_thermalPanel"
	bl_idname = "HYDRA_PT_thermalHeightPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"

class ThermalOp(bpy.types.Operator):
	"""Thermal erosion operator."""
	bl_idname = "hydra.thermal"
	bl_label = "Erode"
	bl_description = "Erode object"
	bl_options = {'REGISTER', 'UNDO'}
			
	def invoke(self, ctx, event):
		data = common.data
		data.clear()
		hyd = ctx.object.hydra_erosion
		apply.removePreview()

		thermal.thermalPrepare(ctx.object)
		thermal.thermalRun(ctx.object)
		thermal.thermalFinish(ctx.object)

		heightmap.preview(ctx.object, data.maps[hyd.map_current], data.maps[hyd.map_base])
		nav.gotoModifier()
		data.report(self, callerName="Erosion")
		return {'FINISHED'}
	
#-------------------------------------------- Cleanup

class CleanupPanel(bpy.types.Panel):
	"""Panel for cleanup operations."""
	bl_category = "Hydra"
	bl_label = "Hydra - Cleanup"
	bl_idname = "HYDRA_PT_cleanPanel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, context):
		col = self.layout.column()
		col.operator('hydra.clean', text="Clear cache", icon="SHADING_BBOX")
		col.operator('hydra.hmnoview', text="Remove previews", icon="HIDE_ON")
	
	@classmethod
	def poll(cls, ctx):
		return not startup.invalid

class CleanupOp(bpy.types.Operator):
	"""Resource release operator."""
	bl_idname = "hydra.clean"
	bl_label = "Clean"
	bl_description = "Release cached textures"
	bl_options = {'REGISTER', 'UNDO'}
	
	def invoke(self, context, event):
		apply.removePreview()
		apply.removeImagePreview()
		common.data.freeAll()
		self.report({'INFO'}, "Successfuly freed cached textures.")
		common.showMessage("Successfuly freed cached textures.")
		return {'FINISHED'}

#-------------------------------------------- Tests

class InfoPanel(bpy.types.Panel):
	"""Object info panel."""
	bl_category = "Hydra"
	bl_label = "Hydra - Info"
	bl_idname = "HYDRA_PT_info"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		obj = ctx.object
		col = self.layout.column()

		col.separator()
		col.operator("hydra.instantiate", icon="DUPLICATE").object = True

		if owner := common.getOwner(obj.name, apply.P_LAND_NAME):
			col.separator()
			col.label(text="Original:")
			box = col.box()
			split = box.split()
			split.label(text=owner)
			split.operator('hydra.nav', text="", icon="IMAGE_DATA").target = owner
	
	@classmethod
	def poll(cls, ctx):
		obj = ctx.object
		if startup.invalid or not obj:
			return False
		return obj.hydra_erosion.is_generated
#-------------------------------------------- Exports

EXPORTS = [
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
	HeightmapOp,
	HeightmapPanel,
	CleanupOp,
	CleanupPanel
]
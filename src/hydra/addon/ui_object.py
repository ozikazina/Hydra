import bpy, bpy.types

from Hydra import common
from Hydra.addon import ui_common

class HeightmapPanel(ui_common.ObjectPanel):
	"""Panel for standalone heightmap generation."""
	bl_label = "Hydra - Heightmap"
	bl_idname = "HYDRA_PT_heightPanel"
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

		if data.has_map(hyd.map_base):
			col.separator()
			size = data.get_map(hyd.map_base).size
			split = col.split()
			split.label(text="Cached:")
			split.label(text=str(size))
			box = col.box()	#shared; if other heighmaps exist, then so does map_base
			split = box.split()
			split.label(text="Mesh")
			split.operator('hydra.hm_apply_img', text="", icon="IMAGE_DATA").save_target = hyd.map_base
		
		if data.has_map(hyd.map_source):
			col.separator()
			split = box.split()
			name = data.get_map(hyd.map_source).name
			split.label(text=name)
			split.operator('hydra.hm_apply_img', text="", icon="IMAGE_DATA").save_target = hyd.map_source
		
		if data.has_map(hyd.map_current):
			col.separator()
			split = box.split()
			name = data.get_map(hyd.map_current).name
			split.label(text=name)
			split.operator('hydra.hm_apply_img', text="", icon="IMAGE_DATA").save_target = hyd.map_current

#-------------------------------------------- Erosion

class ErosionPanel(ui_common.ErosionPanel, ui_common.ObjectPanel):
	bl_idname = "HYDRA_PT_ErosionPanel"

class ErosionHeightmapPanel(ui_common.HeightmapSystemPanel, ui_common.ObjectPanel):
	"""Subpanel for water erosion heightmap stack. Uses :class:`DefaultHeightmapPanel`"""
	bl_parent_id = "HYDRA_PT_ErosionPanel"
	bl_idname = "HYDRA_PT_ErosionHeightmapPanel"

class ErosionExtrasPanel(ui_common.ErosionExtrasPanel, ui_common.ObjectPanel):
	bl_parent_id = "HYDRA_PT_ErosionPanel"
	bl_idname = "HYDRA_PT_ErosionExtrasPanel"

class ErosionSettingsPanel(ui_common.ErosionSettingsPanel, ui_common.ObjectPanel):
	bl_parent_id = "HYDRA_PT_ErosionPanel"
	bl_idname = "HYDRA_PT_ErosionSettingsPanel"	

class ErosionAdvancedPanel(ui_common.ErosionAdvancedPanel, ui_common.ObjectPanel):
	bl_parent_id = "HYDRA_PT_ErosionPanel"
	bl_idname = "HYDRA_PT_ErosionAdvancedPanel"

#-------------------------------------------- Flow

class FlowPanel(ui_common.FlowPanel, ui_common.ObjectPanel):
	"""Panel for flowmap generation."""
	bl_idname = "HYDRA_PT_FlowPanel"

#-------------------------------------------- Thermal

class ThermalPanel(ui_common.ThermalPanel, ui_common.ObjectPanel):
	bl_idname = "HYDRA_PT_ThermalPanel"

class ThermalHeightPanel(ui_common.HeightmapSystemPanel, ui_common.ObjectPanel):
	"""Subpanel for thermal erosion heightmap stack. Uses :class:`DefaultHeightmapPanel`."""
	bl_parent_id = "HYDRA_PT_ThermalPanel"
	bl_idname = "HYDRA_PT_ThermalHeightPanel"

#-------------------------------------------- Info

class InfoPanel(ui_common.InfoPanel, ui_common.ObjectPanel):
	"""Object info panel."""
	bl_idname = "HYDRA_PT_InfoPanel"

#-------------------------------------------- Cleanup

class CleanupPanel(ui_common.ObjectPanel):
	"""Panel for cleanup operations."""
	bl_label = "Hydra - Cleanup"
	bl_idname = "HYDRA_PT_CleanupPanel"

	def draw(self, ctx):
		col = self.layout.column()
		col.operator('hydra.release_cache', text="Clear cache", icon="SHADING_BBOX")
		col.operator('hydra.hmnoview', text="Remove previews", icon="HIDE_ON")
	
#-------------------------------------------- Debug

class DebugPanel(bpy.types.Panel):
	bl_category = "Hydra"
	bl_label = "Hydra - Debug"
	bl_idname = "HYDRA_PT_debug"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_context = "objectmode"
	bl_options = {'DEFAULT_CLOSED'}

	def draw(self, ctx):
		col = self.layout.column()
		col.operator('hydra.reload_shaders', text="Reload shaders", icon="FILE_REFRESH")
		col.operator('hydra.nuke_gui', text="Nuke GUI", icon="MOD_EXPLODE")

	@classmethod
	def poll(cls, ctx):
		return common.get_preferences().debug_mode

#-------------------------------------------- Exports

def get_exports()->list:
	return [
		InfoPanel,
		ErosionPanel,
		ErosionSettingsPanel,
		ErosionHeightmapPanel,
		ErosionExtrasPanel,
		ErosionAdvancedPanel,
		ThermalPanel,
		ThermalHeightPanel,
		FlowPanel,
		HeightmapPanel,
		CleanupPanel,
		DebugPanel
	]
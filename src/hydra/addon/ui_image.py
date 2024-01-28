import bpy
from Hydra.addon import ui_common

class LandscapePanel(ui_common.ImagePanel):
	"""Panel for landscape generation."""
	bl_label = "Hydra - Landscape"
	bl_idname = "HYDRA_PT_LandscapePanel"

	def draw(self, ctx):
		act = ctx.area.spaces.active.image
		hyd = act.hydra_erosion
		
		col = self.layout.column()
		col.prop(hyd, "gen_subscale")
		col.operator('hydra.landscape', text="Generate", icon="RNDCURVE")

#-------------------------------------------- Erosion

class ErosionPanel(ui_common.ErosionPanel, ui_common.ImagePanel):
	"""Panel for water erosion."""
	bl_idname = "HYDRA_PT_ErosionPanelImage"

class ErosionHeightmapPanel(ui_common.HeightmapSystemPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion heightmap stack."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionHeightmapPanelImage"

class ErosionExtrasPanel(ui_common.ErosionExtrasPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion extra settings."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionExtrasPanelImage"

class ErosionSettingsPanel(ui_common.ErosionSettingsPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion particle settings."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionSettingsPanelImage"

class ErosionAdvancedPanel(ui_common.ErosionAdvancedPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion advanced settings."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionAdvancedPanelImage"

#-------------------------------------------- Flow

class FlowPanel(ui_common.FlowPanel, ui_common.ImagePanel):
	bl_idname = "HYDRA_PT_FlowPanelImage"

#-------------------------------------------- Thermal

class ThermalPanel(ui_common.ThermalPanel, ui_common.ImagePanel):
	"""Panel for thermal erosion."""
	bl_idname = "HYDRA_PT_ThermalPanelImage"

class ThermalHeightPanel(ui_common.HeightmapSystemPanel, ui_common.ImagePanel):
	"""Subpanel for thermal erosion heightmap stack."""
	bl_label = "Heightmaps"
	bl_parent_id = "HYDRA_PT_ThermalPanelImage"
	bl_idname = "HYDRA_PT_ThermalHeightPanelImage"

#-------------------------------------------- Info

class InfoPanel(ui_common.InfoPanel, ui_common.ImagePanel):
	"""Image info panel."""
	bl_idname = "HYDRA_PT_InfoPanelImage"

#-------------------------------------------- Cleanup

class CleanupPanel(ui_common.ImagePanel):
	"""Panel for cleanup operations."""
	bl_label = "Hydra - Cleanup"
	bl_idname = "HYDRA_PT_CleanupPanelImage"

	def draw(self, ctx):
		col = self.layout.column()
		col.operator('hydra.release_cache', text="Clear cache", icon="SHADING_BBOX")

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
		LandscapePanel,
		CleanupPanel
	]
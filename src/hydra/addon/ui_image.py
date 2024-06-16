"""Module for Image editor panels."""

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
		col.operator('hydra.landscape', text="Generate", icon="RNDCURVE")
		col.prop(hyd, "gen_subscale")

#-------------------------------------------- Erosion

class ErosionPanel(ui_common.ErosionPanel, ui_common.ImagePanel):
	"""Panel for water erosion."""
	bl_idname = "HYDRA_PT_ErosionPanelImage"

class ErosionSettingsPanel(ui_common.ErosionSettingsPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion particle settings."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionSettingsPanelImage"

class ErosionHeightmapPanel(ui_common.HeightmapSystemPanel, ui_common.ImagePanel):
	"""Subpanel for water erosion heightmap stack."""
	bl_parent_id = "HYDRA_PT_ErosionPanelImage"
	bl_idname = "HYDRA_PT_ErosionHeightmapPanelImage"

#-------------------------------------------- Flow

class ExtrasPanel(ui_common.ExtrasPanel, ui_common.ImagePanel):
	bl_idname = "HYDRA_PT_ExtrasPanelImage"

#-------------------------------------------- Thermal

class ThermalPanel(ui_common.ThermalPanel, ui_common.ImagePanel):
	"""Panel for thermal erosion."""
	bl_idname = "HYDRA_PT_ThermalPanelImage"

class ThermalSettingsPanel(ui_common.ThermalSettingsPanel, ui_common.ImagePanel):
	"""Subpanel for thermal erosion settings."""
	bl_parent_id = "HYDRA_PT_ThermalPanelImage"
	bl_idname = "HYDRA_PT_ThermalSettingsPanelImage"

class ThermalHeightmapPanel(ui_common.HeightmapSystemPanel, ui_common.ImagePanel):
	"""Subpanel for thermal erosion heightmap stack."""
	bl_parent_id = "HYDRA_PT_ThermalPanelImage"
	bl_idname = "HYDRA_PT_ThermalHeightmapPanelImage"

#-------------------------------------------- Snow
class SnowPanel(ui_common.SnowPanel, ui_common.ImagePanel):
	"""Panel for snow simulation."""
	bl_idname = "HYDRA_PT_SnowPanelImage"

class SnowHeightmapPanel(ui_common.HeightmapSystemPanel, ui_common.ImagePanel):
	"""Subpanel for snow heightmap stack. Uses :class:`DefaultHeightmapPanel`."""
	bl_parent_id = "HYDRA_PT_SnowPanelImage"
	bl_idname = "HYDRA_PT_SnowHeightmapPanelImage"

	@classmethod
	def poll(cls, ctx):
		return cls.get_settings(ctx).snow_output != "texture"

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
		col.operator('hydra.release_cache', text="Clear data", icon="SHADING_BBOX")

#-------------------------------------------- Exports

def get_exports()->list:
    return [
		InfoPanel,
		ErosionPanel,
		ErosionSettingsPanel,
		ErosionHeightmapPanel,
		ThermalPanel,
		ThermalSettingsPanel,
		ThermalHeightmapPanel,
		SnowPanel,
		SnowHeightmapPanel,
		ExtrasPanel,
		LandscapePanel,
		CleanupPanel
	]
import bpy.types

class NodesPanel(bpy.types.Panel):
	bl_region_type = 'UI'
	bl_category = "Hydra"
	bl_space_type = 'NODE_EDITOR'
	bl_options = {'DEFAULT_CLOSED'}
	bl_label = "Hydra - Utils"
	bl_idname = "HYDRA_PT_ShaderUtils"

	@classmethod
	def poll(cls, ctx):
		return ctx.area.ui_type == "ShaderNodeTree"

	def draw(self, ctx):
		self.layout.operator('hydra.planet_uv', icon="RNDCURVE")

def get_exports()->list:
	return [
		NodesPanel
	]
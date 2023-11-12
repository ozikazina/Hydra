"""Module specifying settings for Hydra."""

import bpy
from bpy.props import (
	BoolProperty,
	FloatProperty,
	IntProperty,
	IntVectorProperty,
	StringProperty,
	EnumProperty)

from Hydra import common

#-------------------------------------------- Settings

class HydraGlobalGroup(bpy.types.PropertyGroup):
	"""Global settings group for Hydra."""
	heightmap_size: IntVectorProperty(
		default=(512,512),
		name="Heightmap size",
		min=16,
		max=4096,
		description="Image size for direct heightmap generation",
		size=2
	)
	"""Image size for direct heightmap generation."""

	gen_subscale: IntProperty(
		default=2,
		name="Subscale",
		min=1, max=16,
		description="Resolution divisor for landscape generation"
	)
	"""Resolution divisor for landscape generation"""

class ErosionGroup(bpy.types.PropertyGroup):
	"""Individual settings for objects and images."""
	height_scale: FloatProperty(
		name="Height scale", default=1,
		min = 0.01, max = 10
	)
	"""Height scaling factor after normalization. Value of 1 means same scale as heightmap width."""

	scale_ratio: FloatProperty(
		name="Scale ratio", default=1,
		min = 0.01, max = 10
	)
	"""Ratio of Y to X scales for non-uniform images."""

	org_scale: FloatProperty(
		name="Original height scaling", default=1,
		min = 0.01, max = 10
	)
	"""Original height scaling to use with modifiers, which affect it."""

	img_size: IntVectorProperty(
		default=(512,512),
		name="Image size",
		min=16,
		max=2048,
		description="Image size",
		size=2
	)
	
	#------------------------- Erosion
	
	out_color: BoolProperty(
		default=False,
		name="Transport color",
		description="Transport color during motion (slow)"
	)

	interpolate_color: BoolProperty(
		default=True,
		name="Interpolate color",
		description="Deposited color is smoothly applied between cells. May cause visual artifacts on borders"
	)

	interpolate_erosion: BoolProperty(
		default=True,
		name="Interpolate erosion",
		description="Particle erodes all nearest cells. Produces smoother curves"
	)

	interpolate_flow: BoolProperty(
		default=True,
		name="Interpolate flow",
		description="Creates smoother but blurrier streaks"
	)
	
	color_src: StringProperty(
		name="Color",
		description="Color image texture"
	)
	
	out_depth: BoolProperty(
		default=False,
		name="Create depth map",
		description="Output depth of erosion at each point"
	)
	
	out_sediment: BoolProperty(
		default=False,
		name="Create sediment map",
		description="Output sediment height at each point"
	)

	part_deposition: FloatProperty(
		default=0.5,
		min=0.0, max=1.0,
		name="Deposition strength",
		description="Defines how fast sediment can deposit. A value of 0 means only erosion occurs"
	)
	
	part_fineness: FloatProperty(
		default=0.25,
		min=0.1, max=2.0,
		soft_min=0.1, soft_max=1.0,
		name="Erosion smoothness",
		description="Higher values smooth erosion, but may create unwanted patterns"
	)
	
	part_capacity: FloatProperty(
		default=1.0,
		min=0.5, max=3.0,
		soft_max=2.0,
		name="Capacity",
		description="Sediment capacity of the particle. High capacity, high acceleration and low iterations lead to smoother results"
	)

	part_subdiv: EnumProperty(
		default="4",
		items=(
			("16", "16", "Chunks of side 16", 0),
			("8", "8", "Chunks of side 8", 1),
			("4", "4", "Chunks of side 4", 2),
			("2", "2", "Chunks of side 2", 3),
			("1", "1", "No chunking", 4),
		),
		name="Chunk size",
		description="Size of solver chunks. Higher values prevent interference between particles"
	)

	flow_subdiv: EnumProperty(
		default="8",
		items=(
			("16", "16", "Chunks of side 16", 0),
			("8", "8", "Chunks of side 8", 1),
			("4", "4", "Chunks of side 4", 2),
			("2", "2", "Chunks of side 2", 3),
			("1", "1", "No chunking", 4),
		),
		name="Chunk size",
		description="Size of solver chunks. Higher values prevent interference between particles"
	)

	part_randomize: BoolProperty(
		default=True,
		name="Randomize droplets",
		description="Each chunk has randomized droplets. Otherwise creates one particle for each pixel. Requires higher iterations"
	)

	part_maxjump: FloatProperty(
		default=0.1,
		min=0.01, soft_max=0.2, max=1,
		name="Maximum drop",
		description="Maximum height a particle can drop. Prevents deformations near borders"
	)
	
	#------------------------- Particle

	part_iter_num: IntProperty(
		default=100,
		min=1, max=1000,
		name="Iterations",
		description="Number of iterations, each over the entire image"
	)
	
	part_lifetime: IntProperty(
		default=50,
		min=1, max=500,
		name="Lifetime",
		description="Number of steps a particle can take"
	)
	
	part_acceleration: FloatProperty(
		default=0.5,
		min=0.01, max=4.0,
		soft_max=3.0,
		name="Acceleration",
		description="Influence of the surface on motion"
	)
	
	part_drag: FloatProperty(
		default=0.2,
		min=0.0, max=0.99,
		name="Drag",
		description="Drag applied to the particle. Lower values lead to smoother streaks"
	)

	sed_contrast: FloatProperty(
		default=0.5,
		min=0.0, max=1.0,
		name="Sediment brightness",
		description="Brightens the sedimentation map"
	)

	depth_contrast: FloatProperty(
		default=0.5,
		min=0.0, max=1.0,
		name="Depth brightness",
		description="Brightens the depth map"
	)

	color_mixing: FloatProperty(
		default=0.2,
		min=0.0, max=1.0,
		name="Color mixing",
		description="Defines how strongly a particle colors the path it takes. Value of 1 means directly painting the color"
	)
	
	#------------------------- Flow
	
	flow_contrast: FloatProperty(
		default=0.5,
		min=0.0, max=1.0,
		name="Flow contrast",
		description="Higher values lead to thinner streaks"
	)

	#------------------------- Thermal
	
	thermal_iter_num: IntProperty(
		default=100,
		min=1, max=3000, soft_max=1000,
		name="Iterations",
		description="Number of iterations of thermal erosion"
	)

	thermal_angle: FloatProperty(
		default=45,
		min=0, max=85,
		name="Angle",
		description="Maximum angle the surface can have in degrees"
	)

	thermal_strength: FloatProperty(
		default=1,
		min=0, max=2, soft_max=1,
		name="Strength",
		description="Strength of each iteration"
	)

	thermal_solver: EnumProperty(
		default="both",
		items=(
			("both", "All", "Alternate directions each iteration", 0),
			("cardinal", "Cardinal", "Only move material in XY directions", 1),
			("diagonal", "Diagonal", "Only move material on diagonals", 2),
		),
		name="Direction",
		description="Solver neighborhood type"
	)

	#------------------------- Utils

	is_generated: BoolProperty(name="Is Generated", description="Prevents resource allocation for generated objects")

	map_current: StringProperty(name="Current map", description="Current heightmap")
	map_source: StringProperty(name="Source map", description="Source heightmap")
	map_base: StringProperty(name="Base map", description="Base heightmap")
	
	#------------------------- Funcs
	
	def getSize(self):
		return tuple(self.img_size)
		
	def isSameSize(self, hm: common.Heightmap):
		return tuple(hm.size) == tuple(self.img_size)

EXPORTS = [HydraGlobalGroup, ErosionGroup]
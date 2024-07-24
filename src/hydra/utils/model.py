"""Module responsible for VAO creation and mesh operations."""

import numpy as np
import bpy, bmesh
import bpy.types
import moderngl as mgl
from Hydra import common

# --------------------------------------------------------- Models

def create_vao(ctx: mgl.Context, program: mgl.Program, vertices:list[tuple[float]]=None, indices:list[int]=None)->mgl.VertexArray:
	"""Creates a :class:`moderngl.VertexArray` object.
	
	:param ctx: ModernGL context.
	:type ctx: :class:`moderngl.Context`
	:param program: Program to bind to the VAO.
	:type program: :class:`moderngl.Program`
	:param vertices: Optional list of 3D vertex position.
	:type vertices: :class:`list[tuple[float, float, float]]`
	:param indices: Optional list of vertex indices.
	:type indices: :class:`list[int]`
	:return: Created VAO object.
	:rtype: :class:`moderngl.VertexArray`"""
	if vertices is None:
		vertices = [(1,1,0), (1,-1,0), (-1,-1,0), (1,1,0), (-1,-1,0),  (-1,1,0)]
		indices = None
		
	vbo = ctx.buffer(data=np.array(vertices).astype('f4').tobytes())
	if indices is None:
		return ctx.vertex_array(
			program=program,
			content=[(vbo, "3f", "position")]
		)
	else:
		ind = ctx.buffer(data=np.array(indices).tobytes())
		return ctx.vertex_array(
			program=program,
			content=[(vbo, "3f", "position")], index_buffer=ind
		)

def create_vaos(ctx: mgl.Context, programs: list[mgl.Program], obj: bpy.types.Object)->list[mgl.VertexArray]:
	mesh = evaluate_mesh(obj)

	if common.get_preferences().skip_indexing:
		print("Skipping vertex indexing.")
		verts = np.empty((len(mesh.vertices), 3), 'f')
		
		mesh.vertices.foreach_get(
			"co", np.reshape(verts, len(mesh.vertices) * 3))

		verts = [verts[i] for face in mesh.loop_triangles for i in face.vertices]
		return [create_vao(ctx, prog, vertices=verts) for prog in programs]
	else:
		verts = np.empty((len(mesh.vertices), 3), 'f')
		inds = np.empty((len(mesh.loop_triangles), 3), 'i')

		mesh.vertices.foreach_get(
			"co", np.reshape(verts, len(mesh.vertices) * 3))
		mesh.loop_triangles.foreach_get(
			"vertices", np.reshape(inds, len(mesh.loop_triangles) * 3))

		return [create_vao(ctx, prog, vertices=verts, indices=inds) for prog in programs]

def evaluate_mesh(obj: bpy.types.Object)->bpy.types.Mesh:
	"""Evaluates an object as a mesh.
	
	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Evaluated mesh with calculated loop triangles.
	:rtype: :class:`bpy.types.Mesh`"""
	depsgraph = bpy.context.evaluated_depsgraph_get()
	eval = obj.evaluated_get(depsgraph)
	mesh = bpy.data.meshes.new_from_object(eval)
	mesh.calc_loop_triangles()
	return mesh

def get_resize_matrix(obj: bpy.types.Object, planet: bool = False, with_scale: bool = False)->tuple[float]:
	"""
	Creates a resizing matrix that scales the input object into normalized device coordinates, so that 1-Z is the normalized surface height.

	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	:return: Created resizing matrix.
	:rtype: :class:`tuple[float]`
	"""
	# bounding box is relative to object center
	ar = np.array(obj.bound_box)

	if planet:
		if with_scale:
			scale = max([
				ar[4][0] * obj.scale[0], ar[0][0] * obj.scale[0],
				ar[2][1] * obj.scale[1], ar[0][1] * obj.scale[1],
				ar[1][2] * obj.scale[2], ar[0][2] * obj.scale[2]
			])
			scale = 1.0 / scale

			return [
				scale * obj.scale[0],0,0,0,
				0,scale * obj.scale[1],0,0,
				0,0,scale * obj.scale[2],0,
				0,0,0,1
			]
		else:
			scale = max([
				ar[4][0], ar[0][0],
				ar[2][1], ar[0][1],
				ar[1][2], ar[0][2]
			])
			scale = 1.0 / scale

			return [
				scale,0,0,0,
				0,scale,0,0,
				0,0,scale,0,
				0,0,0,1
			]
	else:
		cx = (ar[4][0] + ar[0][0]) * 0.5
		cy = (ar[2][1] + ar[0][1]) * 0.5
		cz = (ar[1][2] + ar[0][2]) * 0.5
		dx = 2.0/(ar[4][0] - ar[0][0])
		dy = 2.0/(ar[2][1] - ar[0][1])
		dz = 1.0/(ar[1][2] - ar[0][2])

		return [
			dx,0,0,-cx*dx,
			0,dy,0,-cy*dy,
			0,0,-dz,0.5+cz*dz,
			0,0,0,1
		]

def recalculate_scales(obj: bpy.types.Object)->None:
	"""
	Sets :data:`hydra_erosion.scale_ratio`, :data:`hydra_erosion.org_scale`, :data:`hydra_erosion.org_width` and :data:`hydra_erosion.height_scale` for the object.

	:param obj: Object to be evaluated.
	:type obj: :class:`bpy.types.Object`
	"""
	ar = np.array(obj.bound_box)
	dx = (ar[4][0] - ar[0][0]) / 2
	dy = (ar[2][1] - ar[0][1]) / 2
	dz = (ar[1][2] - ar[0][2])

	obj.hydra_erosion.scale_ratio = dy / dx if dx > 1e-3 else 1
	obj.hydra_erosion.height_scale = dz / dx if dx > 1e-3 else 1
	obj.hydra_erosion.org_scale = abs(obj.dimensions.z / obj.scale.z) if abs(obj.scale.z) > 1e-3 else 1
	obj.hydra_erosion.org_width = abs(obj.dimensions.x / obj.scale.x) if abs(obj.scale.x) > 1e-3 else 1

def create_cube_mesh(side_length, name):
	res = side_length

	vert_count = 6 * res ** 2 - 12 * res + 8
	face_count = 6 * (res-1) ** 2

	verts = np.empty((vert_count * 3), dtype=np.float32)
	edges = []
	faces = np.zeros((face_count, 4), dtype=np.int32)

	tile_size = 2/(res-1)

	def add_verts(off, dest_a, dest_b, dest_c, c, size_a, size_b, count_a, count_b):
		end = off + 3 * count_a * count_b
		verts[off + dest_a:end + dest_a:3], verts[off+dest_b:end+dest_b:3] = \
			np.mgrid[-size_a:size_a:complex(count_a),-size_b:size_b:complex(count_b)].reshape((2,count_a * count_b))
		if c is not None:
			verts[off + dest_c:end + dest_c:3] = c
		return end
	
	def add_faces(off, width, height, flip):
		# Creates starting indices for vertical edge, repeats them width-times, adds increasing series to each row
		end = off[0] + (width - 1) * (height - 1)
		start = np.array(range(off[1], off[1] + width * (height - 1), width), dtype=np.int32).repeat(width-1).reshape((height-1,width-1)) + np.array([range(width-1)], dtype=np.int32)
		# Repeats each vertex 4 times, adds 0,1 (bottom edge), res+1,res (top edge) to make a face
		adjust = np.array([width, width+1, 1, 0] if flip else [0,1,width+1,width], dtype=np.int32)
		faces[off[0]:end] = start.reshape(-1).repeat(4).reshape(((width - 1) * (height - 1), 4)) + adjust
		return (end, off[1] + width * height)
	
	def add_face_strip(off, length, width1, width2, off1, off2, flip):
		end = off[0] + length - 1
		if flip:
			(width1, width2, off1, off2) = (width2, width1, off2, off1)
		faces[off[0]:end] = [[
			x * width1 + off1,
			(x + 1) * width1 + off1,
			(x + 1) * width2 + off2,
			x * width2 + off2
		] for x in range(0, length - 1)]
		return (end, off[1])

	verts.fill(-1)

	# +Z
	offset = end = add_verts(0, 1, 0, 2, 1, 1, 1, res, res)
	# -Z
	offset = end = add_verts(offset, 1, 0, 2, None, 1, 1, res, res)
	# -Y
	offset = end = add_verts(offset, 2, 0, 1, None, 1-tile_size, 1, res-2, res)
	# +Y
	offset = end = add_verts(offset, 2, 0, 1, 1, 1-tile_size, 1, res-2, res)
	# -X
	offset = end = add_verts(offset, 2, 1, 0, None, 1-tile_size, 1-tile_size, res-2, res-2)
	# +X
	offset = end = add_verts(offset, 2, 1, 0, 1, 1-tile_size, 1-tile_size, res-2, res-2)
	
	# Faces
	# +Z
	(end, vert_offset) = add_faces((0,0), res, res, False)
	# -Z
	(end, vert_offset) = add_faces((end,vert_offset), res, res, True)
	# -Y
	(end, vert_offset) = add_faces((end,vert_offset), res, res-2, False)
	vert_offset -= res * (res - 2)

	end, vert_offset = add_face_strip((end, vert_offset), res, 1, 1,
								vert_offset + res * (res - 3),
								0, False)
	end, vert_offset = add_face_strip((end, vert_offset), res, 1, 1,
								vert_offset,
								0 + res ** 2, True)
	vert_offset += res * (res - 2)
	# +Y
	(end, vert_offset) = add_faces((end,vert_offset), res, res-2, True)
	vert_offset -= res * (res - 2)

	end, vert_offset = add_face_strip((end, vert_offset), res, 1, 1,
								vert_offset + res * (res - 3),
								0 + res * (res - 1), True)
	end, vert_offset = add_face_strip((end, vert_offset), res, 1, 1,
								vert_offset,
								res ** 2 + res * (res - 1), False)
	offset = end
	vert_offset += res * (res - 2)
	# -X
	(end, vert_offset) = add_faces((end,vert_offset), res-2, res-2, True)
	vert_offset -= (res - 2)**2

	#flipped
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res - 2, res,
								vert_offset,
								vert_offset - 2 * res * (res - 2), True)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res - 2, res,
								vert_offset + res - 3,
								vert_offset - res * (res - 2), False)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res, 1,
								res,
								vert_offset + (res - 2) * (res - 3), False)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res, 1,
								res ** 2 + res,
								vert_offset, True)
	offset = end

	end += 4
	faces[offset:end] = [
		[
			res ** 2 + res,
			res ** 2,
			vert_offset - 2 * res * (res - 2),
			vert_offset,
		],
		[
			res ** 2 + res + res * (res-2),
			res ** 2 + res * (res-2),
			vert_offset + res - 3,
			vert_offset - 2 * res * (res - 2) + res * (res - 2),
		],
		[
			0,
			res,
			vert_offset + (res - 2) * (res - 3),
			vert_offset - 2 * res * (res - 2) + res * (res - 3),
		],
		[
			0 + res * (res - 2),
			res + res * (res - 2),
			vert_offset - res,
			vert_offset + (res - 2) * (res - 3) + res - 3,
		]
	]
	offset = end
	vert_offset += (res - 2)**2

	# +X
	(end, vert_offset) = add_faces((end,vert_offset), res-2, res-2, False)
	vert_offset -= (res - 2)**2

	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res - 2, res,
								vert_offset,
								vert_offset - 2 * res * (res - 2) + 2 * res - res * (res - 3) - 5, False)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res - 2, res,
								vert_offset + res - 3,
								vert_offset - res * (res - 2) + 2 * res - res * (res - 3) - 5, True)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res, 1,
								res + res - 1,
								vert_offset + (res - 2) * (res - 3), True)
	end, vert_offset = add_face_strip((end, vert_offset), res - 2, res, 1,
								res ** 2 + res + res - 1,
								vert_offset, False)
	offset = end

	end += 4
	faces[offset:end] = [
		[
			vert_offset,
			vert_offset - 2 * res * (res - 2) - res * (res - 5) - 5,
			res ** 2 + res-1,
			res ** 2 + res + res-1
		],
		[
			res ** 2 + res * (res-2) + res - 1,
			res ** 2 + res * (res-1) + res - 1,
			vert_offset - res * (res - 2) - res * (res - 5) - 5,
			vert_offset + res - 3,
		],
		[
			res + res-1,
			res-1,
			vert_offset - 2 * res * (res - 2) + res * (res - 3) - res * (res - 5) - 5,
			vert_offset + (res - 2) * (res - 3),
		],
		[
			vert_offset + (res - 2) * (res - 3) + res - 3,
			vert_offset - res - res * (res - 5) - 5,
			res * (res - 1) + res-1,
			res * (res - 2) + res-1
		]
	]

	mesh = bpy.data.meshes.new(name)

	mesh.from_pydata(verts.reshape((vert_count, 3)), edges, faces)

	return mesh
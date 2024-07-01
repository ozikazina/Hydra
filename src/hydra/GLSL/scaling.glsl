#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D A;//output
uniform float scale = 1.0;
uniform float offset = 0.0;

void main() {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	imageStore(A, base, (imageLoad(A,base) + offset) * scale);
}
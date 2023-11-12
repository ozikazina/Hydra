#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D A;//output
layout (r32f) uniform image2D B;//base

void main() {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	vec4 dif = 0.5*(imageLoad(A,base) - imageLoad(B,base));
	imageStore(A, base, vec4(0.5) + dif);
}
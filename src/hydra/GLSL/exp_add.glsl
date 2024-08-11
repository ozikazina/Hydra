#version 430

layout (local_size_x=1, local_size_y=1, local_size_z=1) in;

layout (r32f) uniform image2D A;
layout (r32f) uniform image2D B;

uniform float factor = 1.0;
uniform float scale = 1.0;

#define PI 3.14159265

void main(void) {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    float h_A = exp((imageLoad(A, pos).x - 1) * PI);
    float h_B = exp((imageLoad(B, pos).x - 1) * PI);

    imageStore(A, pos, vec4(scale * (h_A + factor * h_B)));
}
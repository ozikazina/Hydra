#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout(r32f) uniform image2D mapH;

uniform float snow_add = 0.0;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
    float h1 = imageLoad(mapH, base).x;
    imageStore(mapH, base, vec4(h1 + snow_add));
}

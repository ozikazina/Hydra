#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout(r32f) uniform image2D mapH;
// layout(r32f) uniform image2D offset;

// uniform float evap_start = 0.5;
// uniform float evap_rate = -2;
// uniform float evap_add = 0.1;
// uniform float evap_max = 0.5;

uniform float snow_add = 0.0;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
    float h1 = imageLoad(mapH, base).x;
    // float ht = h1 + imageLoad(offset, base).x;

    // float evap = clamp(evap_rate * (ht - evap_start), 0, evap_max) + evap_add;

    imageStore(mapH, base, vec4(h1 + snow_add));
}

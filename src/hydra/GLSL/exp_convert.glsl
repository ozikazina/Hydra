#version 430

layout (local_size_x=1, local_size_y=1, local_size_z=1) in;

layout (r32f) uniform image2D map;

uniform bool to_log = true;

#define PI 3.14159265

void main(void) {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    float h = imageLoad(map, pos).x;
    if (to_log) {
        h = log(h) / PI + 1;
    }
    else {
        h = exp((h - 1) * PI);
    }
    imageStore(map, pos, vec4(h));
}
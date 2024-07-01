#version 430

layout(local_size_x = 32, local_size_y = 1, local_size_z = 1) in;

layout(r32f) uniform readonly image2D in_image;
layout(std430) writeonly buffer out_buffer {
    float buf[];
};

uniform int height = 1;
uniform int width = 32;

void main(void) {
    ivec2 pos = ivec2(gl_GlobalInvocationID.xy);
    float mn = 1e9, mx = -1e9;

    for (int i = 0; i < height; i++) {
        float a = imageLoad(in_image, pos).x;
        mn = min(mn, a);
        mx = max(mx, a);
        pos.y++;
    }

    buf[pos.x] = mn;
    buf[width + pos.x] = mx;
}
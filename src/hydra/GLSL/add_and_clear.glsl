#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D img_in_out;
layout (r32f) uniform image2D img_add;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
    vec4 add = imageLoad(img_add, base) + imageLoad(img_in_out, base);
    imageStore(img_in_out, base, add);
    imageStore(img_add, base, vec4(0.0));
}
#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D in_sampler;
layout(rgba32f) uniform image2D out_map;

uniform vec2 tile_mult = vec2(1, 1);
uniform bool rotate_back = false;

#define PI 3.14159265

void main(void) {
    vec2 uv = (gl_GlobalInvocationID.xy + vec2(0.5,0.5)) * tile_mult * vec2(2 * PI, PI);
    vec3 pos = vec3(
        sin(uv.y) * cos(uv.x),
        sin(uv.y) * sin(uv.x),
        cos(uv.y)
    );
    // 90deg rotation around X axis (Y axis in Blender)
    pos = pos.xzy;
    if (rotate_back) {
        pos.y *= -1;
    }
    else {
        pos.z *= -1;
    }

    uv = vec2(
        atan(pos.y, pos.x),
        acos(pos.z)
    );
    vec4 color = texture(in_sampler, uv / vec2(2 * PI, PI));
    imageStore(out_map, ivec2(gl_GlobalInvocationID.xy), color);
}
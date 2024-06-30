#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D d_map;
layout (r32f) uniform image2D c_map;    //capacity -> d_mean

uniform float dt = 0.25;
uniform float lx = 1;
uniform float ly = 1;

uniform ivec2 size = ivec2(512, 512);

uniform bool tile_x = false;
uniform bool tile_y = false;

#define LEFT   (pos + ivec2(-1, 0))
#define RIGHT  (pos + ivec2(+1, 0))
#define UP     (pos + ivec2(0, -1))
#define DOWN   (pos + ivec2(0, +1))

//  1y -1
//0x  2z
//  3w +1

vec4 pipe_at(ivec2 pos) {
    if (tile_x) {
		pos.x += pos.x < 0 ? size.x : 0;
		pos.x -= pos.x >= size.x ? size.x : 0;
	}
	if (tile_y) {
		pos.y += pos.y < 0 ? size.y : 0;
		pos.y -= pos.y >= size.y ? size.y : 0;
	}

    return imageLoad(pipe_map, pos);
}

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

    vec4 pipe = imageLoad(pipe_map, pos);
    float inflow =
        pipe_at(LEFT).z + pipe_at(RIGHT).x +
        pipe_at(UP).w + pipe_at(DOWN).y;
    float outflow = pipe.x + pipe.y + pipe.z + pipe.w;
    float dv = inflow - outflow;

    dv *= dt / (lx * ly);

    float d1 = imageLoad(d_map, pos).x;

    float d = max(d1 + dv / 2, 0);
    imageStore(c_map, pos, vec4(d));  //d_mean
    d = max(d1 + dv, 0);
    imageStore(d_map, pos, vec4(d));  //d2
}//main

#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D d_map;
layout (r32f) uniform image2D c_map;    //capacity -> d_mean

uniform float dt = 0.25;
uniform float lx = 1;
uniform float ly = 1;

//  1y -1
//0x  2z
//  3w +1

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

    vec4 pipe = imageLoad(pipe_map, pos);
    float dv =  imageLoad(pipe_map, pos + ivec2(-1, 0)).z + imageLoad(pipe_map, pos + ivec2(+1, 0)).x +
                imageLoad(pipe_map, pos + ivec2(0, -1)).w + imageLoad(pipe_map, pos + ivec2(0, +1)).y -
                (pipe.x + pipe.y + pipe.z + pipe.w);

    dv *= dt / (lx * ly);

    float d1 = imageLoad(d_map, pos).x;

    float d = max((d1 + d1 + dv) / 2, 0);
    imageStore(c_map, pos, vec4(d));  //d_mean
    d = max(d1 + dv, 0);
    imageStore(d_map, pos, vec4(d));  //d2
}//main
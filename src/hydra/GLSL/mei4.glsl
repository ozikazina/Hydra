#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D b_map;
layout (rg32f) uniform image2D v_map;
layout (r32f) uniform image2D d_map;
layout (r32f) uniform image2D dmean_map;    //d_mean -> capacity

uniform float Kc = 0.1;

uniform float lx = 1;
uniform float ly = 1;
uniform float scale = 1;

uniform float depth_scale = 1;

#define LEFT   (pos + ivec2(-1, 0))
#define RIGHT  (pos + ivec2(+1, 0))
#define UP     (pos + ivec2(0, -1))
#define DOWN   (pos + ivec2(0, +1))

//  1y -1
//0x  2z
//  3w +1

float heightAt(ivec2 pos) {
    return imageLoad(b_map, pos).r + imageLoad(d_map, pos).r;
}

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

    vec4 pipe = imageLoad(pipe_map, pos);
    float dmean = imageLoad(dmean_map, pos).r;
    dmean = max(dmean, 1e-5);

    float du = imageLoad(pipe_map, LEFT).z - imageLoad(pipe_map, RIGHT).x
               + pipe.z - pipe.x;

    float u = 0.5 * du / (dmean * ly);

    float dv = imageLoad(pipe_map, UP).w - imageLoad(pipe_map, DOWN).y
               + pipe.w - pipe.y;
    
    float v = 0.5 * dv / (dmean * lx);

    imageStore(v_map, pos, vec4(u,v,0,0));

    float sx = 0.5 * abs(heightAt(RIGHT) - heightAt(LEFT)) * scale;
    float sy = 0.5 * abs(heightAt(DOWN) - heightAt(UP)) * scale;
    float gradient = sx * sx + sy * sy;

    float slope = sqrt(gradient);
    
    float C = slope * length(vec2(u,v)) * Kc * max(1 - depth_scale * dmean, 0);
    ivec2 size = imageSize(pipe_map);

    imageStore(dmean_map, pos, vec4(C));
}//main

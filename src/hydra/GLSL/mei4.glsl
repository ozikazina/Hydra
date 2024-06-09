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
uniform float minalpha = 0.025;
uniform float scale = 1;

uniform bool diagonal = true;

#define LEFT   (diagonal ? pos + ivec2(-1, -1) : pos + ivec2(-1, 0))
#define RIGHT  (diagonal ? pos + ivec2(+1, +1) : pos + ivec2(+1, 0))
#define UP     (diagonal ? pos + ivec2(+1, -1) : pos + ivec2(0, -1))
#define DOWN   (diagonal ? pos + ivec2(-1, +1) : pos + ivec2(0, +1))

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

    float du = imageLoad(pipe_map, LEFT).z - imageLoad(pipe_map, RIGHT).x
               + pipe.z - pipe.x;

    float u = 0.5 * du / (dmean * ly);

    float dv = imageLoad(pipe_map, UP).w - imageLoad(pipe_map, DOWN).y
               + pipe.w - pipe.y;
    
    float v = 0.5 * dv / (dmean * lx);

    imageStore(v_map, pos, vec4(u,v,0,0));

    float sx = 0.5 * abs(heightAt(RIGHT) - heightAt(LEFT)) * scale;
    float sy = 0.5 * abs(heightAt(DOWN) - heightAt(UP)) * scale;

    float slope = 1 - 1 / sqrt(1 + sx * sx + sy * sy);
    slope = max(min(1, slope), minalpha);
    
    float C = slope * length(vec2(u,v)) * Kc;
    ivec2 size = imageSize(pipe_map);
    C *= float(pos.x > 0 && pos.x < size.x - 1 && pos.y > 0 && pos.y < size.y - 1);

    imageStore(dmean_map, pos, vec4(C));
}//main

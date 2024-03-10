#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D b_map;
layout (r32f) uniform image2D d_map;

uniform float dt = 0.25;
uniform float lx = 1;
uniform float ly = 1;

const float A = 0.25;
//  1y -1
//0x  2z
//  3w +1

float heightAt(ivec2 pos) {
    return imageLoad(b_map, pos).r + imageLoad(d_map, pos).r;
}

void main(void) {

	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	float h = heightAt(pos); 
	vec4 pipe = imageLoad(pipe_map, pos);

	float hN = heightAt(pos + ivec2(-1, -1));
	pipe.x = max(0, pipe.x + dt * A * (h-hN) / lx);

	hN = heightAt(pos + ivec2(+1, +1));
	pipe.z = max(0, pipe.z + dt * A * (h-hN) / lx);

	hN = heightAt(pos + ivec2(+1, -1));
	pipe.y = max(0, pipe.y + dt * A * (h-hN) / ly);

	hN = heightAt(pos + ivec2(-1, +1));
	pipe.w = max(0, pipe.w + dt * A * (h-hN) / ly);

	float K = min(1, imageLoad(d_map, pos).r * lx * ly / (dt * (pipe.x + pipe.y + pipe.z + pipe.w)));

	pipe *= K;
	imageStore(pipe_map, pos, pipe);
}//main

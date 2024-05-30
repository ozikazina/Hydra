#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D b_map;
layout (r32f) uniform image2D d_map;

uniform float dt = 0.25;
uniform float lx = 1;
uniform float ly = 1;

const float A = 0.25;

uniform bool diagonal = true;
uniform bool erase = false;

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
	ivec2 imgsize = imageSize(b_map);

	float h = heightAt(pos); 
	vec4 pipe = imageLoad(pipe_map, pos);

	float allowed = float(LEFT.x >= 0);
	float hN = h - heightAt(LEFT);
	pipe.x = max(0, pipe.x + dt * A * hN * allowed / lx);

	allowed = float(LEFT.x < imgsize.x);
	hN = h - heightAt(RIGHT);
	pipe.z = max(0, pipe.z + dt * A * hN * allowed / lx);

	allowed = float(UP.y >= 0);
	hN = h - heightAt(UP);
	pipe.y = max(0, pipe.y + dt * A * hN * allowed / ly);

	allowed = float(DOWN.y < imgsize.y);
	hN = h - heightAt(DOWN);
	pipe.w = max(0, pipe.w + dt * A * hN * allowed / ly);

	//clamp instead of min due to NaNs
	float K = clamp(imageLoad(d_map, pos).r * lx * ly / (dt * (pipe.x + pipe.y + pipe.z + pipe.w)),
					0, 1);

	pipe *= K;
	if (erase) {
		pipe = vec4(0);
	}
	
	imageStore(pipe_map, pos, pipe);
}//main

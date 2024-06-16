#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (rgba32f) uniform image2D pipe_map;
layout (r32f) uniform image2D b_map;
layout (r32f) uniform image2D d_map;

uniform float dt = 0.25;
uniform float lx = 1;
uniform float ly = 1;

uniform ivec2 size = ivec2(512, 512);

uniform float A = 1;

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

	float h = heightAt(pos); 
	vec4 pipe = imageLoad(pipe_map, pos);
	float hN;

	hN = h - heightAt(LEFT);
	pipe.x = max(0, pipe.x + dt * A * hN * lx);
	pipe.x *= float(pos.x > 0);

	hN = h - heightAt(RIGHT);
	pipe.z = max(0, pipe.z + dt * A * hN * lx);
	pipe.z *= float(pos.x < size.x - 1);

	hN = h - heightAt(UP);
	pipe.y = max(0, pipe.y + dt * A * hN * ly);
	pipe.y *= float(pos.y > 0);

	hN = h - heightAt(DOWN);
	pipe.w = max(0, pipe.w + dt * A * hN * ly);
	pipe.w *= float(pos.y < size.y - 1);

	float sum = pipe.x + pipe.y + pipe.z + pipe.w;
	float water = lx * ly * imageLoad(d_map, pos).r;
	//clamp instead of min due to NaNs
	float K = clamp(water / (dt * sum), 0, 1);

	pipe *= sum > water ? K : 1;
	
	imageStore(pipe_map, pos, pipe);
}//main

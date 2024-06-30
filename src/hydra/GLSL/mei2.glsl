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

uniform bool tile_x = false;
uniform bool tile_y = false;

#define LEFT   (pos + ivec2(-1, 0))
#define RIGHT  (pos + ivec2(+1, 0))
#define UP     (pos + ivec2(0, -1))
#define DOWN   (pos + ivec2(0, +1))

//  1y -1
//0x  2z
//  3w +1

float heightAt(ivec2 pos) {
	if (tile_x) {
		pos.x += pos.x < 0 ? size.x : 0;
		pos.x -= pos.x >= size.x ? size.x : 0;
	}
	if (tile_y) {
		pos.y += pos.y < 0 ? size.y : 0;
		pos.y -= pos.y >= size.y ? size.y : 0;
	}

	pos = clamp(pos, ivec2(0), size - 1);

    return imageLoad(b_map, pos).r + imageLoad(d_map, pos).r;
}

void main(void) {
	ivec2 pos = ivec2(gl_GlobalInvocationID.xy);

	float h = heightAt(pos); 
	vec4 pipe = imageLoad(pipe_map, pos);
	float hN;

	hN = h - heightAt(LEFT);
	pipe.x = max(0, pipe.x + dt * A * hN * lx);

	hN = h - heightAt(RIGHT);
	pipe.z = max(0, pipe.z + dt * A * hN * lx);

	hN = h - heightAt(UP);
	pipe.y = max(0, pipe.y + dt * A * hN * ly);

	hN = h - heightAt(DOWN);
	pipe.w = max(0, pipe.w + dt * A * hN * ly);

	float sum = pipe.x + pipe.y + pipe.z + pipe.w;
	float water = lx * ly * imageLoad(d_map, pos).r;
	//clamp instead of min due to NaNs
	float K = clamp(water / (dt * sum), 0, 1);

	pipe *= sum > water ? K : 1;
	
	imageStore(pipe_map, pos, pipe);
}//main

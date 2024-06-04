#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D height_sampler;

layout (r32f) uniform image2D height_map;

uniform ivec2 tile_size = ivec2(32,32);
uniform vec2 tile_mult = vec2(1.0/512.0,1.0/512.0);

uniform int lifetime = 50;
uniform int iterations = 100;
uniform int seed = 1;

uniform float acceleration = 0.5;
uniform float max_velocity = 3.0;
uniform float drag = 0.9;

uniform float capacity_factor = 0.5;
uniform float erosion_strength = 0.25;
uniform float deposition_strength = 0.5;

uniform float max_change = 0.01;

// pcg3d hashing algorithm from:
// Author: Mark Jarzynski and Marc Olano
// Title: Hash Functions for GPU Rendering
// Journal: Journal of Computer Graphics Techniques (JCGT), vol. 9, no. 3, 21-38, 2020
uvec3 hash(uvec3 v) {
	v = v * 1664525u + 1013904223u;
	v.x += v.y * v.z; v.y += v.z * v.x; v.z += v.x * v.y;
	v ^= v >>16u;
	v.x += v.y * v.z; v.y += v.z*v.x; v.z += v.x*v.y;
	return v;
}

void erode(uvec2 base, int seed) {
	vec2 pos = (hash(uvec3(base.x, base.y, seed)).xy & (16384u - 1u)) / 8192.0;
	pos = (pos + base) * tile_size;

	float height = texture(height_sampler, tile_mult * pos).x;

	vec2 vel = vec2(
		height - texture(height_sampler, tile_mult * (pos + vec2(1, 0))).x,
		height - texture(height_sampler, tile_mult * (pos + vec2(0, 1))).x
	);

	vec2 dir = normalize(vel);

	float saturation = 0.0;
	
	for (int i = 0; i < lifetime; ++i) {
		float height = texture(height_sampler, tile_mult * pos).x;
		float height_vel = texture(height_sampler, tile_mult * (pos + dir)).x;
		float height_dir = texture(height_sampler, tile_mult * (pos + vec2(-dir.y, dir.x))).x;

		vel += acceleration * (
			(height - height_vel) * dir +
			(height - height_dir) * vec2(-dir.y, dir.x)
		);
		
		float len = min(length(vel), max_velocity);
		dir = normalize(vel);
		vel = dir * len;

		float capacity = capacity_factor * len * float(height > height_vel);

		float dif = capacity-saturation;

		dif *= dif > 0 ? erosion_strength : deposition_strength;
		dif = clamp(dif, -max_change, max_change);
		saturation += dif;
		
		ivec2 ipos = ivec2(pos);
		imageStore(height_map, ipos, imageLoad(height_map, ipos) - vec4(dif));

		pos += dir;
		
		vel *= drag;
	}//i loop
}

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	for (int j = 0; j < iterations; ++j) {
		erode(base, seed + j);
	}
}//main

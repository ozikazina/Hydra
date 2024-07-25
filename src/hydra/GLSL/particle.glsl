#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D height_sampler;
uniform sampler2D hardness_sampler;

layout (r32f) uniform image2D height_map;

uniform ivec2 size = ivec2(512,512);
uniform ivec2 tile_size = ivec2(32,32);
uniform vec2 tile_mult = vec2(1.0/512.0,1.0/512.0);

uniform int lifetime = 50;
uniform int iterations = 100;
uniform int seed = 1;

uniform float acceleration = 0.5;
uniform float lateral_acceleration = 1.0;
uniform float max_velocity = 3.0;
uniform float drag = 0.9;

uniform float capacity_factor = 0.5;
uniform float erosion_strength = 0.25;
uniform float deposition_strength = 0.5;

uniform float max_change = 0.01;

uniform bool use_hardness = false;
uniform bool invert_hardness = false;

uniform bool planet = false;

#define PI 3.14159265

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

	vec2 vel = acceleration * vec2(
		height - texture(height_sampler, tile_mult * (pos + vec2(1, 0))).x,
		height - texture(height_sampler, tile_mult * (pos + vec2(0, 1))).x
	);

	vec2 dir = normalize(vel);

	if (length(vel) < 1e-5) {
		vel = vec2(0,0);
		dir = vec2(1,0);
	}

	float saturation = 0.0;
	
	for (int i = 0; i < lifetime; ++i) {
		float dir_mult = (i & 1) == 0 ? 1.0 : -1.0; // swapping lateral checks prevents biased rotation
		float height = texture(height_sampler, tile_mult * pos).x;
		float height_vel = texture(height_sampler, tile_mult * (pos + dir)).x;
		float height_dir = texture(height_sampler, tile_mult * (pos + dir_mult * vec2(-dir.y, dir.x))).x;

		vec2 accel = acceleration * (
			(height - height_vel) * dir +
			lateral_acceleration * (height - height_dir) * dir_mult * vec2(-dir.y, dir.x)
		);

		if (planet) {
			accel.x *= 1 / max(sin(tile_mult.y * pos.y * PI), 1e-3);
		}

		vel += accel;

		float len = min(length(vel), max_velocity);
		dir = normalize(vel);

		float true_len;
		if (planet) {
			true_len = min(length(vel * vec2(sin(tile_mult.y * pos.y * PI), 1)), max_velocity);
		}
		else {
			true_len = len;
		}

		vel = dir * len;

		float capacity = capacity_factor * true_len * float(height > height_vel);

		float dif = capacity-saturation;

		float erosion_str = erosion_strength;
		
		if (use_hardness) {
			float hardness = texture(hardness_sampler, tile_mult * pos).x;
			if (!invert_hardness) hardness = 1 - hardness;
			erosion_str *= clamp(hardness, 0, 1);
		}

		dif *= dif >= 0 ? erosion_str : deposition_strength;

		dif = clamp(dif, -max_change, max_change);
		saturation += dif;
		
		ivec2 ipos = ivec2(floor(pos));
		imageStore(height_map, ipos, imageLoad(height_map, ipos) - vec4(dif));

		pos += dir;

		pos.x += pos.x < 0 ? size.x : pos.x >= size.x ? -size.x : 0;
		pos.y += pos.y < 0 ? size.y : pos.y >= size.y ? -size.y : 0;
		
		vel *= drag;
	}//i loop
}

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	for (int j = 0; j < iterations; ++j) {
		erode(base, seed + j);
	}
}//main

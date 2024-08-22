#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D height_sampler;

layout (r32f) uniform image2D height_map;
layout (rgba32f) uniform image2D color_map;

uniform ivec2 size = ivec2(512,512);
uniform ivec2 tile_size = ivec2(32, 32);
uniform vec2 tile_mult = vec2(1.0/512.0,1.0/512.0);

uniform int iterations = 100 * 20;
uniform int lifetime = 50;

uniform float acceleration = 0.5;
uniform float lateral_acceleration = 1.0;

uniform float erosion_strength = 0.75;
uniform float deposition_strength = 0.5;
uniform float max_velocity = 2.0;

uniform float drag = 0.8;
uniform float capacity_factor = 0.8;
uniform float color_strength = 0.5;

uniform bool tile_x = false;
uniform bool tile_y = false;
uniform bool planet = false;

uniform int seed = 1;

#define PI 3.14159265

ivec2 pos_at(ivec2 org) {
	if (tile_x) {
		org.x += org.x >= size.x ? -size.x : 0;
	}
	if (tile_y) {
		org.y += org.y >= size.y ? -size.y : 0;
	}
	return org;
}

void colorize(vec2 pos, vec4 col, float strength) {
	pos -= vec2(0.5,0.5);
	vec2 factor = pos - floor(pos);
	ivec2 corner = ivec2(floor(pos)); //has to have floor

	//X Y
	float f = strength * (1-factor.x) * (1-factor.y);
	vec4 surf_color = imageLoad(color_map, corner);
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, corner, surf_color);

	//X+1 Y
	f = strength * factor.x * (1-factor.y);
	ivec2 coords = pos_at(corner + ivec2(1,0));
	surf_color = imageLoad(color_map, coords);
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, coords, surf_color);
	
	//X Y+1
	f = strength * (1-factor.x) * factor.y;
	coords = pos_at(corner + ivec2(0,1));
	surf_color = imageLoad(color_map, coords);
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, coords, surf_color);
	
	//X+1 Y+1
	f = strength * factor.x * factor.y;
	coords = pos_at(corner + ivec2(1,1));
	surf_color = imageLoad(color_map, coords);
	surf_color = mix(surf_color, col, f);
	imageStore(color_map, coords, surf_color);
}

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

void erode(ivec2 base, int seed) {
	vec2 pos = (hash(uvec3(base.x, base.y, seed)).xy & (8192u - 1u)) / 8192.0;
	pos = (pos + base) * tile_size;

	float h = texture(height_sampler, tile_mult * pos).x;

	vec2 vel = acceleration * vec2(
		h - texture(height_sampler, tile_mult * (pos + vec2(1, 0))).x,
		h - texture(height_sampler, tile_mult * (pos + vec2(0, 1))).x
	);

	vec2 dir = normalize(vel);

	if (length(vel) < 1e-5) {
		vel = vec2(0,0);
		dir = vec2(1,0);
	}

	float saturation = 0;

	vec4 col = imageLoad(color_map, ivec2(pos));
	
	for (int i = 0; i < lifetime; ++i) {
		ivec2 ipos = ivec2(pos);
		
		h = texture(height_sampler, tile_mult * pos).x;
		float height_vel = texture(height_sampler, tile_mult * (pos + dir)).x;
		float height_dir = texture(height_sampler, tile_mult * (pos + vec2(-dir.y, dir.x))).x;

		vec2 accel = acceleration * (
			(h - height_vel) * dir +
			lateral_acceleration * (h - height_dir) * vec2(-dir.y, dir.x)
		);

		if (planet) {
			accel.x *= 1 / max(sin(tile_mult.y * pos.y * PI), 1e-3);
		}

		vel += accel;

		vel *= float(h >= height_vel);
		
		float len = min(length(vel), max_velocity);
		dir = normalize(vel);
		vel = dir * len;

		float capacity = capacity_factor * len;

		float dif = capacity-saturation;
		
		dif *= dif > 0 ? erosion_strength : deposition_strength;
		h -= dif;
		imageStore(height_map, ipos, vec4(h,0,0,1));
		saturation += dif;

		float color_strength_adj = color_strength * (planet ? sin(tile_mult.y * pos.y * PI) : 1);
		col = mix(col, imageLoad(color_map, ipos), (1 - color_strength_adj) * float(dif > 0));

		if (dif < 0) {	//deposit
			colorize(pos, col, color_strength_adj);
		}

		pos += dir;

		if (tile_x) {
			pos.x += pos.x < 0 ? size.x : pos.x >= size.x ? -size.x : 0;
		}
		if (tile_y) {
			pos.y += pos.y < 0 ? size.y : pos.y >= size.y ? -size.y : 0;
		}

		vel *= drag;
	}//i loop
}

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	for (int j = 0; j < iterations; ++j) {
		erode(base, seed + j);
	}
}//main
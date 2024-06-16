#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform sampler2D height_sampler;
layout (r32f) uniform image2D flow;

uniform ivec2 tile_size = ivec2(32, 32);
uniform vec2 tile_mult = vec2(1.0/512.0,1.0/512.0);

uniform int iterations = 200;
uniform int lifetime = 50;
uniform float acceleration = 0.5;
uniform float max_velocity = 2.0;
uniform float drag = 0.8;
uniform float strength = 0.10;

uniform int seed = 1;

void add_flow(vec2 pos, float strength) {
	pos -= vec2(0.5,0.5);
	vec2 factor = pos - floor(pos);
	ivec2 corner = ivec2(floor(pos));
	
	//X Y
	float f = strength * (1-factor.x) * (1-factor.y);
	float surf = imageLoad(flow, corner).x;
	imageStore(flow, corner, vec4(surf * (1-f) + f));
	
	//X+1 Y
	f = strength * factor.x * (1-factor.y);
	surf = imageLoad(flow, corner + ivec2(1,0)).x;
	imageStore(flow, corner + ivec2(1,0), vec4(surf * (1-f) + f));

	//X Y+1
	f = strength * (1-factor.x) * factor.y;
	surf = imageLoad(flow, corner + ivec2(0,1)).x;
	imageStore(flow, corner + ivec2(0,1), vec4(surf * (1-f) + f));
	
	//X+1 Y+1
	f = strength * factor.x * factor.y;
	surf = imageLoad(flow, corner + ivec2(1,1)).x;
	imageStore(flow, corner + ivec2(1,1), vec4(surf * (1-f) + f));
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

void run(ivec2 base, int seed) {
	vec2 pos = (hash(uvec3(base.x, base.y, seed)).xy & (16384u - 1u)) / 8192.0;
	pos = (pos + base) * tile_size;

	float h = texture(height_sampler, tile_mult * pos).x;
	vec2 vel = acceleration * vec2(
		h - texture(height_sampler, tile_mult * (pos + vec2(1, 0))).x,
		h - texture(height_sampler, tile_mult * (pos + vec2(0, 1))).x
	);

	vec2 dir = normalize(vel);

	
	for (int i = 0; i < lifetime; ++i) {
		h = texture(height_sampler, tile_mult * pos).x;
		float height_vel = texture(height_sampler, tile_mult * (pos + dir)).x;
		float height_dir = texture(height_sampler, tile_mult * (pos + vec2(-dir.y, dir.x))).x;
		
		vel += acceleration * (
			(h - height_vel) * dir +
			(h - height_dir) * vec2(-dir.y, dir.x)
		);
		
		float len = min(length(vel), max_velocity);
		dir = normalize(vel);
		vel = dir * len;

		add_flow(pos, strength);
		
		pos += dir;
		vel *= drag;
	}
}

void main(void) {
	ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	for (int j = 0; j < iterations; ++j) {
		run(base, seed + j);
	}
}//main
#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D map;

float toLinear(float C) {
	if (C <= 0.04045)
		return C / 12.92;
	else
		return pow(((C + 0.055) / 1.055), 2.4);
}

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	vec4 col = imageLoad(map, base);
	col.x = toLinear(col.x);
	//col.y = toLinear(col.y);
	//col.z = toLinear(col.z);
    imageStore(map, base, col);
}
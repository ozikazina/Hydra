#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

layout (r32f) uniform image2D inMap;
layout (r32f) uniform image2D outMap;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	vec4 col = imageLoad(inMap, base);
    float val = imageLoad(inMap, base+ivec2(-1,0)).x +
        imageLoad(inMap, base+ivec2(1,0)).x +
        imageLoad(inMap, base+ivec2(0,1)).x + 
        imageLoad(inMap, base+ivec2(0,-1)).x;

    val *= 0.25;
    col.x = col.x == 0.0 || isnan(col.x) ? val : col.x;
    imageStore(outMap, base, col);
}
#version 430

layout(local_size_x = 1, local_size_y = 1, local_size_z = 1) in;

layout (r32f) uniform image2D inMap;
layout (r32f) uniform image2D outMap;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
	
	vec4 col = imageLoad(inMap, base);
    if (col.x == 0.0 || isnan(col.x)) {
        float l = imageLoad(inMap, base+ivec2(-1,0)).x;
        float r = imageLoad(inMap, base+ivec2(1,0)).x;
        float u = imageLoad(inMap, base+ivec2(0,1)).x;
        float d = imageLoad(inMap, base+ivec2(0,-1)).x;
        col.x = 0.25 * (l+r+u+d);
    }
    imageStore(outMap, base, col);
}
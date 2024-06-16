#version 430

layout(local_size_x = 32, local_size_y = 32, local_size_z = 1) in;

uniform bool is_horizontal;
layout (r32f) uniform image2D img_in;
layout (r32f) uniform image2D img_out;

void main(void) {
    ivec2 base = ivec2(gl_GlobalInvocationID.xy);
    
    float weights[5] = float[](0.15246914402033734, 0.22184129554377693, 0, 0.22184129554377693, 0.15246914402033734);
    
    float color = imageLoad(img_in, base).x;
    color *= color < 0 ? 0.25137912087177144 : 1;
    
    if (is_horizontal) {
        for (int i = -2; i <= 2; i++) 
        {
            float val = imageLoad(img_in, base + ivec2(i, 0)).x;
            color += min(val, 0) * weights[i + 2];
        }
    } else {
        for (int i = -2; i <= 2; i++) {
            float val = imageLoad(img_in, base + ivec2(0, i)).x;
            color += min(val, 0) * weights[i + 2];
        }
    }

    imageStore(img_out, base, vec4(color));
}
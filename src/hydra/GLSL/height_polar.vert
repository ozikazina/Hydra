#version 430

layout (location=0) in vec3 position;
uniform mat4 resize_matrix = mat4(1.0);

out vec4 pos;

void main(void) {
	vec4 npos = vec4(position, 1.0) * resize_matrix;

    vec3 dif = normalize(npos.xyz);
    dif /= max(abs(dif.z), 1e-2);

    float h = length(npos.xyz);

    pos = vec4(h, 0, 0, 0);

	gl_Position = vec4(1 * dif.x, 1 * dif.y, -0.5 + 0.1 * h + (dif.z - 1), 1.0);
}
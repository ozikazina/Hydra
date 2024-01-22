#version 430

out vec4 FragColor;
in vec4 pos;

uniform float scale = 1.0;

void main(void) {
	float height = (1-pos.z) * scale;
	FragColor = vec4(height, height, height, 1.0);
}
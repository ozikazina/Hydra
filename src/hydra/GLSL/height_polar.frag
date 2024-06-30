#version 430

out vec4 FragColor;
in vec4 pos;

uniform float scale = 1.0;
uniform float offset = 0.0;

void main(void) {
	float height = (pos.x + offset) * scale;
	FragColor = vec4(height, 0, 0, 1.0);
}
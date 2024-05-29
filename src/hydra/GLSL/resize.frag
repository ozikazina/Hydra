#version 430

out vec4 FragColor;
in vec2 uv;

uniform sampler2D in_texture;

void main(void) {
	FragColor = texture(in_texture, uv);
}
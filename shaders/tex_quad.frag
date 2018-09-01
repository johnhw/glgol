#version 430 core
in vec2 texCoord;
out vec4 fragColor;
uniform sampler2D tex;

void main() {
    // We're not interested in changing the alpha value
    fragColor = texture(tex, texCoord);
}
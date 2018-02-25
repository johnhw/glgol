

// These are sent to the fragment shader
out vec2 texCoord;      // UV coordinates of texture
layout(location=0) in vec2 position;

void main()
{
    gl_Position = vec4(position.xy, 0, 1);
    // tex-coords are just 0-1, 0-1
    texCoord = position / 2.0 + 0.5;
}
#version 330 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;

layout(location=0) out vec4 frag_color;


void main(void)
{          
     // look up the texture at the UV coordinates
    frag_color = texture2D(quadTexture, vec2(texCoord.x, texCoord.y)).xxxx;

}
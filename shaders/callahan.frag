#version 430 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;
uniform sampler2D callahanTexture;
layout(location=0) out vec4 frag_color;


void main(void)
{               
    ivec4 q = ivec4(textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).wxzy * 15);
    float x = (q.x * 16 + q.y) / 256.0;
    float y = (q.z * 16 + q.w) / 256.0;
    float out_cell = texture(callahanTexture, vec2(y, x)).x;
    frag_color = vec4(out_cell,out_cell,out_cell,1);

}
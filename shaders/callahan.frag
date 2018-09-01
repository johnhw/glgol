#version 430 core
#define M_PI 3.1415926535897932384626433832795
// count number of times the shader was used
layout (binding = 0, offset = 0) uniform atomic_uint population;

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;
uniform sampler2D callahanTexture;
layout(location=0) out float frag_color;
uniform int frameOffset;

void main(void)
{               
    ivec4 q = ivec4(textureGatherOffset(quadTexture, texCoord, ivec2(-frameOffset,-frameOffset)).wxzy * 15);    
    frag_color = texelFetch(callahanTexture, ivec2((q.z * 16 + q.w), (q.x * 16 + q.y)), 0).x;          
    if(frag_color>0.0)
        atomicCounterIncrement(population);
}
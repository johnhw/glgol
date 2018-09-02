#version 430 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D lifeTex;
uniform sampler2D callahanLUT;
layout(location=0) out float nextGen;
uniform int frameOffset;

void main(void)
{               
    ivec4 q = ivec4(textureGatherOffset(lifeTex, texCoord, ivec2(-frameOffset,-frameOffset)).wxzy * 15);    
    nextGen = texelFetch(callahanLUT, ivec2((q.z * 16 + q.w), (q.x * 16 + q.y)), 0).x;  
    
}
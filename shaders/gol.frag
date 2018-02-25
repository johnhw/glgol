#version 330 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;

layout(location=0) out vec4 frag_color;


void main(void)
{          
     // look up the texture at the UV coordinates
    
    float a = textureOffset(quadTexture, texCoord, ivec2(0,0)).x;
    float acc=0;
    acc += textureOffset(quadTexture, texCoord, ivec2(-1,-1)).x;
    acc += textureOffset(quadTexture, texCoord, ivec2(-1,0)).x;
    acc += textureOffset(quadTexture, texCoord, ivec2(-1,1)).x;
    
    acc += textureOffset(quadTexture, texCoord, ivec2(0,-1)).x;
    acc += textureOffset(quadTexture, texCoord, ivec2(0,1)).x;

    acc += textureOffset(quadTexture, texCoord, ivec2(1,-1)).x;
    acc += textureOffset(quadTexture, texCoord, ivec2(1,0)).x;
    acc += textureOffset(quadTexture, texCoord, ivec2(1,1)).x;

    float low = step(1.5, acc);
    float left = step(2.5, acc);
    float right = step(3.5, acc);

    float out_cell = left - right + step(0.5, a) * low  - right;

  
    frag_color = vec4(out_cell,out_cell,out_cell,1);

}
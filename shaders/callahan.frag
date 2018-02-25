#version 430 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;
uniform sampler2D callahanTexture;
layout(location=0) out vec4 frag_color;


void main(void)
{          
     // look up the texture at the UV coordinates
    
    // could do single unfiltered read here
    /*float a = textureOffset(quadTexture, texCoord, ivec2(-1,-1)).x;
    float c = textureOffset(quadTexture, texCoord, ivec2(0,-1)).x;
    float b = textureOffset(quadTexture, texCoord, ivec2(-1, 0)).x;
    float d = textureOffset(quadTexture, texCoord, ivec2(0, 0)).x;
*/
    
    float a = textureGatherOffset(quadTexture, texCoord, ivec2(-1,-1)).w;
    float c = textureGatherOffset(quadTexture, texCoord, ivec2(0,-1)).w;
    float b = textureGatherOffset(quadTexture, texCoord, ivec2(-1, 0)).w;
    float d = textureGatherOffset(quadTexture, texCoord, ivec2(0, 0)).w;

    a = textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).w;
    c = textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).z;
    b = textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).x;
    d = textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).y;
    vec4 q = textureGatherOffset(quadTexture, texCoord, ivec2(-1, -1)).wxzy;


    //vec4 q = vec4(a,b,c,d);

    int ia = int(q.x * 15);
    int ib = int(q.y * 15);
    int ic = int(q.z * 15);
    int id = int(q.w * 15);

    int x = ia * 16 + ib;
    int y = ic * 16 + id;

    float out_cell = texture(callahanTexture, vec2(y/256.0, x/256.0)).x;
        
    
    frag_color = vec4(out_cell,out_cell,out_cell,1);

}
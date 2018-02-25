#version 330 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 texCoord;

uniform sampler2D quadTexture;
uniform float in_size;

layout(location=0) out vec4 frag_color;


void main(void)
{          

    int odd_row = int(texCoord.x * 2 * in_size) % 2;
    int odd_col = int(texCoord.y * 2 * in_size) % 2;
    
    float fpacked = texture2D(quadTexture, texCoord).x;
    int pcked = int(fpacked*15);
    int a = ((pcked >> 0) & 1);
    int b = ((pcked >> 1) & 1);
    int c = ((pcked >> 2) & 1);
    int d = ((pcked >> 3) & 1);
        
    float col;
    if(odd_row==0 && odd_col==0) 
        col = a;
    if(odd_row==0 && odd_col==1) 
        col = b;
    if(odd_row==1 && odd_col==0) 
        col = c;
    if(odd_row==1 && odd_col==1) 
        col = d;

    col = col;
     // look up the texture at the UV coordinates
    frag_color = vec4(col, col, col, 1);

}
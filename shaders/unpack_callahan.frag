#version 430 core
#define M_PI 3.1415926535897932384626433832795
// count number of times the shader was used
 layout(std430, binding = 0) buffer population
 {
     int popCount;
 };

// from the vertex shader
in vec2 texCoord;

uniform sampler2D tex;

uniform float in_size;
layout(location=0) out vec4 fragColor;
flat in float fragStrobeLight;


void main(void)
{          

    int odd_row = int(texCoord.x * 2 * in_size) % 2;
    int odd_col = int(texCoord.y * 2 * in_size) % 2;
    
    float fpacked = texture(tex, texCoord).x;
    int pcked = int(fpacked*15);
    int a = ((pcked >> 0) & 1);
    int b = ((pcked >> 1) & 1);
    int c = ((pcked >> 2) & 1);
    int d = ((pcked >> 3) & 1);
        
    float col;

    // select the appropriate pixel to write out
    col =   a* (1-odd_row) * (1-odd_col)  +   b * (1-odd_row) * odd_col +
            c * (odd_row) * (1-odd_col) +     d * (odd_row) * odd_col;

     // look up the texture at the UV coordinates
    fragColor = vec4(col, col, col, fragStrobeLight);

    if(col>0.0)
        atomicAdd(popCount, 1);
}
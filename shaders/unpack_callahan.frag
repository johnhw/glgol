#version 330 core
#define M_PI 3.1415926535897932384626433832795

// from the vertex shader
in vec2 v_tex;

uniform sampler2D tex;
uniform float in_size;

layout(location=0) out vec4 frag_color;

uniform int frame;
uniform int strobe;

void main(void)
{          
    float frame_pos = float(frame % strobe) / strobe;    

    if(frame_pos==0)
        frame_pos=1.0;
    else
        frame_pos=0.1;
    

    int odd_row = int(v_tex.x * 2 * in_size) % 2;
    int odd_col = int(v_tex.y * 2 * in_size) % 2;
    
    float fpacked = texture2D(tex, v_tex).x;
    int pcked = int(fpacked*15);
    int a = ((pcked >> 0) & 1);
    int b = ((pcked >> 1) & 1);
    int c = ((pcked >> 2) & 1);
    int d = ((pcked >> 3) & 1);
        
    float col;

    // select the appropriate pixel to write out
    col = (1-odd_row) * (1-odd_col) * a + (1-odd_row)*odd_col * b
     + (odd_row)*(1-odd_col)*c + (odd_row)*odd_col*d;

     // look up the texture at the UV coordinates
    frag_color = vec4(col, col, col, frame_pos*(col+0.55));

}
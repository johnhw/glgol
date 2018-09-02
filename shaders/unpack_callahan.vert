#version 430 core
                
in vec2 pos;    
out vec2 texCoord;
flat out float fragStrobeLight;

uniform int frame;
uniform int strobe;    
uniform float strobe_exp;

void main() {
    // apply strobing
    float strobeLight = float(frame % strobe) / float(strobe);   
    strobeLight = pow(1.0-strobeLight, strobe_exp);
    


    gl_Position = vec4(pos*2, 0.0, 1.0);
    texCoord = pos/2.0 + 0.5;
    fragStrobeLight = strobeLight;
}
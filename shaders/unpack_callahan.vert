#version 430 core
                
in vec2 pos;    
out vec2 texCoord;

void main() {
    gl_Position = vec4(pos*2, 0.0, 1.0);
    texCoord = pos/2.0 + 0.5;
}
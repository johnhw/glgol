#version 430 core
                
in vec2 pos;    
out vec2 texCoord;
uniform mat4 projection, modelview;

void main() {
    gl_Position = projection * modelview * vec4(pos, 0.0, 1.0);                    
    texCoord = pos/2.0 + 0.5;
}
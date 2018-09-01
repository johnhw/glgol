#version 430 core
                
in vec2 in_vert;    
in vec2 in_tex;            
out vec2 v_tex;

void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    v_tex = in_tex;

}
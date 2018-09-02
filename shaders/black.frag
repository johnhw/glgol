#version 430 core

layout(location=0) out vec4 fragColor;

uniform float alpha;

void main(void)
{          
    fragColor= vec4(0.0, 0.0, 0.0, alpha);    
}
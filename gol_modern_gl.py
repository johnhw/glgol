'''
    Renders a traingle that has all RGB combinations
'''

import moderngl
import numpy as np
import modern_gl_skeleton as skel
import time
import lifeparsers
from callahan import pack_life, load_life, create_callahan_table
import os

def shader_from_file(ctx, vtx, frag):
    with open(os.path.join("shaders",vtx)) as v:
        vertex_shader = v.read()
    with  open(os.path.join("shaders",frag)) as f:
        frag_shader = f.read()
    return ctx.program(vertex_shader=vertex_shader, fragment_shader=frag_shader)
    
def modulate_uniform(prog):    
    uniform = prog.get("col_mod", None)
    clock = np.array([time.clock()])
    uniform.write(clock.astype("f4").tobytes())

quad = np.array([[-1,-1,0,0],[-1,1,0,1], [1,1,1,1], [1,-1,1,0]]).astype('f4')
quad_ixs = np.array([0,1,3,2]).astype('u4')


def fit_life(ctx, packed, lif_size):
    # upload, centered, into texture
    w, h = lif_size, lif_size # size of FBO texture
    x_off = (w - packed.shape[1]) // 2
    y_off = (h - packed.shape[0]) // 2
    # normalize for 0.0-1.0 texture format and upload
    packed = packed.astype(np.float32) / 15.0
    
    # upload as texture
    tex = ctx.texture((lif_size, lif_size), 1, dtype='f4')    
    tex.write(packed, viewport=(x_off, y_off, packed.shape[1], packed.shape[0]))        
    tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
    return tex

def load_life_texture(ctx, fname, size):
    lif = load_life(fname)
    return fit_life(ctx, pack_life(lif), size)

class SimpleColorTriangle:

    def __init__(self):
        self.skeleton = skel.GLSkeleton(draw_fn=self.render, window_size=(1024, 1024))
        self.ctx = self.skeleton.get_context()
        
        # load life pattern
        self.pat_tex = load_life_texture(self.ctx, "../../qlife/lifep/cordtoss.lif", 512)

        self.lif_size = 512
        self.fbo_texture = self.ctx.texture((self.lif_size, self.lif_size), components=1, dtype='f1')
        
        self.fbo = self.ctx.framebuffer(color_attachments=(self.fbo_texture), depth_attachment=None)
        self.fbo_scope = self.ctx.scope(self.fbo)
        
        successors, s_table, view_table = create_callahan_table()        

        # upload the reshaped, normalised texture
        
        self.callahan_texture = self.ctx.texture((256,256), components=1, dtype='f4', data=(s_table.reshape(256,256)/15.0).astype('f4'))        
        self.callahan_texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
        
        self.unpack_prog = shader_from_file(self.ctx, "unpack_callahan.vert", "unpack_callahan.frag")
        self.tex_prog = self.ctx.program(
            vertex_shader='''
                #version 330
                
                in vec2 in_vert;    
                in vec2 in_tex;            
                out vec3 v_color;    // Goes to the fragment shader
                out vec2 v_tex;
                uniform float col_mod;
                void main() {
                    gl_Position = vec4(in_vert, 0.0, 1.0);
                    v_color = vec3(1.,0.,1.)*sin(col_mod);
                    v_tex = in_tex;

                }
            ''',
            fragment_shader='''
                #version 330
                in vec3 v_color;
                in vec2 v_tex;
                out vec4 f_color;
                uniform sampler2D tex;
                
                void main() {
                    // We're not interested in changing the alpha value
                    f_color = vec4(v_color, 1.0) + texture(tex, v_tex);
                }
            ''',
        )
   

        self.vbo = self.ctx.buffer(quad.tobytes())
        self.ibo = self.ctx.buffer(quad_ixs.tobytes())
        
        # We control the 'in_vert' and `in_color' variables
        self.unpack_vao = self.ctx.simple_vertex_array(self.unpack_prog, self.vbo, 
                                                'in_vert', 'in_tex', index_buffer=self.ibo)

        self.tex_vao = self.ctx.simple_vertex_array(self.tex_prog, self.vbo, 
                                                'in_vert', 'in_tex', index_buffer=self.ibo)

        in_size = self.unpack_prog["in_size"]
        in_size.value = self.lif_size 
        
        self.skeleton.after(1.0, print, "hello", repeat=True)
        
        self.skeleton.after(10.0, self.skeleton.exit)
        self.skeleton.run()

    def render(self):
        self.ctx.viewport = (0, 0, self.skeleton.window.width, self.skeleton.window.height)
        self.ctx.clear(0.0, 0.0, 0.0)
        with self.fbo_scope:
            self.pat_tex.use()
            self.unpack_vao.render(mode=moderngl.TRIANGLE_STRIP)
        
        self.fbo_texture.use()
        self.tex_vao.render(mode=moderngl.TRIANGLE_STRIP)
        
        

SimpleColorTriangle()
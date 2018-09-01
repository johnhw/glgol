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
    

def fit_life(ctx, packed, lif_size):
    # upload, centered, into texture
    w, h = lif_size, lif_size # size of FBO texture
    x_off = (w - packed.shape[1]) // 2
    y_off = (h - packed.shape[0]) // 2
    # normalize for 0.0-1.0 texture format and upload
    packed = packed.astype(np.float32) / 15.0
    
    # upload as texture
    tex = square_red_texture(ctx, lif_size, dtype='f4')    
    tex.write(packed, viewport=(x_off, y_off, packed.shape[1], packed.shape[0]))        
    
    return tex

def load_life_texture(ctx, fname, size):
    lif = load_life(fname)
    return fit_life(ctx, pack_life(lif), size)

def square_red_texture(ctx, size, dtype='f1'):
    texture = ctx.texture((size, size), components=1, dtype=dtype)        
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    return texture

class FBO:
    def __init__(self, ctx, size):
        self.texture = square_red_texture(ctx, size)        
        self.fbo = ctx.framebuffer(color_attachments=self.texture, depth_attachment=None)
        self.scope = ctx.scope(self.fbo)
        self.ctx = ctx
        self.size = size
        self.offset = 0

    def use(self):
        self.texture.use()

    def __enter__(self):        
        self.scope.__enter__()
        self.ctx.viewport = (self.offset,self.offset,self.size+self.offset,self.size+self.offset)

    def __exit__(self, type, value, tb):
        self.scope.__exit__(type, value, tb)


class SimpleColorTriangle:

    def __init__(self):
        self.skeleton = skel.GLSkeleton(draw_fn=self.render, window_size=(800, 800))
        self.ctx = self.skeleton.get_context()
        self.frame = 0

        # load life pattern
        self.lif_size = 1024
        self.pat_tex = load_life_texture(self.ctx, "breeder.lif", self.lif_size)

        self.fbo_texture = square_red_texture(self.ctx, self.lif_size)        
        self.fbo = self.ctx.framebuffer(color_attachments=(self.fbo_texture), depth_attachment=None)
        self.fbo_scope = self.ctx.scope(self.fbo)

        self.back = FBO(self.ctx, self.lif_size)
        #self.fbo_texture_back = square_red_texture(self.ctx, self.lif_size)        
        #self.fbo_back = self.ctx.framebuffer(color_attachments=(self.fbo_texture_back), depth_attachment=None)
        #self.fbo_scope_back = self.ctx.scope(self.fbo_back)
        
        self.display = FBO(self.ctx, self.lif_size * 2)
        
        successors, s_table, view_table = create_callahan_table()        

        # upload the reshaped, normalised texture        
        self.callahan_texture = square_red_texture(self.ctx, 256, dtype='f4')
        self.callahan_texture.write(s_table.reshape(256,256)/15.0)
        
        self.unpack_prog = shader_from_file(self.ctx, "unpack_callahan.vert", "unpack_callahan.frag")
        self.gol_prog = shader_from_file(self.ctx, "callahan.vert", "callahan.frag")
        self.tex_prog = shader_from_file(self.ctx, "tex_quad.vert", "tex_quad.frag")        

        quad = np.array([[-1,-1,0,0],[-1,1,0,1], [1,1,1,1], [1,-1,1,0]]).astype('f4')
        quad_ixs = np.array([0,1,3,2]).astype('u4')
        vbo = self.ctx.buffer(quad.tobytes())
        ibo = self.ctx.buffer(quad_ixs.tobytes())
        
        # We control the 'in_vert' and `in_color' variables
        self.unpack_vao = self.ctx.simple_vertex_array(self.unpack_prog, vbo, 
                                                'in_vert', 'in_tex', index_buffer=ibo)
        self.gol_vao = self.ctx.simple_vertex_array(self.gol_prog, vbo, 
                                                'in_vert', 'in_tex', index_buffer=ibo)
        self.tex_vao = self.ctx.simple_vertex_array(self.tex_prog, vbo, 
                                                'in_vert', 'in_tex', index_buffer=ibo)

        self.unpack_prog["in_size"].value = self.lif_size
        self.gol_prog["quadTexture"].value = 0
        self.gol_prog["callahanTexture"].value = 1
        self.skeleton.run()

    def render(self):
        
        self.ctx.clear(0.0, 0.0, 0.0)
        # initial copy to the framebuffer
        if self.frame==0:
            with self.fbo_scope:
                self.ctx.viewport = (0,0,self.lif_size, self.lif_size)
                self.pat_tex.use()
                self.tex_vao.render(mode=moderngl.TRIANGLE_STRIP)

        frame_offset = self.frame % 2
        with self.fbo_scope_back:
            self.ctx.viewport = (0,0,self.lif_size, self.lif_size)
            self.fbo_texture.use(0)
            self.callahan_texture.use(1)
            self.gol_prog["frameOffset"].value = frame_offset
            self.gol_vao.render(mode=moderngl.TRIANGLE_STRIP)
        

            
        self.display.offset = -frame_offset
        with self.display:                          
             self.fbo_texture_back.use()
             self.unpack_vao.render(mode=moderngl.TRIANGLE_STRIP)
            
        self.ctx.viewport = (0, 0, self.skeleton.window.width, self.skeleton.window.height)
        self.display.texture.build_mipmaps()
        self.display.use()
        
        self.tex_vao.render(mode=moderngl.TRIANGLE_STRIP)
        self.frame += 1
        self.fbo_scope, self.fbo_scope_back = self.fbo_scope_back, self.fbo_scope
        self.fbo_texture, self.fbo_texture_back = self.fbo_texture_back, self.fbo_texture
        
        

SimpleColorTriangle()
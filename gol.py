import numpy as np
import pyglet
from pyglet.gl import *

import json
# sphere stuff
import pyspheregl.utils.glskeleton as skeleton
import pyspheregl.utils.np_vbo as np_vbo
import pyspheregl.utils.shader as shader
from pyspheregl.utils.shader import shader_from_file
from pyspheregl.utils.np_vbo import VBuf, IBuf


from pyspheregl.utils.graphics_utils import make_unit_quad_tile
import time
import timeit
# high precision timing
wall_clock = timeit.default_timer

import os
import lifeparsers

class Texture:
    def __init__(self, target, id):
        self.target = target
        self.id = id

def create_callahan_table():
    """Generate the lookup table for the cells."""
    successors = {}
    # map predecessors to successor
    s_table = np.zeros((16,16,16,16), dtype=np.float32)
    # map 16 "colours" to 2x2 cell patterns
    view_table = np.zeros((16,2,2), dtype=np.float32)

    def life(*args):
        n = sum(args[1:])
        n |= args[0] # if we or with the cell value, we can just test == 3        
        if n==3:
            return 1
        else:
            return 0

    # abcd
    # eFGh
    # iJKl
    # mnop

    # pack format 
    # ab
    # cd
    # packed = a + (b<<1) + (c<<2) + (d<<3)

    # generate all 16 bit strings
    for iv in range(65536):
        bv = [(iv>>z)&1 for z in range(16)]
        a,b,c,d,e,f,g,h,i,j,k,l,m,n,o,p = bv
        
        # compute next state of the inner 2x2
        nw = life(f, a, b, c, e, g, i, j, k)
        ne = life(g, b, c, d, f, h, j, k, l)
        sw = life(j, e, f, g, i, k, m, n, o)
        se = life(k, f, g, h, j, l, n, o, p)

        centre_code = f | (g<<1) | (j<<2) | (k<<3)
        view_table[centre_code] = [[f,g], [j,k]]

        # compute the index of this 4x4
        nw_code = a | (b<<1) | (e<<2) | (f<<3)
        ne_code = c | (d<<1) | (g<<2) | (h<<3)
        sw_code = i | (j<<1) | (m<<2) | (n<<3)
        se_code = k | (l<<1) | (o<<2) | (p<<3)
        
        # compute the state for the 2x2
        next_code = nw | (ne<<1) | (sw<<2) | (se<<3)

        # get the 4x4 index, and write into the table
        this_code = nw_code | (ne_code<<4) | (sw_code<<8) | (se_code<<12) 
        successors[this_code] = next_code
        s_table[nw_code, ne_code, sw_code, se_code] = next_code
        
    return successors, s_table, view_table
   
        


class FBOContext:
        
    def __init__(self, width, height):
        aspect = float(width)/float(height)

        self.fbo_texture, self.fbo_buffer, self.fbo_renderbuffer = GLuint(), GLuint(), GLuint()
        glGenTextures(1, self.fbo_texture)
        glGenFramebuffers(1, self.fbo_buffer)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_buffer) 
        
        self.texture = Texture(GL_TEXTURE_2D, self.fbo_texture)
        # bind the texture and set its parameters
        # create a texture
        glBindTexture(GL_TEXTURE_2D, self.fbo_texture)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST) 
        glTexImage2D(GL_TEXTURE_2D, 0,GL_RED,width,height,0,GL_RED,GL_FLOAT, None)
        
        # bind the frame buffer to the texture as the color render target        
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.fbo_texture, 0)
                            

        # create a depth buffer (as a render buffer) and attach it        
        glGenRenderbuffers(1, self.fbo_renderbuffer)
        glBindRenderbuffer(GL_RENDERBUFFER, self.fbo_renderbuffer)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH24_STENCIL8, width, height)                
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_STENCIL_ATTACHMENT, GL_RENDERBUFFER, self.fbo_buffer)

        # unbind the framebuffer/renderbuffer
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glBindRenderbuffer(GL_RENDERBUFFER, 0)
        
        self.width = width
        self.height = height
        
    

    def __enter__(self):        
        #enable render buffer
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo_buffer)        
        self.real_viewport = (GLint * 4)()
        glGetIntegerv(GL_VIEWPORT, self.real_viewport)
        glViewport(0, 0, self.width, self.height)
        
        
    def __exit__(self, exc_type, exc_value, traceback):
        # disable render buffer        
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(*self.real_viewport)
        
      

def mkshader(verts, frags, geoms=None):
    geoms = geoms or []
    return shader_from_file([c for c in verts], 
    [c for c in frags])

class NPTexture(object):

    def __init__(self, arr):
        self.id = GLuint()
        glGenTextures(1, self.id)
        glBindTexture(GL_TEXTURE_2D, self.id)
        glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_MODULATE)
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_WRAP_S,GL_REPEAT)
        glTexParameterf( GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT )
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST) 
        glTexImage2D(GL_TEXTURE_2D, 0,GL_RED,arr.shape[1],arr.shape[0],0,GL_RED,GL_FLOAT, arr.ctypes.data)
        self.target = GL_TEXTURE_2D

def mkeven_integer(arr):
    return np.pad(arr, ((arr.shape[0]%2,0), (arr.shape[1]%2,0)), 'constant').astype(np.int32)

def pack_callahan(arr):
    # force even size
    return arr[::2,::2] + (arr[1::2, ::2] << 1) + (arr[::2, 1::2]<<2)+ (arr[1::2, 1::2]<<3)

def unpack_callahan(cal_arr):
    unpacked = np.zeros((cal_arr.shape[0]*2, cal_arr.shape[1]*2), dtype=np.int32)
    unpacked[::2, ::2] = (cal_arr & 1)
    unpacked[1::2, ::2] = ((cal_arr >> 1) & 1)
    unpacked[::2, 1::2] = ((cal_arr >> 2) & 1)
    unpacked[1::2, 1::2] = ((cal_arr >> 3) & 1)
    return unpacked

class GOL(object):
    def __init__(self):
        window_size = (800, 800)
        self.skeleton = skeleton.GLSkeleton(draw_fn = self.redraw, resize_fn = self.resize, 
                                              tick_fn=self.tick, mouse_fn=self.mouse, key_fn=self.key, 
                                              exit_fn=self.exit, window_size=window_size)
        lif_size = 8192
        self.fbo_front = FBOContext(lif_size, lif_size)
        self.fbo_back = FBOContext(lif_size, lif_size)
        self.fbo_display = FBOContext(lif_size*2, lif_size*2)

        # enable filtering for the display texture
        glBindTexture(self.fbo_display.texture.target, self.fbo_display.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)      
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, 5.0)  

        successors, s_table, view_table = create_callahan_table()        

        self.callahan_texture = NPTexture(s_table.reshape(256,256)/15.0)        

        
        quad_indices, quad_verts, tex = make_unit_quad_tile(1)
        screen_shader =mkshader(["screen_quad.vert"], ["screen_quad.frag"]) 
        self.screen_render = shader.ShaderVBO(screen_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},
            textures={"quadTexture":self.fbo_display.texture})

        unpack_shader =mkshader(["screen_quad.vert"], ["unpack_callahan.frag"]) 
        self.unpack_render = shader.ShaderVBO(unpack_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},
            textures={"quadTexture":self.fbo_front.texture},
            vars={"in_size":lif_size})

        cal_shader =mkshader(["screen_quad.vert"], ["callahan.frag"]) 
        self.cal_render = shader.ShaderVBO(cal_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},            
            )

        # load life pattern
        lif = lifeparsers.to_numpy(lifeparsers.autoguess_life_file("breeder.lif")[0])
        
        lif = lif.astype(np.float32)

        lif_int = mkeven_integer(lif)
        packed = pack_callahan(lif_int)
        unpacked = unpack_callahan(packed)
        assert(np.allclose(lif_int, unpacked))        

        # upload, centered, into texture
        w, h = lif_size, lif_size # size of FBO texture
        x_off = (w - packed.shape[1]) / 2
        y_off = (h - packed.shape[0]) / 2
        
        packed = packed.astype(np.float32) / 15.0
        glBindTexture(self.fbo_back.texture.target, self.fbo_back.texture.id)        
        glTexSubImage2D(GL_TEXTURE_2D, 0, x_off, y_off, packed.shape[1], packed.shape[0], GL_RED, GL_FLOAT, packed.ctypes.data)
        


    def start(self):
        self.skeleton.main_loop()

    def resize(self,w,h):
        glViewport(0,0,w,h)

    def tick(self):
        pass

    def mouse(self, event, x=None, y=None, dx=None, dy=None, buttons=None, modifiers=None, **kwargs):
        pass

    def key(self, event, symbol, modifiers):
        pass

    def exit(self):
        pass
    
    def redraw(self):
        glClearColor(1,0,1,1)
        glClear(GL_COLOR_BUFFER_BIT)
        for i in range(25):
            with self.fbo_front:            
                # render the back to the front, applying the shader effect
                self.cal_render.draw(textures={"callahanTexture":self.callahan_texture, 
                                           "quadTexture":self.fbo_back.texture})
                
            # switch double buffer
            self.fbo_front, self.fbo_back = self.fbo_back, self.fbo_front

        # with self.fbo_front:
        #    self.cal_render.draw(textures={"callahanTexture":self.callahan_texture, 
        #                                   "quadTexture":self.fbo_back.texture})


        with self.fbo_display:
            self.unpack_render.draw()

        glBindTexture(self.fbo_display.texture.target, self.fbo_display.texture.id)                
        glGenerateMipmap(GL_TEXTURE_2D) # make sure we have a mipmap
            
        print(self.skeleton.actual_fps)
        
        self.screen_render.draw()
        
        # switch double buffer
        self.fbo_front, self.fbo_back = self.fbo_back, self.fbo_front
            

    
if __name__=="__main__":
    g = GOL()
    g.start()

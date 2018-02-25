import numpy as np
import pyglet
from pyglet.gl import *

import json
# sphere stuff
import pyspheregl.utils.glskeleton as skeleton
from pyspheregl.utils.gloffscreen import FBOContext
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


def mkshader(verts, frags, geoms=None):
    geoms = geoms or []
    return shader_from_file([c for c in verts], 
    [c for c in frags])

class GOL(object):
    def __init__(self):
        window_size = (800, 800)
        self.skeleton = skeleton.GLSkeleton(draw_fn = self.redraw, resize_fn = self.resize, 
                                              tick_fn=self.tick, mouse_fn=self.mouse, key_fn=self.key, 
                                              exit_fn=self.exit, window_size=window_size)
        lif_size = 4096
        self.fbo_front = FBOContext(lif_size, lif_size)
        self.fbo_back = FBOContext(lif_size, lif_size)
        quad_indices, quad_verts, tex = make_unit_quad_tile(1)
        screen_shader =mkshader(["screen_quad.vert"], ["screen_quad.frag"]) 
        self.screen_render = shader.ShaderVBO(screen_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},
            textures={"quadTexture":self.fbo_front.texture})

        gol_shader =mkshader(["screen_quad.vert"], ["gol.frag"]) 
        self.gol_render = shader.ShaderVBO(gol_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},)

        # load life pattern
        lif = lifeparsers.to_numpy(lifeparsers.autoguess_life_file("breeder.lif")[0])
        lif = np.tile(lif[:,:,None], (1,1,4)).astype(np.float32)

        # upload, centered, into texture
        w, h = lif_size, lif_size # size of FBO texture
        x_off = (w - lif.shape[1]) / 2
        y_off = (h - lif.shape[0]) / 2
        glBindTexture(self.fbo_back.texture.target, self.fbo_back.texture.id)
        glTexSubImage2D(GL_TEXTURE_2D, 0, x_off, y_off, lif.shape[1], lif.shape[0], GL_RGBA, GL_FLOAT, lif.ctypes.data)

        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glBindTexture(self.fbo_front.texture.target, self.fbo_front.texture.id)
        #glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST_MIPMAP_NEAREST)
        


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
                self.gol_render.draw(textures={"quadTexture":self.fbo_back.texture})
                glBindTexture(self.fbo_back.texture.target, self.fbo_back.texture.id)
                glGenerateMipmap(GL_TEXTURE_2D) # make sure we have a mipmap
            # switch double buffer
            self.fbo_front, self.fbo_back = self.fbo_back, self.fbo_front
            
        print(self.skeleton.actual_fps)
        # render the front to the screen, with mipmapping on
        glBindTexture(self.fbo_front.texture.target, self.fbo_front.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)      
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, 5.0)  
        self.screen_render.draw(textures={"quadTexture":self.fbo_front.texture})
        #glBindTexture(self.fbo_front.texture.target, self.fbo_front.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)        
        
        # switch double buffer
        self.fbo_front, self.fbo_back = self.fbo_back, self.fbo_front
            

    
if __name__=="__main__":
    g = GOL()
    g.start()

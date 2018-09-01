import numpy as np
import pyglet

import moderngl
# sphere stuff
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
        glTexImage2D(GL_TEXTURE_2D, 0,GL_R8,width,height,0,GL_RED,GL_FLOAT, None)
        
        # bind the frame buffer to the texture as the color render target        
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, self.fbo_texture, 0)
                            

        
        # unbind the framebuffer/renderbuffer
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        
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
        glTexImage2D(GL_TEXTURE_2D, 0,GL_R8, arr.shape[1],arr.shape[0],0,GL_RED,GL_FLOAT, arr.ctypes.data)
        self.target = GL_TEXTURE_2D

def mkeven_integer(arr):
    # force even size
    return np.pad(arr, ((arr.shape[0]%2,0), (arr.shape[1]%2,0)), 'constant').astype(np.int32)

def pack_callahan(arr):
    # pack into 4 bit 2x2 cell format
    return arr[::2,::2] + (arr[1::2, ::2] << 1) + (arr[::2, 1::2]<<2)+ (arr[1::2, 1::2]<<3)

def unpack_callahan(cal_arr):
    # unpack from 4 bit 2x2 cell format into standard array
    unpacked = np.zeros((cal_arr.shape[0]*2, cal_arr.shape[1]*2), dtype=np.int32)
    unpacked[::2, ::2] = (cal_arr & 1)
    unpacked[1::2, ::2] = ((cal_arr >> 1) & 1)
    unpacked[::2, 1::2] = ((cal_arr >> 2) & 1)
    unpacked[1::2, 1::2] = ((cal_arr >> 3) & 1)
    return unpacked
from ctypes import sizeof,byref

import glmat

class GOL(object):
    def create_atomic_counter(self):
        self.atomic_buffer = GLuint()
        self.atomics = (GLuint * 1) ()
        glGenBuffers(1, self.atomic_buffer)
        glBindBuffer(GL_ATOMIC_COUNTER_BUFFER, self.atomic_buffer)
        glBufferData(GL_ATOMIC_COUNTER_BUFFER, sizeof(self.atomics), 0, GL_DYNAMIC_DRAW)
        glBindBuffer(GL_ATOMIC_COUNTER_BUFFER,0)

    def __init__(self):
        window_size = (800, 800)
        self.skeleton = skeleton.GLSkeleton(draw_fn = self.redraw, resize_fn = self.resize, 
                                              tick_fn=self.tick, mouse_fn=self.mouse, key_fn=self.key, 
                                              exit_fn=self.exit, window_size=window_size)
        lif_size = 1024
        self.quad_res = lif_size * 0.5
        self.fbo_front = FBOContext(lif_size, lif_size)
        self.fbo_back = FBOContext(lif_size, lif_size)
        self.fbo_display = FBOContext(lif_size*2, lif_size*2)
        self.window_size = window_size
        # enable filtering for the display texture
        glBindTexture(self.fbo_display.texture.target, self.fbo_display.texture.id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)      
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAX_ANISOTROPY_EXT, 5.0)  

        successors, s_table, view_table = create_callahan_table()        

        # upload the reshaped, normalised texture
        self.callahan_texture = NPTexture(s_table.reshape(256,256)/15.0)        

        self.model = np.eye(4)
        self.proj = np.eye(4)
        
        quad_indices, quad_verts, tex = make_unit_quad_tile(1)
        screen_shader =mkshader(["screen_quad_mappable.vert"], ["screen_quad.frag"]) 
        self.screen_render = shader.ShaderVBO(screen_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},
            textures={"quadTexture":self.fbo_display.texture},
            )

        unpack_shader =mkshader(["screen_quad.vert"], ["unpack_callahan.frag"]) 
        self.unpack_render = shader.ShaderVBO(unpack_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},
            textures={"quadTexture":self.fbo_front.texture},
            vars={"in_size":lif_size})

        cal_shader =mkshader(["screen_quad.vert"], ["callahan.frag"]) 
        self.cal_render = shader.ShaderVBO(cal_shader, np_vbo.IBuf(quad_indices),
            buffers={"position":np_vbo.VBuf(quad_verts)},            
            )

        self.create_atomic_counter()

        # load life pattern
        lif = lifeparsers.to_numpy(lifeparsers.autoguess_life_file("../../qlife/lifep/cordtoss.lif")[0])
            

        # pack into 4 bit format
        lif_int = mkeven_integer(lif)
        packed = pack_callahan(lif_int)
        unpacked = unpack_callahan(packed)
        assert(np.allclose(lif_int, unpacked))        

        # upload, centered, into texture
        w, h = lif_size, lif_size # size of FBO texture
        x_off = (w - packed.shape[1]) / 2
        y_off = (h - packed.shape[0]) / 2
        # normalize for 0.0-1.0 texture format and upload
        packed = packed.astype(np.float32) / 15.0
        glBindTexture(self.fbo_back.texture.target, self.fbo_back.texture.id)        
        glTexSubImage2D(GL_TEXTURE_2D, 0, x_off, y_off, packed.shape[1], packed.shape[0], GL_RED, GL_FLOAT, packed.ctypes.data)
        

        self.proj = glmat.perspective(60, 1.0, 0.1, 1000) * glmat.scale((1.0/self.quad_res, 1.0/self.quad_res, 1))

        self.frame_ctr = 0
        self.scale = 1
        self.target_scale = 1
        

    def start(self):
        self.skeleton.main_loop()

    def resize(self,w,h):
        glViewport(0,0,w,h)

    def tick(self):
        pass

    def mouse(self, event, x=None, y=None, dx=None, dy=None, buttons=None, modifiers=None, **kwargs):
        if event=="scroll":
            scroll = kwargs["scroll_y"]
            if scroll<0:
                self.target_scale *= 0.8
            else:
                self.target_scale *= 1.2
            xs, ys = self.unproject(x,y)
            
        pass

    def key(self, event, symbol, modifiers):
        pass

    def exit(self):
        pass

    def unproject(self, x, y):
        # convert screen coords to world coords
        outx, outy, outz = GLdouble(), GLdouble(), GLdouble()
        view = (GLint * 4)(0,0,self.window_size[0], self.window_size[1])
        model = (GLdouble * 16)()
        proj = (GLdouble * 16)()        
        model[0:16] = np.array(self.model).ravel()
        proj[0:16] = np.array(self.proj).ravel()
        gluUnProject(x,y,1,model, proj, view, outx, outy, outz)
        return outx.value, outy.value
    
    def redraw(self):
        self.scale = 0.97 *self.scale + 0.03*self.target_scale
        glClearColor(0,0,0,1)
        glClear(GL_COLOR_BUFFER_BIT)
       

        population = (GLuint * 1)()

        self.frame_ctr += 1
        glDisable(GL_BLEND)
        glDisable(GL_DEPTH_TEST)
        for i in range(1):
            with self.fbo_front:                   
                glBindBufferBase(GL_ATOMIC_COUNTER_BUFFER, 0, self.atomic_buffer)
                glBufferSubData(GL_ATOMIC_COUNTER_BUFFER, 0, sizeof(population), population)
              
                # render the back to the front, applying the shader effect
                self.cal_render.draw(textures={"callahanTexture":self.callahan_texture, 
                                               "quadTexture":self.fbo_back.texture}, vars={"frame_offset":self.frame_ctr%2})
                # read back the buffer
                glGetBufferSubData(GL_ATOMIC_COUNTER_BUFFER, 0, sizeof(population), population)
                print(population[0])
            

            # switch double buffer
            self.fbo_front, self.fbo_back = self.fbo_back, self.fbo_front

        glEnable(GL_BLEND)

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        with self.fbo_display:            
                self.unpack_render.draw(vars={"frame":self.frame_ctr, "strobe":60})

        
        glBindTexture(self.fbo_display.texture.target, self.fbo_display.texture.id)                
        glGenerateMipmap(GL_TEXTURE_2D) # make sure we have a mipmap
            
        print(self.skeleton.actual_fps)
        #self.model =  glmat.scale((self.quad_res, self.quad_res, 1)) *  glmat.lookat((0,0,1), (0,0,0), (0,1.0,0))  
        
        #self.model = (tn.scale_matrix(self.quad_res*self.scale)).T
        self.model =    glmat.scale((self.scale, self.scale, 1)) * glmat.rotz(0) * glmat.translate((-0.0*self.frame_ctr,0,0))  *  glmat.scale((self.quad_res, self.quad_res, 1)) *  glmat.lookat((0,0,1), (0,0,0), (0,1.0,0))  
        
        self.screen_render.draw(vars={"proj":np.array(self.proj.astype(np.float32)).ravel(), "model":np.array(self.model.astype(np.float32)).ravel()})
        
            
def prod(*args):
    return reduce(np.dot, args)
    
if __name__=="__main__":
    g = GOL()
    g.start()

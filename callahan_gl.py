"""
    Renders a traingle that has all RGB combinations
"""

import moderngl
import numpy as np
import modern_gl_skeleton as skel
import time
import lifeparsers
from callahan import pack_life, load_life, create_callahan_table
import os
import glmat




def shader_from_file(ctx, vtx, frag):
    with open(os.path.join("shaders", vtx)) as v:
        vertex_shader = v.read()
    with open(os.path.join("shaders", frag)) as f:
        frag_shader = f.read()
    return ctx.program(vertex_shader=vertex_shader, fragment_shader=frag_shader)


def packed_to_texture(ctx, packed, lif_size, texture):
    # upload, centered, into texture
    w, h = lif_size, lif_size  # size of FBO texture
    x_off = (w - packed.shape[1]) // 2
    y_off = (h - packed.shape[0]) // 2
    # normalize for the format and upload
    packed = (packed * 17).astype(np.uint8)
    texture.write(packed, viewport=(x_off, y_off, packed.shape[1], packed.shape[0]))
    return texture


def square_single_channel_texture(ctx, size, data=None):
    texture = ctx.texture((size, size), components=1, data=data)
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    return texture


# Framebuffer, backed to a single-channel texture, color buffer only
class FBO:
    def __init__(self, ctx, size):
        self.texture = square_single_channel_texture(ctx, size)
        self.fbo = ctx.framebuffer(color_attachments=self.texture)
        self.scope = ctx.scope(self.fbo)
        self.ctx = ctx
        self.size = size
        self.offset = 0

    # bind the texture (i.e. for reading the image back)
    def use(self):
        self.texture.use()

    # proxy the scope object, and configure
    # the viewport so that rendering is pixel-perfect
    def __enter__(self):
        self.scope.__enter__()
        self.ctx.viewport = (
            self.offset,
            self.offset,
            self.size + self.offset,
            self.size + self.offset,
        )

    def __exit__(self, type, value, tb):
        self.scope.__exit__(type, value, tb)

def set_matrix(prog, uniform, x):
    prog[uniform].write(x.T.astype('f4').tobytes())

class CallahanGL:
    def setup_gl(self):
        self.skeleton = skel.GLSkeleton(draw_fn=self.render, window_size=(800, 800))
        self.ctx = self.skeleton.get_context()
        # framebuffers
        self.front = FBO(self.ctx, self.lif_size)
        self.back = FBO(self.ctx, self.lif_size)
        self.display = FBO(
            self.ctx, self.lif_size * 2
        )  # twice resolution because data is unpacked
        self.pop_buffer = self.ctx.buffer(data=np.zeros(1, dtype="uint32").tobytes())

        self.colour_fbo = self.ctx.simple_framebuffer(
            (self.skeleton.window.width, self.skeleton.window.height), components=4
        )
        self.colour_scope = self.ctx.scope(self.colour_fbo)

    def load_shaders(self):
        # shader to convert packed 4 bit format to binary pixels
        self.unpack_prog = shader_from_file(
            self.ctx, "unpack_callahan.vert", "unpack_callahan.frag"
        )
        # shader to perform Life rule using Callahan's lookup table
        self.gol_prog = shader_from_file(self.ctx, "callahan.vert", "callahan.frag")
        # Simple textured quad shader
        self.tex_prog = shader_from_file(self.ctx, "tex_quad.vert", "tex_quad.frag")
        self.black_prog = shader_from_file(self.ctx, "black.vert", "black.frag")
        self.black_prog["alpha"].value = 0.25
        self.unpack_prog["in_size"].value = self.lif_size
        self.gol_prog["quadTexture"].value = 0
        self.gol_prog["callahanTexture"].value = 1

    def setup_geometry(self):
        quad = np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]]).astype("f4")
        quad_vbo = self.ctx.buffer(quad.tobytes())

        # create a vertex array that just renders a single triangle strip
        # quad, with the given program
        def make_quad_vao(prog):
            return self.ctx.simple_vertex_array(prog, quad_vbo, "pos")

        self.unpack_vao = make_quad_vao(self.unpack_prog)
        self.gol_vao = make_quad_vao(self.gol_prog)
        self.tex_vao = make_quad_vao(self.tex_prog)
        self.black_vao = make_quad_vao(self.black_prog)

    def setup_matrices(self):
        self.model_view = glmat.lookat((0,0,0.7), (0,0,0), (0,1,0)).astype(np.float32)        
        self.projection = glmat.perspective(40, self.skeleton.window.width/self.skeleton.window.height, 0.1, 100).astype(np.float32)
        

    def __init__(self):
        self.lif_size = 2048

        self.setup_gl()
        self.load_shaders()
        self.setup_geometry()
        self.setup_matrices()

        self.track = [-0.5, 0]

        s_table = create_callahan_table()
        # upload the reshaped, normalised texture
        self.callahan_texture = square_single_channel_texture(
            self.ctx, 256, data=s_table * 17
        )

        # load life pattern
        fname = "pat/breeder.lif"
        packed = pack_life(load_life(fname))
        packed_to_texture(self.ctx, packed, self.lif_size, self.front.texture)
        self.population = 0

        # bind the lookup table to texture slot 1
        self.callahan_texture.use(1)
        self.skeleton.run()

    def render(self):
        # pixel offset (alternates each frame)
        frame_offset = self.skeleton.frames % 2

        self.ctx.clear(0.0, 0.0, 0.0)

        # # apply forward algorithm
        with self.back:
            self.front.use()
            # adjust for pixel shift on each frame
            self.gol_prog["frameOffset"].value = frame_offset
            self.gol_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # render to the display buffer
        self.display.offset = -frame_offset
        with self.display:
            self.back.use()
            self.unpack_prog["strobe"].value=30
            self.unpack_prog["frame"].value=self.skeleton.frames
            self.unpack_prog["strobe_exp"].value=1
            
            self.ctx.enable(moderngl.BLEND)


            #self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            #self.black_vao.render(mode=moderngl.TRIANGLE_STRIP)

            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            # read population back from the buffer
            self.pop_buffer.bind_to_storage_buffer(binding=0)
            self.unpack_vao.render(mode=moderngl.TRIANGLE_STRIP)
            self.population = np.frombuffer(self.pop_buffer.read(), dtype=np.uint32)[0]

        # ensure mip-mapping is rebuilt
        self.display.texture.build_mipmaps()

        # now render to the screen
        self.ctx.viewport = (
            0,
            0,
            self.skeleton.window.width,
            self.skeleton.window.height,
        )

        # bugfix? without this, rendering is stuck
        # in single channel mode. This restores the colour rendering
        with self.colour_scope:
            pass

        self.display.use()

        # translate to smoothly track the location
        self.model_view = glmat.translate([2*self.track[0]/self.lif_size, 2*self.track[1]/self.lif_size, 0]).astype(np.float32) @ self.model_view
        set_matrix(self.tex_prog, "modelview", self.model_view)
        set_matrix(self.tex_prog, "projection", self.projection)
        
        
        self.tex_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # flip buffers
        self.front, self.back = self.back, self.front


CallahanGL()

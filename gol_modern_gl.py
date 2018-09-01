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


def shader_from_file(ctx, vtx, frag):
    with open(os.path.join("shaders", vtx)) as v:
        vertex_shader = v.read()
    with open(os.path.join("shaders", frag)) as f:
        frag_shader = f.read()
    return ctx.program(vertex_shader=vertex_shader, fragment_shader=frag_shader)


def fit_life(ctx, packed, lif_size, texture):
    # upload, centered, into texture
    w, h = lif_size, lif_size  # size of FBO texture
    x_off = (w - packed.shape[1]) // 2
    y_off = (h - packed.shape[0]) // 2
    # normalize for the format and upload
    packed = (packed * 17).astype(np.uint8)
    texture.write(packed, viewport=(x_off, y_off, packed.shape[1], packed.shape[0]))
    return texture


def load_life_texture(ctx, fname, size, texture):
    lif = load_life(fname)
    return fit_life(ctx, pack_life(lif), size, texture)


def square_red_texture(ctx, size, dtype="f1"):
    texture = ctx.texture((size, size), components=1, dtype=dtype)
    texture.filter = (moderngl.NEAREST, moderngl.NEAREST)
    return texture


class FBO:
    def __init__(self, ctx, size):
        self.texture = square_red_texture(ctx, size)
        self.fbo = ctx.framebuffer(color_attachments=self.texture)
        self.scope = ctx.scope(self.fbo)
        self.ctx = ctx
        self.size = size
        self.offset = 0

    def use(self):
        self.texture.use()

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


class SimpleColorTriangle:
    def __init__(self):
        self.skeleton = skel.GLSkeleton(draw_fn=self.render, window_size=(800, 800))
        self.ctx = self.skeleton.get_context()
        self.frame = 0

        # load life pattern
        self.lif_size = 1024

        # framebuffers
        self.front = FBO(self.ctx, self.lif_size)
        self.back = FBO(self.ctx, self.lif_size)
        self.display = FBO(self.ctx, self.lif_size * 2)

        _, s_table, _ = create_callahan_table()

        self.pop_buffer = self.ctx.buffer(data=np.zeros(1, dtype="uint32").tobytes())

        # upload the reshaped, normalised texture
        self.callahan_texture = square_red_texture(self.ctx, 256, dtype="f4")
        self.callahan_texture.write(s_table.reshape(256, 256) / 15.0)

        load_life_texture(self.ctx, "breeder.lif", self.lif_size, self.front.texture)

        self.unpack_prog = shader_from_file(
            self.ctx, "unpack_callahan.vert", "unpack_callahan.frag"
        )
        self.gol_prog = shader_from_file(self.ctx, "callahan.vert", "callahan.frag")
        self.tex_prog = shader_from_file(self.ctx, "tex_quad.vert", "tex_quad.frag")
        quad = np.array([[-1, -1], [-1, 1], [1, -1], [1, 1]]).astype("f4")
        vbo = self.ctx.buffer(quad.tobytes())

        # We control the 'in_vert' and `in_color' variables
        self.unpack_vao = self.ctx.simple_vertex_array(self.unpack_prog, vbo, "pos")
        self.gol_vao = self.ctx.simple_vertex_array(self.gol_prog, vbo, "pos")
        self.tex_vao = self.ctx.simple_vertex_array(self.tex_prog, vbo, "pos")

        self.unpack_prog["in_size"].value = self.lif_size
        self.gol_prog["quadTexture"].value = 0
        self.gol_prog["callahanTexture"].value = 1
        self.skeleton.run()

    def render(self):
        frame_offset = self.frame % 2

        self.ctx.clear(0.0, 0.0, 0.0)

        # apply forward algorithm
        with self.back:
            self.front.use()
            self.callahan_texture.use(1)
            # adjust for pixel shift on each frame
            self.gol_prog["frameOffset"].value = frame_offset
            self.gol_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # render to the display buffer
        self.display.offset = -frame_offset
        with self.display:
            self.back.use()
            self.unpack_vao.render(mode=moderngl.TRIANGLE_STRIP)
        self.display.texture.build_mipmaps()  # ensure mip-mapping is rebuilt

        # now render to the screen
        self.ctx.viewport = (
            0,
            0,
            self.skeleton.window.width,
            self.skeleton.window.height,
        )
        self.display.use()
        self.tex_vao.render(mode=moderngl.TRIANGLE_STRIP)

        # flip buffers
        self.frame += 1
        self.front, self.back = self.back, self.front


SimpleColorTriangle()

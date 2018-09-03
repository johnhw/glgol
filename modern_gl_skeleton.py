import sys, time, os
import pyglet
import moderngl
import timeit

timer = timeit.default_timer

# Skeleton class
class GLSkeleton:
    def init_pyglet(self, size):
        width, height = size
        config = None
        # windows only
        if os.name == "nt":
            config = pyglet.gl.Config(sample_buffers=1, samples=8)
        screens = pyglet.window.get_platform().get_default_display().get_screens()
        self.window = None
        # try to find a matching screen
        for screen in screens:
            if screen.width == width and screen.height == height:
                self.window = pyglet.window.Window(
                    config=config, fullscreen=True, screen=screen
                )
        if not self.window:
            self.window = pyglet.window.Window(
                config=config, fullscreen=False, width=width, height=height
            )

        # attach the handlers for events
        self.window.set_handler("on_draw", self.draw_fn)
        if self.resize_fn is not None:
            self.window.set_handler("on_resize", self.resize_fn)

        events = {"on_key_press":(self.on_key, "press"),
                  "on_key_release":(self.key_fn, "release"),
                  "on_mouse_motion":(self.mouse_fn, "move"),
                  "on_mouse_drag":(self.mouse_fn, "drag"),
                  "on_mouse_scroll":(self.mouse_fn, "scroll"),
                  "on_mouse_press":(self.key_fn, "press"),
                  "on_mouse_release":(self.key_fn, "release"),                                    
                  }

        for event, handler in events.items():
            fn, evt = handler
            if fn is not None:
                def handler(*args, **kwargs):                    
                    fn(evt, *args, **kwargs)
                self.window.set_handler(event, handler)
        self.w, self.h = self.window.width, self.window.height
        
        self.context = moderngl.create_context()

        print(
            "OpenGL version %s %s"
            % (pyglet.gl.gl_info.get_version(), pyglet.gl.gl_info.get_vendor())
        )
        print("       renderer %s " % (pyglet.gl.gl_info.get_renderer()))

        print("Resolution: %d x %d" % (self.window.width, self.window.height))

    
    def get_context(self):
        return self.context

    def on_resize(self, w, h):
        if self.resize_fn:
            self.resize_fn(w, h)
        return pyglet.event.EVENT_HANDLED

    def on_draw(self):

        if self.draw_fn:
            self.draw_fn()

    def on_key(self, evt, symbol, modifiers):
        if symbol == pyglet.window.key.ESCAPE:
            self.running = False

        
    # init routine, sets up the engine, then enters the main loop
    def __init__(
        self,
        draw_fn=None,
        tick_fn=None,
        event_fn=None,
        key_fn=None,
        resize_fn=None,
        mouse_fn=None,
        exit_fn=None,
        window_size=(800, 600),
        debug=True,
        fullscreen=False,
    ):
        if not debug:
            # faster, but unsafe operation
            pyglet.options["debug_gl"] = False
        
        self.fps = 60
        self.frames = 0
        self.debug = debug
        self.resize_fn = resize_fn
        self.draw_fn = draw_fn
        self.tick_fn = tick_fn
        self.key_fn = key_fn
        self.exit_fn = exit_fn
        self.mouse_fn = mouse_fn
        self.running = True
        self.elapsed_time = 0
        self.actual_fps = self.fps  # until we update when running
        self.init_pyglet(window_size)

    # handles shutdown
    def exit(self):
        self.running = False
        if self.exit_fn is not None:
            self.exit_fn()

    # frame loop. Called on every frame. all calculation shpuld be carried out here
    def tick(self, delta_t):
        time.sleep(0.002)  # yield!        
        if self.tick_fn:
            self.tick_fn()

    def clock(self):
        return timer()

    # main loop. Just runs tick until the program exits
    def run(self):
        self.start_time = self.clock()
        while self.running:
            event = self.window.dispatch_events()
            pyglet.clock.tick()
            self.tick(1 / self.fps)
            self.frames += 1
            self.elapsed_time = self.start_time - self.clock()
            self.on_draw()
            self.window.flip()
            self.actual_fps = pyglet.clock.get_fps()

    def main_loop(self):
        pyglet.clock.set_fps_limit(self.fps)
        self.run()


class Scheduler:
    def __init__(self):
        # events:
        # start, duration, fn, args
        self.events = []
        self.adds = []

    def update(self, time):
        for duration, repeat, fn, args in self.adds:
            self.events.append((time, duration, repeat, fn, args))
        self.adds = []
        removes = []

        for event in self.events:
            start, duration, repeat, fn, args = event
            expiry = start + duration

            # fire expired functions
            if time >= expiry:
                fn(*args)
                if repeat:
                    # readd repeating events
                    self.add(duration, fn, args, repeat=True)

                removes.append(event)

        # clear expired events
        for event in removes:
            self.events.remove(event)

    def add(self, duration, fn, args, repeat=False):
        self.adds.append((duration, repeat, fn, args))


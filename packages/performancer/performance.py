import time


class Performancer:
    def __init__(self, logger):
        self.start_time = {}
        self.end_time = {}
        self.log = logger

    def start(self, id="default"):
        self.start_time[id] = time.time()

    def end(self, id="default", prefix="counted", suffix=""):
        if id not in self.start_time:
            self.log(f'id {id} not in start_time found')
            return False
        self.end_time[id] = time.time()
        duration = self.end_time[id] - self.start_time[id]
        self.log(prefix + " " + str(round(duration)) + " seconds " + suffix)
        return duration

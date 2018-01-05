from abc import abstractmethod
from threading import Thread
from time import sleep, time


class Runner(object):
    """
    Runs a function in a separate thread.
    """

    def __init__(self, name="Runner", target=None):
        self.name = name
        self.__thread = None
        if target:
            self.__target = target
        else:
            self.__target = self._work

    def get_name(self) -> str:
        return self.name

    def run(self, *args, **kwargs):
        self.__thread = Thread(target=self.__target, args=args, kwargs=kwargs)
        self.__thread.daemon = True
        self.__thread.start()

    def is_running(self) -> bool:
        return self.__thread.is_alive()

    def join(self):
        if self.__thread is not None:
            self.__thread.join()

    @abstractmethod
    def _work(self):
        pass

    @staticmethod
    def _run_target(target):
        if type(target) is Runner:
            target.run()
            target.join()
        elif type(target) in [classmethod, staticmethod]:
            target()

    @staticmethod
    def sleep(delay: float, tick: float):
        sleep(delay - (time() - tick))


class ResettingQueueRunner(Runner):
    """
    A runner with an internal queue that resets every time the runner is executed.
    """

    def __init__(self, target: classmethod):
        super().__init__(self.__class__.__name__)
        self._target = target
        self._queue = []

    def __reset_queue(self):
        self._queue = []

    def add_to_queue(self, item):
        self._queue.append(item)

    def _work(self):
        self._target()
        self.__reset_queue()


class RepeatingRunner(Runner):
    """
    A Runner that automatically restarts itself after it's done.
    """

    def __init__(self, target: classmethod, auto_start=True):
        super().__init__(self.__class__.__name__)
        self._target = target
        self._running = False

        if auto_start:
            self.start()

    def start(self):
        if not self._running:
            self._running = True
            self.run()

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def join(self):
        while self.is_running():
            sleep(0.01)

    def _work(self):
        while self._running:
            self._target()


class PeriodicRunner(Runner):
    """
    A Runner that automatically runs at a fixed period.
    """

    def __init__(self, target: classmethod, auto_start=True, period=1.0):
        super().__init__(self.__class__.__name__)
        self._period = period
        self._target = target

        self._running = False

        if auto_start:
            self.start()

    def set_period(self, delay: float):
        self._period = delay

    def get_period(self):
        return self._period

    def start(self):
        if not self._running:
            self._running = True
            self.run()

    def stop(self):
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def join(self):
        while self.is_running():
            sleep(0.01)

    def _work(self):
        while self._running:
            tick = time()
            self._target()
            self.sleep(self._period, tick)


class RunnerQueue(Runner):
    """
    Runs a series of functions or runners in the specified order.
    """

    def __init__(self, *runners):
        super().__init__(self.__class__.__name__)
        self._runners = list(runners)

    def add_runner(self, runner: Runner):
        self._runners.append(runner)

    def get_list(self) -> list:
        return list(self._runners)

    def _work(self):
        for runner in self._runners:
            if type(runner) is Runner:
                runner.run()
                runner.join()
            elif type(runner) in [classmethod, staticmethod]:
                runner()


class ConcurrentRunner(RunnerQueue):
    """
    Runs a series of functions at the same time and dies when they're all done.
    Sub-thread liveliness is checked at 100Hz.
    """

    def __init__(self, *runners):
        RunnerQueue.__init__(self, *runners)

    def is_running(self):
        for runner in self._runners:
            if runner.is_running():
                return True
        return False

    def _work(self):
        tick = time()
        for runner in self._runners:
            runner.start()
        while self.is_running():
            self.sleep(0.01, tick)

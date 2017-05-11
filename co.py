# -*- coding:utf-8 -*-
import log
import types
from functools import wraps
from itertools import count
import time
import sys
import copy

logger = log.getLogger('coroutine')

future_map = {}
future_id_counter = count(0)


class Future(object):

    def __init__(self):
        self.id = future_id_counter.next()
        self.timeout_time = 0
        self.on_result_cb = None
        self.on_exception_cb = None
        self.data = {}

    def set_on_result_cb(self, on_result_cb):
        self.on_result_cb = on_result_cb
        if 'result' in self.data:
            self.on_result_cb(self.data.pop('result'))
            future_map.get(int(self.timeout_time), {}).pop(self.id, None)

    def set_on_exception_cb(self, on_exception_cb):
        self.on_exception_cb = on_exception_cb
        if 'exception' in self.data:
            self.on_exception_cb(self.data.pop('exception'))
            future_map.get(int(self.timeout_time), {}).pop(self.id, None)

    def set_result(self, result):
        if self.on_result_cb:
            self.on_result_cb(result)
            future_map.get(int(self.timeout_time), {}).pop(self.id, None)
        else:
            self.data['result'] = result

    def set_exception(self, e):
        if self.on_exception_cb:
            self.on_exception_cb(e)
            future_map.get(int(self.timeout_time), {}).pop(self.id, None)
        else:
            self.data['exception'] = e

    def timeout(self, seconds):
        self.timeout_time = time.time() + seconds
        future_map.setdefault(int(self.timeout_time), {})[self.id] = self
        return self

    def destroy(self):
        future_map.get(int(self.timeout_time), {}).pop(self.id, None)
        self.on_result_cb = None
        self.on_exception_cb = None
        self.data = {}


def any_future(futures, destroy_others=True):
    future = Future()

    def callback(_future, _all_futures, result):
        if destroy_others:
            for f in _all_futures:
                f.destroy()
        future.set_result([_future, result])

    for f in futures:
        f.set_on_result_cb(lambda result, _future=f, _all_futures=copy.copy(futures):
                           callback(_future, _all_futures, result))

    return future


class Return(Exception):

    def __init__(self, result):
        self.result = result


class TimeoutError(Exception):
    pass


def _co_run(co, future, args, exception=None):
    # logger.info('%r future[%d] %r', co, future.id, args)
    try:
        if exception:
            inner_future = co.throw(*exception)
        else:
            inner_future = co.send(args)
    except StopIteration:
        future.set_result(None)
    except Return as e:
        future.set_result(e.result)
    except:
        future.set_exception(sys.exc_info())
    else:
        if type(inner_future) is not Future:
            future.set_exception(
                [Exception('async function must yield a Future object')])
            return
        inner_future.set_on_exception_cb(
            lambda _exception: _co_run(co, future, None, _exception))
        inner_future.set_on_result_cb(
            lambda result: _co_run(co, future, result))


def async(f):

    @wraps(f)
    def wrap_f(*args, **kwargs):
        co = f(*args, **kwargs)
        if type(co) is not types.GeneratorType:
            logger.warning('%r is not a generator function', f)
            return co

        future = Future()
        _co_run(co, future, None)
        return future

    return wrap_f


def coroutine_loop():
    now = time.time()
    for t in sorted(future_map.keys()):
        if t > now:
            break
        for fid in future_map[t].keys():
            future = future_map[t][fid]
            if future.timeout_time <= now:
                future.set_exception([TimeoutError])
                future_map[t].pop(fid, None)

            if not future_map[t]:
                future_map.pop(t, None)

# -*- coding:utf-8 -*-
from multiprocessing import Process, Pipe
import log
import random
import time
from co import async, Future, Return, TimeoutError
from collections import defaultdict
from functools import wraps
import traceback

server_logger = log.getLogger('server')
client_logger = log.getLogger('client')

server_timers = defaultdict(list)
server_now = 0


def rpc_method(f):
    @wraps(f)
    def wrap_f(*args, **kwargs):
        ret = f(*args, **kwargs)
        if type(ret) is Future:
            def handler(exception):
                server_logger.error('%s', ''.join(
                    traceback.format_exception(*exception)))
            ret.set_on_exception_cb(handler)
    return wrap_f


def add_server_timer(delay, callback):
    server_timers[server_now + delay].append(callback)


def server_timer_loop():
    global server_now
    server_now += 1
    to_remove = []
    for t, callbacks in server_timers.iteritems():
        if t <= server_now:
            to_remove.append(t)
            for callback in callbacks:
                callback()

    for t in to_remove:
        server_timers.pop(t, None)


def append_x(s):
    server_logger.info('append_x %r', s)
    f = Future().timeout(5)
    add_server_timer(2, lambda: f.set_result(s + 'x'))
    return f


def append_y(s):
    server_logger.info('append_y %r', s)
    f = Future().timeout(5)
    add_server_timer(1, lambda: f.set_result(s + 'y'))
    return f


@async
def _echo(s):
    server_logger.info('[0] _echo %r', s)
    try:
        f1 = append_x(s)
        f2 = append_y(s)
        s = yield f1
        s1 = yield f2
    except TimeoutError:
        server_logger.error('timeout for append_x')

    server_logger.info('[1] _echo %r', s + s1)
    raise Return('server: ' + s + s1)


@rpc_method
@async
def echo(conn, s):
    server_logger.info('[0] echo %r', s)
    s = yield _echo(s)
    server_logger.info('[1] echo %r', s)
    conn.send(s)
    server_logger.info('[2] echo %r', s)

server_rpc_map = {
    'echo': echo
}


def server(conn):
    from co import coroutine_loop
    while True:
        if conn.poll():
            rpc, args = conn.recv()
            server_logger.info('%s(%r)', rpc, args)

            try:
                server_rpc_map.get(rpc, lambda _args: None)(conn, *args)
            except Exception as e:
                server_logger.info('exception: %r', e)
                import traceback
                traceback.print_stack()

        time.sleep(1.0)
        server_timer_loop()
        coroutine_loop()


def client(conn):
    from co import coroutine_loop
    while True:
        rpc = 'echo'
        args = (str(random.randint(0, 100)), )
        conn.send([rpc, args])

        time.sleep(1.0)
        coroutine_loop()

        if conn.poll():
            ret = conn.recv()
            client_logger.info('%r', ret)


def main():
    conn1, conn2 = Pipe()
    c = Process(target=client, args=(conn1, ))
    s = Process(target=server, args=(conn2, ))
    c.start()
    s.start()
    c.join()
    s.join()

if __name__ == '__main__':
    main()

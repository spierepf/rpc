import pytest
from contextlib import contextmanager
from threading import Thread

from rpc import RPCServer, RPCClient


def run_server_until_done(server):
    def do():
        while server.run():
            pass

    return do


@contextmanager
def rpc_fixture(test_object):
    server = RPCServer(test_object)
    server.connect()
    Thread(target=run_server_until_done(server), daemon=True).start()
    client = RPCClient(('127.0.0.1', server._port))
    client.connect()
    try:
        yield client
    finally:
        client.disconnect()
        server.disconnect()


def test_server_finds_method_on_exposed_instance():
    class TestObject:
        def method(self):
            pass

    server = RPCServer(TestObject())
    assert server._methods['method'] is not None


def test_call_to_existing_method():
    class TestObject:
        def method(self):
            pass

    with rpc_fixture(TestObject()) as client:
        client.method()


def test_call_to_missing_method():
    with pytest.raises(Exception):
        with rpc_fixture(object()) as client:
            client.method()


def test_call_to_exception_raising_method():
    class TestObject:
        def method(self):
            raise Exception()

    with pytest.raises(Exception):
        with rpc_fixture(TestObject()) as client:
            client.method()


@pytest.mark.parametrize("value", [
    (7),
    ('11'),
    (['string'])
])
def test_call_to_method_returning_value(value):
    class TestObject:
        def method(self):
            return value

    with rpc_fixture(TestObject()) as client:
        assert value == client.method()


@pytest.mark.parametrize("value", [
    (7),
    ('11'),
    (['string'])
])
def test_call_to_method_taking_positional_arg(value):
    class TestObject:
        def __init__(self):
            self.value = None

        def method(self, arg):
            self.value = arg

    test_object = TestObject()
    with rpc_fixture(test_object) as client:
        client.method(value)

    assert value == test_object.value


@pytest.mark.parametrize("value", [
    (7),
    ('11'),
    (['string'])
])
def test_call_to_method_taking_keyword_arg(value):
    class TestObject:
        def __init__(self):
            self.value = None

        def method(self, **kwargs):
            self.value = kwargs['arg']

    test_object = TestObject()
    with rpc_fixture(test_object) as client:
        client.method(arg=value)

    assert value == test_object.value

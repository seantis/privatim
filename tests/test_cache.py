from privatim.cache import clear_instance_cache
from privatim.cache import instance_cache


class DummyObject:

    def __init__(self, result='called'):
        self.result = result
        self.calls = 0

    @instance_cache()
    def method(self):
        self.calls += 1
        return self.result

    @instance_cache()
    def method_args(self, arg):
        self.calls += 1
        return self.result

    @instance_cache()
    def method_kwargs(self, **kwargs):
        self.calls += 1
        return self.result


def test_instance_cache():
    obj1 = DummyObject()
    obj2 = DummyObject(result='called too')
    assert obj1.method() == 'called'
    assert obj1.calls == 1

    assert obj2.method() == 'called too'
    assert obj2.calls == 1
    # Call a second time
    assert obj2.method() == 'called too'
    assert obj2.calls == 1


def test_instance_cache_args():
    obj = DummyObject()
    assert obj.method_args('test1') == 'called'
    assert obj.calls == 1
    assert obj.method_args('test2') == 'called'
    assert obj.calls == 2
    assert obj.method_args('test2') == 'called'
    assert obj.calls == 2


def test_instance_cache_kwargs():
    obj = DummyObject()
    assert obj.method_kwargs(arg='test1') == 'called'
    assert obj.calls == 1
    assert obj.method_kwargs(arg='test2') == 'called'
    assert obj.calls == 2
    assert obj.method_kwargs(arg='test2') == 'called'
    assert obj.calls == 2


def test_cache():
    obj1 = DummyObject()
    assert obj1.method.cache(obj1) == {}

    obj1.method()
    cache_key = ('method', (obj1,), frozenset([]))
    cache = obj1.method.cache(obj1)
    assert cache == {cache_key: 'called'}


def test_clear_instance_cache():
    obj = DummyObject()
    assert obj.method() == 'called'
    assert obj.calls == 1
    assert len(obj.method.cache(obj).keys()) == 1
    clear_instance_cache(obj)
    assert obj.method.cache(obj) == {}
    assert obj.method() == 'called'
    assert obj.calls == 2

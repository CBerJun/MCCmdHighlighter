# Version controller

__all__ = [
    "VersionedMixin", "VersionedMethod",
    "versioned_method", "MIN_VERSION"
]

MIN_VERSION = (1, 19, 0)

class VersionedMixin:
    # A class that contains `VersionedMethod`
    def set_version(self, version: tuple):
        # The version used in this instance
        assert MIN_VERSION <= version
        self.version = version

    @classmethod
    def get_all_versions(cls) -> set:
        # Get all "meaningful" versions
        res = set()
        for attr in dir(cls):
            value = getattr(cls, attr)
            # NOTE this relies on that `Class.versioned_method` returns the
            # data descriptor itself!!!
            if isinstance(value, VersionedMethod):
                res.update(value.versions)
        return res

class VersionedMethod:
    # Data descriptor; a method that has different versions
    def __init__(self):
        self.version2func = {}
        self.versions = []

    def register(self, func, version):
        """Register the function as a different version of method."""
        assert version not in self.versions
        self.version2func[version] = func
        # Insert version into list of versions and keep it descending
        for i, v in enumerate(self.versions):
            if v < version:
                self.versions.insert(i, version)
                break
        else:
            self.versions.append(version)

    def variation(self, *args, **kwargs):
        """
        Decorator version of method `register`.
        Return a decorator that register the decorated function as a different
        version of the method.
        """
        def _decorator(func):
            self.register(func, *args, **kwargs)
            # Here we return the original function, so that this decorator
            # won't actually affect the decorated method, but just register it
            # as a variation of versioned method
            return func
        return _decorator

    def __get__(self, instance, owner):
        assert issubclass(owner, VersionedMixin)
        if instance is None:
            # If calling just using the class, return the descriptor itself
            return self
        for v in self.versions:
            if instance.version >= v:
                def _target(*args, **kwargs):
                    return self.version2func[v](instance, *args, **kwargs)
                return _target
        else:
            raise NotImplementedError(
                "No implementation found for version %r" % (instance.version,)
            )

def versioned_method(*args, **kwargs):
    """
    Decorator version of `VersionedMethod`
    Typically usage:
    >>> class Test(VersionedMixin):
    ...     def __init__(self, version):
    ...         self.set_version(version)
    ... 
    ...     @versioned_method(version=(1, 19, 70))
    ...     def foo(self):
    ...         print("foo 1.19.70")
    ... 
    ...     @foo.variation(version=(1, 19, 50))
    ...     def foo_1_19_50(self):
    ...         print("foo 1.19.50")
    ... 
    >>> t = Test((1, 19, 60))
    >>> t.foo()
    foo 1.19.50
    >>> t2 = Test((1, 19, 70))
    >>> t2.foo()
    foo 1.19.70
    >>> t2.foo_1_19_50()
    foo 1.19.50
    """
    res = VersionedMethod()
    def _decorator(func):
        res.register(func, *args, **kwargs)
        return res
    return _decorator


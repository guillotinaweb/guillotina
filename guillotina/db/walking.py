from guillotina.configure import adapter
from guillotina.interfaces import IFolder
from guillotina.interfaces import IIteratorResources
from guillotina.interfaces import IResource


@adapter(for_=(IFolder), provides=IIteratorResources)
class WalkingIterator(object):
    def __init__(self, context):
        self.context = context
        self.total = 0
        self.count = 0

    async def deep_walk(self, actual):
        self.total += await actual.async_len()
        async for obj in actual.async_values():
            if IFolder.providedBy(obj):
                async for children in self.deep_walk(obj):
                    yield children
            if IResource.providedBy(obj):
                yield obj

    async def __call__(self, ids=False, size=None, include=None, myself=False):
        object_list = []
        if myself:
            yield self.context
        async for obj in self.deep_walk(self.context):
            if include is not None:
                for interface_to_include in include:
                    if not interface_to_include.providedBy(obj):
                        continue
            if ids:
                if size is not None:
                    object_list.append(obj.__uuid__)
                    if len(object_list) == size:
                        yield object_list
                        object_list = []
                else:
                    yield obj.__uuid__
            else:
                if size is not None:
                    object_list.append(obj)
                    if len(object_list) == size:
                        yield object_list
                        object_list = []
                else:
                    yield obj
        if size is not None and len(object_list) > 0:
            yield object_list

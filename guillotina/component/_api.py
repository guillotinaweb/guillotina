##############################################################################
#
# Copyright (c) 2001, 2002 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# flake8: noqa
from guillotina.component._compat import _BLANK
from guillotina.component._declaration import adapter  # noqa
from guillotina.component.hookable import hookable
from guillotina.component.interfaces import ComponentLookupError
from guillotina.component.interfaces import IComponentLookup
from guillotina.component.interfaces import IFactory
from zope.interface import Interface

import sys
import zope.interface.interface


# getSiteManager() returns a component registry.  Although the term
# "site manager" is deprecated in favor of "component registry",
# the old term is kept around to maintain a stable API.
base = None


@hookable
def getSiteManager(context=None):
    """ See IComponentArchitecture.
    """
    global base
    if context is None:
        if base is None:
            from guillotina.component.globalregistry import base
        return base
    else:
        # Use the global site manager to adapt context to `IComponentLookup`
        # to avoid the recursion implied by using a local `getAdapter()` call.
        try:
            return IComponentLookup(context)
        except TypeError as error:
            raise ComponentLookupError(*error.args)


def getAdapterInContext(object, interface, context):
    adapter_ = queryAdapterInContext(object, interface, context)
    if adapter_ is None:
        raise ComponentLookupError(object, interface)
    return adapter_


def queryAdapterInContext(object, interface, context, default=None):
    conform = getattr(object, '__conform__', None)
    if conform is not None:
        try:
            adapter_ = conform(interface)
        except TypeError:
            # We got a TypeError. It might be an error raised by
            # the __conform__ implementation, or *we* may have
            # made the TypeError by calling an unbound method
            # (object is a class).  In the later case, we behave
            # as though there is no __conform__ method. We can
            # detect this case by checking whether there is more
            # than one traceback object in the traceback chain:
            if sys.exc_info()[2].tb_next is not None:
                # There is more than one entry in the chain, so
                # reraise the error:
                raise
            # This clever trick is from Phillip Eby
        else:
            if adapter_ is not None:
                return adapter_

    if interface.providedBy(object):
        return object

    return getSiteManager(context).queryAdapter(object, interface, '', default)


def getAdapter(object, interface=Interface, name=_BLANK, context=None):
    adapter_ = queryAdapter(object, interface, name, None, context)
    if adapter_ is None:
        raise ComponentLookupError(object, interface, name)
    return adapter_


def queryAdapter(object, interface=Interface, name=_BLANK, default=None,
                 context=None):
    if context is None:
        return adapter_hook(interface, object, name, default)
    return getSiteManager(context).queryAdapter(object, interface, name,
                                                default)


def getMultiAdapter(objects, interface=Interface, name=_BLANK, context=None):
    adapter_ = queryMultiAdapter(objects, interface, name, context=context)
    if adapter_ is None:
        raise ComponentLookupError(objects, interface, name)
    return adapter_


def queryMultiAdapter(objects, interface=Interface, name=_BLANK, default=None,
                      context=None):
    try:
        sitemanager = getSiteManager(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return default

    return sitemanager.queryMultiAdapter(objects, interface, name, default)


def getAdapters(objects, provided, context=None):
    try:
        sitemanager = getSiteManager(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []
    return sitemanager.getAdapters(objects, provided)


def subscribers(objects, interface, context=None):
    try:
        sitemanager = getSiteManager(context)
    except ComponentLookupError:
        # Oh blast, no site manager. This should *never* happen!
        return []
    return sitemanager.subscribers(objects, interface)


def handle(*objects):
    getSiteManager(None).subscribers(objects, None)

#############################################################################
# Register the component architectures adapter hook, with the adapter hook
# registry of the `zope.inteface` package. This way we will be able to call
# interfaces to create adapters for objects. For example, `I1(ob)` is
# equvalent to `getAdapterInContext(I1, ob, '')`.


@hookable
def adapter_hook(interface, object, name='', default=None):
    try:
        sitemanager = getSiteManager()
    except ComponentLookupError:  # pragma NO COVER w/o context, cannot test
        # Oh blast, no site manager. This should *never* happen!
        return None
    return sitemanager.queryAdapter(object, interface, name, default)


zope.interface.interface.adapter_hooks.append(adapter_hook)
#############################################################################


# Utility API

def getUtility(interface, name='', context=None):
    utility = queryUtility(interface, name, context=context)
    if utility is not None:
        return utility
    raise ComponentLookupError(interface, name)


def queryUtility(interface, name='', default=None, context=None):
    return getSiteManager(context).queryUtility(interface, name, default)


def getUtilitiesFor(interface, context=None):
    return getSiteManager(context).getUtilitiesFor(interface)


def getAllUtilitiesRegisteredFor(interface, context=None):
    return getSiteManager(context).getAllUtilitiesRegisteredFor(interface)


_marker = object()


def getFactoryInterfaces(name, context=None):
    """Return the interface provided by the named factory's objects

    Result might be a single interface. XXX
    """
    return getUtility(IFactory, name, context).get_interfaces()


def getFactoriesFor(interface, context=None):
    """Return info on all factories implementing the given interface.
    """
    utils = getSiteManager(context)
    for (name, factory) in utils.getUtilitiesFor(IFactory):
        interfaces = factory.get_interfaces()
        try:
            if interfaces.isOrExtends(interface):
                yield name, factory
        except AttributeError:
            for iface in interfaces:
                if iface.isOrExtends(interface):
                    yield name, factory
                    break

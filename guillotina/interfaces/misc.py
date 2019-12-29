from guillotina.db.orm.interfaces import IBaseObject
from guillotina.interfaces.content import IApplication
from typing import Optional
from typing import Tuple
from typing import Type
from zope.interface import Interface


class IRequest(Interface):
    url: str
    path: str
    method: str
    resource: Optional[IBaseObject]
    tail: Optional[Tuple[str, ...]]
    exc: Optional[Exception]
    found_view: Optional[Type]
    view_name: Optional[str]
    application: Optional[IApplication]

    def record(event_name) -> None:
        """
        record request event
        """


class ILanguage(Interface):
    pass


# Target interfaces on resolving


class IRenderer(Interface):
    pass


# Get Absolute URL


class IAbsoluteURL(Interface):
    pass


# Addon interface


class IAddOn(Interface):
    def install(container, request):  # noqa: N805
        """
        """

    def uninstall(container, request):  # noqa: N805
        """
        """


# Walking interface
class IIteratorResources(Interface):
    pass

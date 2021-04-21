from datetime import datetime
from dateutil.tz import tzutc
from guillotina import configure
from guillotina import task_vars
from guillotina._cache import BEHAVIOR_CACHE
from guillotina._cache import FACTORY_CACHE
from guillotina._cache import PERMISSIONS_CACHE
from guillotina._cache import SCHEMA_CACHE
from guillotina._settings import app_settings
from guillotina.annotations import AnnotationData
from guillotina.auth.users import ANONYMOUS_USER_ID
from guillotina.auth.users import ROOT_USER_ID
from guillotina.behaviors import apply_markers
from guillotina.browser import get_physical_path
from guillotina.component import get_adapter
from guillotina.component import get_utilities_for
from guillotina.component import get_utility
from guillotina.component import query_utility
from guillotina.component.factory import Factory
from guillotina.db import uid
from guillotina.db.interfaces import ITransaction
from guillotina.db.orm.interfaces import IBaseObject
from guillotina.event import notify
from guillotina.events import BeforeObjectAddedEvent
from guillotina.events import BeforeObjectMovedEvent
from guillotina.events import ObjectDuplicatedEvent
from guillotina.events import ObjectLoadedEvent
from guillotina.events import ObjectMovedEvent
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import InvalidContentType
from guillotina.exceptions import MaxDepthReached
from guillotina.exceptions import NoPermissionToAdd
from guillotina.exceptions import NotAllowedContentType
from guillotina.exceptions import PreconditionFailed
from guillotina.exceptions import TransactionNotFound
from guillotina.interfaces import DEFAULT_ADD_PERMISSION
from guillotina.interfaces import IAddons
from guillotina.interfaces import IAnnotations
from guillotina.interfaces import IAsyncBehavior
from guillotina.interfaces import IBehavior
from guillotina.interfaces import IConstrainTypes
from guillotina.interfaces import IContainer
from guillotina.interfaces import IFolder
from guillotina.interfaces import IGetOwner
from guillotina.interfaces import IIDChecker
from guillotina.interfaces import IItem
from guillotina.interfaces import IJavaScriptApplication
from guillotina.interfaces import ILayers
from guillotina.interfaces import IPermission
from guillotina.interfaces import IPrincipalPermissionManager
from guillotina.interfaces import IPrincipalRoleManager
from guillotina.interfaces import IRequest
from guillotina.interfaces import IResource
from guillotina.interfaces import IResourceFactory
from guillotina.interfaces import IStaticDirectory
from guillotina.interfaces import IStaticFile
from guillotina.profile import profilable
from guillotina.registry import REGISTRY_DATA_KEY
from guillotina.response import HTTPConflict
from guillotina.schema.utils import get_default_from_schema
from guillotina.security.security_code import PrincipalPermissionManager
from guillotina.transactions import get_transaction
from guillotina.utils import get_content_depth
from guillotina.utils import get_object_by_uid
from guillotina.utils import get_security_policy
from guillotina.utils import navigate_to
from guillotina.utils import valid_id
from guillotina.utils.auth import get_authenticated_user_id
from typing import Any
from typing import AsyncIterator
from typing import cast
from typing import Dict
from typing import FrozenSet
from typing import Iterator
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import Interface
from zope.interface import noLongerProvides
from zope.interface.interfaces import ComponentLookupError

import guillotina.db.orm.base
import os
import pathlib


_zone = tzutc()  # utz tz is much faster than local tz info
_marker = object()


@implementer(IResourceFactory)
class ResourceFactory(Factory):
    type_name = None
    schema = None
    behaviors = None
    add_permission = None

    def __init__(
        self,
        klass,
        title="",
        description="",
        type_name="",
        schema=None,
        behaviors=None,
        add_permission=DEFAULT_ADD_PERMISSION,
        allowed_types=None,
    ):
        super(ResourceFactory, self).__init__(
            klass, title, description, tuple(filter(bool, [schema] + list(behaviors) or list()))
        )
        self.type_name = type_name
        self.schema = schema or Interface
        self.behaviors = behaviors or ()
        self.add_permission = add_permission
        self.allowed_types = allowed_types

    @profilable
    def __call__(self, id, parent=None, *args, **kw):
        obj = super(ResourceFactory, self).__call__(*args, **kw)
        if parent is not None:
            obj.__parent__ = parent
        obj.type_name = self.type_name
        now = datetime.now(tz=_zone)
        obj.creation_date = now
        obj.modification_date = now
        if id is None:
            if obj.__uuid__ is None:
                obj.__uuid__ = app_settings["uid_generator"](obj)
            obj.id = uid.get_short_uid(obj.__uuid__)
        else:
            obj.id = id
        obj.__name__ = obj.id
        apply_markers(obj)
        return obj

    @profilable
    def get_interfaces(self):
        spec = super(ResourceFactory, self).get_interfaces()
        spec.__name__ = self.type_name
        return spec

    def __repr__(self):
        return "<{0:s} for {1:s}>".format(self.__class__.__name__, self.type_name)


@implementer(IResource)
class Resource(guillotina.db.orm.base.BaseObject):
    """
    Base resource object class
    """

    __behaviors__: FrozenSet[str] = frozenset({})
    __acl__: Optional[Dict[str, Any]] = None

    type_name: Optional[str] = None
    creation_date = None
    modification_date = None
    title = None
    creators = ()
    contributors = ()

    @property
    def uuid(self):
        """
        The unique id of the content object
        """
        return self.__uuid__

    def __init__(self, id: str = None) -> None:
        if id is not None:
            self.__name__ = id
        super(Resource, self).__init__()

    def __repr__(self):
        """"""
        path = "/".join(get_physical_path(self))
        return "< {type} at {path} by {mem} >".format(type=self.type_name, path=path, mem=id(self))

    @property
    def acl(self) -> dict:
        """
        Access control list stores security information on the object
        """
        if self.__acl__ is None:
            return dict({})
        return self.__acl__

    def set_id(self, id_):
        if id_ is not None:
            self.__name__ = id_

    def get_id(self):
        return self.__name__

    id = property(get_id, set_id)

    @property
    def __behaviors_schemas__(self):
        """Get the dynamic schemas."""
        for behavior in self.__behaviors__:
            yield BEHAVIOR_CACHE[behavior]

    def add_behavior(self, iface: Union[str, Interface]) -> None:
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__  # type: ignore
        else:
            raise AttributeError("Cant identify Interface")
        behavior_registration = get_utility(IBehavior, name=name)
        if behavior_registration is not None and behavior_registration.interface(self) is not None:
            factory_behaviors = get_cached_factory(self.type_name).behaviors or ()
            # We can adapt so we can apply this dynamic behavior
            if behavior_registration.interface not in factory_behaviors and name not in self.__behaviors__:
                self.__behaviors__ |= {name}
                if behavior_registration.marker is not None:
                    alsoProvides(self, behavior_registration.marker)
                self.register()  # make sure we resave this obj

    def remove_behavior(self, iface: Union[str, Interface]) -> None:
        """We need to apply the marker interface.

        value: Interface to add
        """
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__  # type: ignore
        behavior_registration = get_utility(IBehavior, name=name)
        if behavior_registration is not None and behavior_registration.marker is not None:
            try:
                noLongerProvides(self, behavior_registration.marker)
            except ValueError:
                # could not remove interface
                pass
        if iface in self.__behaviors__:
            self.__behaviors__ -= {name}
        self.register()  # make sure we resave this obj

    @profilable
    def __getattr__(self, name):
        # python basics:  __getattr__ is only invoked if the attribute wasn't
        # found by __getattribute__
        #
        # optimization: sometimes we're asked for special attributes
        # such as __conform__ that we can disregard (because we
        # wouldn't be in here if the class had such an attribute
        # defined).
        # also handle special dynamic providedBy cache here.
        # also handle the get_current_request call
        if name.startswith("__") or name == "_v__providedBy__" or name == "request":
            raise AttributeError(name)

        # attribute was not found; try to look it up in the schema and return
        # a default
        value = get_default_from_schema(
            self, SCHEMA_CACHE.get(self.type_name, {}).get("schema"), name, _marker
        )
        if value is not _marker:
            setattr(self, name, value)
            return value
        raise AttributeError(name)


@configure.contenttype(
    type_name="Item", schema=IItem, behaviors=["guillotina.behaviors.dublincore.IDublinCore"]
)
class Item(Resource):
    """
    Basic item content type. Inherits from Resource
    """


@configure.contenttype(
    type_name="Folder", schema=IFolder, behaviors=["guillotina.behaviors.dublincore.IDublinCore"]
)
class Folder(Resource):
    """
    Basic folder content type. Inherits from Resource but provides interface
    to work with contained objects asynchronously.
    """

    def _get_transaction(self) -> ITransaction:
        txn = get_transaction()
        if txn is not None:
            return txn
        if self.__txn__ is not None:
            return self.__txn__
        raise TransactionNotFound()

    async def async_contains(self, key: str) -> bool:
        """
        Asynchronously check if key exists inside this folder

        :param key: key of child object to check
        """
        return await self._get_transaction().contains(self.__uuid__, key)

    async def async_set(self, key: str, value: Resource) -> None:
        """
        Asynchronously set an object in this folder

        :param key: key of child object to set
        :param value: object to set as child
        """
        value.__parent__ = self
        value.__name__ = key
        trns = self._get_transaction()
        if trns is not None:
            value.__txn__ = trns
            trns.register(value)

    async def async_get(self, key: str, default=None, suppress_events=False) -> Optional[IBaseObject]:
        """
        Asynchronously get an object inside this folder

        :param key: key of child object to get
        """
        try:
            txn = self._get_transaction()
            val = await txn.get_child(self, key)
            if val is not None:
                if not suppress_events:
                    await notify(ObjectLoadedEvent(val))
                return val
        except KeyError:
            pass
        return default

    async def async_multi_get(
        self, keys: List[str], default=None, suppress_events=False
    ) -> AsyncIterator[IBaseObject]:
        """
        Asynchronously get an multiple objects inside this folder

        :param keys: keys of child objects to get
        """
        txn = self._get_transaction()
        async for item in txn.get_children(self, keys):  # type: ignore
            yield item

    async def async_del(self, key: str) -> None:
        """
        Asynchronously delete object in the folder

        :param key: key of child objec to delete
        """
        txn = self._get_transaction()
        obj = await self.async_get(key)
        if obj is not None:
            return txn.delete(obj)

    async def async_len(self) -> int:
        """
        Asynchronously calculate the len of the folder
        """
        return await self._get_transaction().len(self.__uuid__)

    async def async_keys(self) -> List[str]:
        """
        Asynchronously get the sub object keys in this folder
        """
        return await self._get_transaction().keys(self.__uuid__)

    async def async_items(self, suppress_events=False) -> AsyncIterator[Tuple[str, Resource]]:
        """
        Asynchronously iterate through contents of folder
        """
        txn = self._get_transaction()
        async for key, value in txn.items(self):  # type: ignore
            if not suppress_events:
                await notify(ObjectLoadedEvent(value))
            yield key, value

    async def async_values(self, suppress_events=False) -> AsyncIterator[Tuple[Resource]]:
        txn = self._get_transaction()
        async for _, value in txn.items(self):  # type: ignore
            if not suppress_events:
                await notify(ObjectLoadedEvent(value))
            yield value


@configure.contenttype(type_name="Container", schema=IContainer)
class Container(Folder):
    """"""

    async def install(self):
        # Creating and registering a local registry
        from guillotina.registry import Registry

        annotations_container = IAnnotations(self)
        registry = Registry()
        await annotations_container.async_set(REGISTRY_DATA_KEY, registry)

        # Set default plugins
        registry.register_interface(ILayers)
        registry.register_interface(IAddons)
        layers = registry.for_interface(ILayers)
        layers["active_layers"] = frozenset()

        roles = IPrincipalRoleManager(self)
        roles.assign_role_to_principal("guillotina.ContainerAdmin", ROOT_USER_ID)

        roles.assign_role_to_principal("guillotina.Owner", ROOT_USER_ID)


@implementer(IStaticFile)
class StaticFile(object):
    def __init__(self, file_path: pathlib.Path) -> None:
        self.file_path = file_path


@implementer(IStaticDirectory)
class StaticDirectory(dict):
    """
    Using dict makes this a simple container so traversing works
    """

    def __init__(self, file_path: pathlib.Path, base_path: pathlib.Path = None) -> None:
        self.file_path = file_path
        if base_path is None:
            self.base_path = file_path
        else:
            self.base_path = base_path

    def __getitem__(self, filename):
        path = pathlib.Path(os.path.join(self.file_path.absolute(), filename))
        if not path.exists():
            raise KeyError(filename)
        if path.is_dir():
            return StaticDirectory(path, self.base_path)
        else:
            return StaticFile(path)

    def __contains__(self, filename):
        try:
            return self[filename] is not None
        except KeyError:
            return False


@implementer(IJavaScriptApplication)
class JavaScriptApplication(StaticDirectory):
    """
    Same as StaticDirectory; however, it renders /index.html for every
    sub-directory
    """

    def __getitem__(self, filename):
        if filename.lower() in app_settings["default_static_filenames"]:
            path = pathlib.Path(os.path.join(self.base_path.absolute(), filename))
            return StaticFile(path)
        path = pathlib.Path(os.path.join(self.file_path.absolute(), filename))
        if path.is_dir() or not path.exists():
            return JavaScriptApplication(path, self.base_path)
        else:
            return StaticFile(path)

    def __contains__(self, filename):
        if not self.file_path.exists():
            # we're in every path is valid mode
            return True
        try:
            return self[filename] is not None
        except KeyError:
            return False


@configure.adapter(for_=IStaticFile, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IStaticDirectory, provides=IPrincipalPermissionManager)
@configure.adapter(for_=IJavaScriptApplication, provides=IPrincipalPermissionManager)
class StaticFileSpecialPermissions(PrincipalPermissionManager):
    def __init__(self, db):
        super(StaticFileSpecialPermissions, self).__init__()
        self.grant_permission_to_principal("guillotina.AccessContent", ANONYMOUS_USER_ID)


@configure.utility(provides=IGetOwner)
async def default_get_owner(obj, creator):
    return creator


def load_cached_schema():
    for x in get_utilities_for(IResourceFactory):
        factory = x[1]
        if factory.type_name not in SCHEMA_CACHE:
            FACTORY_CACHE[factory.type_name] = factory
            behaviors_registrations = []
            for iface in factory.behaviors or ():
                if Interface.providedBy(iface):
                    name = iface.__identifier__
                else:
                    name = iface
                behaviors_registrations.append(get_utility(IBehavior, name=name))
            SCHEMA_CACHE[factory.type_name] = {"behaviors": behaviors_registrations, "schema": factory.schema}
    for iface, utility in get_utilities_for(IBehavior):
        if isinstance(iface, str):
            name = iface
        elif Interface.providedBy(iface):
            name = iface.__identifier__
        if name not in BEHAVIOR_CACHE:
            BEHAVIOR_CACHE[name] = utility.interface


def get_cached_factory(type_name):
    if type_name in FACTORY_CACHE:
        factory = FACTORY_CACHE[type_name]
    else:
        try:
            factory = get_utility(IResourceFactory, type_name)
        except ComponentLookupError:
            raise InvalidContentType(type_name)
        FACTORY_CACHE[type_name] = factory
    return factory


def iter_schemata_for_type(type_name):
    factory = get_cached_factory(type_name)
    if factory.schema is not None:
        yield factory.schema
    for schema in factory.behaviors or ():
        yield schema


def get_all_possible_schemas_for_type(type_name) -> List[Interface]:
    result = set()
    factory = get_cached_factory(type_name)
    if factory.schema is not None:
        result.add(factory.schema)
    for schema in factory.behaviors or ():
        result.add(schema)
    for _, utility in get_utilities_for(IBehavior):
        if utility.for_.isEqualOrExtendedBy(factory.schema):
            result.add(utility.interface)
    return [b for b in result]


def iter_schemata(obj) -> Iterator[Interface]:
    type_name = obj.type_name
    for schema in iter_schemata_for_type(type_name):
        yield schema
    for schema in obj.__behaviors_schemas__:
        yield schema


@profilable
async def create_content(type_, **kw) -> IResource:
    """Utility to create a content.

    This method should not be used to add content, just internally.
    """
    factory = get_cached_factory(type_)
    id_ = kw.pop("id", None)

    # We create the object with at least the ID
    obj = factory(id=id_)
    for key, value in kw.items():
        setattr(obj, key, value)
    obj.__new_marker__ = True
    return obj


@profilable
async def create_content_in_container(
    parent: Folder, type_: str, id_: str, request: IRequest = None, check_security=True, **kw
) -> Resource:
    """Utility to create a content.

    This method is the one to use to create content.
    `id_` can be None

    :param parent: where to create content inside of
    :param type_: content type to create
    :param id_: id to give content in parent object
    :param request: <optional>
    :param check_security: be able to disable security checks
    """
    factory = get_cached_factory(type_)

    if check_security and factory.add_permission:
        if factory.add_permission in PERMISSIONS_CACHE:
            permission = PERMISSIONS_CACHE[factory.add_permission]
        else:
            permission = query_utility(IPermission, name=factory.add_permission)
            PERMISSIONS_CACHE[factory.add_permission] = permission

        if permission is not None:
            policy = get_security_policy()
            if not policy.check_permission(permission.id, parent):
                raise NoPermissionToAdd(str(parent), type_)

    constrains = IConstrainTypes(parent, None)
    if constrains is not None:
        if not constrains.is_type_allowed(type_):
            raise NotAllowedContentType(str(parent), type_)

    # Restrict object tree height
    max_depth = app_settings.get("max_content_depth", None)
    if max_depth is not None and get_content_depth(parent) > max_depth:
        raise MaxDepthReached()

    # We create the object with at least the ID
    obj = factory(id=id_, parent=parent)
    for key, value in kw.items():
        if key == "id":
            # the factory sets id
            continue
        setattr(obj, key, value)

    txn: Optional[ITransaction]
    if hasattr(parent, "_get_transaction"):
        txn = parent._get_transaction()
    else:
        txn = cast(Optional[ITransaction], getattr(parent, "__txn__", None) or get_transaction())
    if txn is None or not txn.storage.supports_unique_constraints:
        # need to manually check unique constraints
        if await parent.async_contains(obj.id):
            raise ConflictIdOnContainer(f"Duplicate ID: {parent} -> {obj.id}")

    obj.__new_marker__ = True

    await notify(BeforeObjectAddedEvent(obj, parent, id_))

    await parent.async_set(obj.id, obj)
    return obj


def get_all_behavior_interfaces(content) -> list:
    factory = get_cached_factory(content.type_name)
    behaviors = []
    for behavior_schema in factory.behaviors or ():
        behaviors.append(behavior_schema)

    for dynamic_behavior in content.__behaviors_schemas__:
        if dynamic_behavior not in behaviors:
            behaviors.append(dynamic_behavior)
    return behaviors


async def get_all_behaviors(content, create=False, load=True) -> list:
    behaviors = []
    for behavior_schema in get_all_behavior_interfaces(content):
        behavior = behavior_schema(content)
        if load:
            if IAsyncBehavior.implementedBy(behavior.__class__):  # pylint: disable=E1120
                # providedBy not working here?
                await behavior.load(create=create)
        behaviors.append((behavior_schema, behavior))
    return behaviors


async def duplicate(
    context: IResource,
    destination: Optional[Union[IResource, str]] = None,
    new_id: Optional[str] = None,
    check_permission: bool = True,
    reset_acl: bool = False,
) -> IResource:
    if destination is not None:
        if isinstance(destination, str):
            destination_ob = None
            if destination.startswith("/"):
                container = task_vars.container.get()
                if container:
                    try:
                        destination_ob = await navigate_to(container, destination)
                    except KeyError:
                        pass
            else:
                try:
                    destination_ob = await get_object_by_uid(destination)
                except KeyError:
                    pass
        else:
            destination_ob = destination

        if destination_ob is None:
            raise PreconditionFailed(context, "Could not find destination object")
    else:
        destination_ob = context.__parent__

    if check_permission:
        policy = get_security_policy()
        if not policy.check_permission("guillotina.AddContent", destination_ob):
            raise PreconditionFailed(
                context, "You do not have permission to add content to " "the destination object"
            )

    if new_id is not None:
        if await destination_ob.async_contains(new_id):
            raise PreconditionFailed(context, f"Destination already has object with the id {new_id}")
    else:
        count = 1
        new_id = f"{context.id}-duplicate-{count}"
        while await destination_ob.async_contains(new_id):
            count += 1
            new_id = f"{context.id}-duplicate-{count}"

    from guillotina.content import create_content_in_container

    creators = context.creators
    contributors = context.contributors
    user_id = get_authenticated_user_id()
    if reset_acl:
        creators = [user_id]
        contributors = [user_id]
    new_obj = await create_content_in_container(
        destination_ob,
        context.type_name,
        new_id,
        id=new_id,
        creators=creators,
        contributors=contributors,
        check_security=check_permission,
    )
    for key in context.__dict__.keys():
        if key.startswith("__") or key.startswith("_BaseObject"):
            continue
        if key in ("id", "creators", "contributors"):
            continue
        new_obj.__dict__[key] = context.__dict__[key]

    if reset_acl:
        new_obj.__acl__ = None
        get_owner = get_utility(IGetOwner)
        roleperm = IPrincipalRoleManager(new_obj)
        owner = await get_owner(new_obj, user_id)
        if owner is not None:
            roleperm.assign_role_to_principal("guillotina.Owner", owner)
    else:
        new_obj.__acl__ = context.__acl__

    for behavior in context.__behaviors__:
        new_obj.add_behavior(behavior)
    # need to copy annotation data as well...
    # load all annotations for context
    [b for b in await get_all_behaviors(context, load=True)]
    annotations_container = IAnnotations(new_obj)
    for anno_id, anno_data in context.__gannotations__.items():
        new_anno_data = AnnotationData()
        for key, value in anno_data.items():
            new_anno_data[key] = value
        await annotations_container.async_set(anno_id, new_anno_data)

    await notify(
        ObjectDuplicatedEvent(
            new_obj, context, destination_ob, new_id, payload={"id": new_id, "destination": destination}
        )
    )
    return new_obj


async def move(
    context: IResource,
    destination: Optional[Union[IResource, str]] = None,
    new_id: Optional[str] = None,
    check_permission: bool = True,
) -> None:
    if destination is None:
        destination_ob = context.__parent__
    else:
        if isinstance(destination, str):
            destination_ob = None
            if destination.startswith("/"):
                container = task_vars.container.get()
                if container is not None:
                    try:
                        destination_ob = await navigate_to(container, destination)
                    except KeyError:
                        pass
            else:
                try:
                    destination_ob = await get_object_by_uid(destination)
                except KeyError:
                    pass
        else:
            destination_ob = destination

    if destination_ob is None:
        raise PreconditionFailed(context, "Could not find destination object")
    if destination_ob.__uuid__ == context.__uuid__:
        raise PreconditionFailed(context, "You can not move object to itself")
    if destination_ob.__uuid__ == context.__parent__.__uuid__ and new_id == context.id:
        raise PreconditionFailed(context, "Object already belongs to this parent with same id")

    txn = get_transaction()
    if txn is not None:
        cache_keys = txn._cache.get_cache_keys(context, "deleted")

    old_id = context.id
    if new_id is not None:
        id_checker = get_adapter(context, IIDChecker)
        if not isinstance(new_id, str) or not await id_checker(new_id, context.type_name):
            raise PreconditionFailed(new_id, "Invalid id")
        context.id = context.__name__ = new_id
    else:
        new_id = context.id

    if check_permission:
        policy = get_security_policy()
        if not policy.check_permission("guillotina.AddContent", destination_ob):
            raise PreconditionFailed(
                context, "You do not have permission to add content to the " "destination object"
            )

    if await destination_ob.async_contains(new_id):
        raise HTTPConflict(content={"reason": f'Destination already has object with the id "{new_id}"'})

    original_parent = context.__parent__

    await notify(
        BeforeObjectMovedEvent(
            context,
            original_parent,
            old_id,
            destination_ob,
            new_id,
            payload={"id": new_id, "destination": destination},
        )
    )

    context.__parent__ = destination_ob
    context.register()

    await notify(
        ObjectMovedEvent(
            context,
            original_parent,
            old_id,
            destination_ob,
            new_id,
            payload={"id": new_id, "destination": destination},
        )
    )

    if txn is not None:
        cache_keys += txn._cache.get_cache_keys(context, "added")
        await txn._cache.delete_all(cache_keys)


@configure.adapter(for_=IResource, provides=IIDChecker)
class DefaultIDChecker:
    def __init__(self, context):
        self.context = context

    async def __call__(self, id_: str, type_: str) -> bool:
        return valid_id(id_)

from guillotina._settings import app_settings
from guillotina.interfaces import IUnauthorized
from zope.interface import implementer
from zope.interface.exceptions import Invalid  # noqa pylint: disable=W0611
from zope.interface.interfaces import ComponentLookupError  # noqa pylint: disable=W0611

import ujson


class NoPermissionToAdd(Exception):
    def __init__(self, container, content_type):
        super().__init__()
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not permission to add {content_type} on {container}".format(
            content_type=self.content_type, container=self.container
        )


class InvalidContentType(Exception):
    def __init__(self, content_type):
        super().__init__()
        self.content_type = content_type

    def __repr__(self):
        return "Invalid type: {content_type}".format(content_type=self.content_type)


class NotAllowedContentType(Exception):
    def __init__(self, container, content_type):
        super().__init__()
        self.container = container
        self.content_type = content_type

    def __repr__(self):
        return "Not allowed {content_type} on {container}".format(
            content_type=self.content_type, container=self.container
        )


class ConflictIdOnContainer(Exception):
    def __init__(self, pg_exc):
        super().__init__()
        self.pg_exc = pg_exc

    def __repr__(self):
        msg = getattr(self.pg_exc, "detail", None) or getattr(self.pg_exc, "message", None) or self.pg_exc
        return f"Conflict ID {msg}"


class TransactionClosedException(Exception):
    def __init__(self, msg, txn, ob):
        super().__init__(msg)
        self.txn = txn
        self.object = ob


class TransactionMismatchException(Exception):
    def __init__(self, msg, txn, ob):
        super().__init__(msg)
        self.txn = txn
        self.object = ob


class UnRetryableRequestError(Exception):
    pass


class MaxDepthReached(Exception):
    pass


class PreconditionFailed(Exception):
    def __init__(self, container, precondition):
        super().__init__()
        self.container = container
        self.precondition = precondition

    def __repr__(self):
        return "Precondition Failed {precondition} on {path}".format(
            precondition=self.precondition, path=self.container
        )


class RequestNotFound(Exception):
    """
    Lookup for the current request for request aware task failed
    """


class TransactionNotFound(Exception):
    """
    Lookup for the current request for request aware task failed
    """


class ContainerNotFound(Exception):
    """
    Lookup for the current container for request aware task failed
    """


class DatabaseNotFound(Exception):
    """
    Lookup for the current db for request aware task failed
    """


class ApplicationNotFound(Exception):
    """
    Could not find application
    """


@implementer(IUnauthorized)
class Unauthorized(Exception):
    """Some user wasn't allowed to access a resource"""


class ConflictError(Exception):
    def __init__(self, msg="", oid=None, txn=None, old_serial=None, writer=None):
        super().__init__()
        if oid is not None:
            conflict_summary = self.get_conflict_summary(oid, txn, old_serial, writer)
            msg = f"{msg}.\n{conflict_summary}"
        super().__init__(msg)

    def get_conflict_summary(self, oid, txn, old_serial, writer):
        from guillotina.utils import get_current_request

        try:
            req = get_current_request()
        except RequestNotFound:
            req = None
        max_attempts = app_settings.get("conflict_retry_attempts", 3)
        attempts = getattr(req, "_retry_attempt", 0)
        return f"""Object ID: {oid}
TID: {txn._tid}
Old Object TID: {old_serial}
Belongs to: {writer.of}
Parent ID: {writer.id}
Retries: {attempts}/{max_attempts}"""


class TIDConflictError(ConflictError):
    pass


class RestartCommit(Exception):
    """
    Commits requires restart
    """


class ConfigurationError(Exception):
    """There was an error in a configuration"""


class ServiceConfigurationError(ConfigurationError):
    pass


class ComponentConfigurationError(ValueError, ConfigurationError):
    pass


class ConfigurationConflictError(ConfigurationError):
    def __init__(self, conflicts):
        super().__init__()
        self._conflicts = conflicts

    def __str__(self):  # pragma NO COVER
        r = ["Conflicting configuration actions"]
        items = self._conflicts.items()
        items.sort()
        for discriminator, infos in items:
            r.append("  For: %s" % (discriminator,))
            for info in infos:
                for line in str(info).rstrip().split("\n"):
                    r.append("    " + line)

        return "\n".join(r)


class NoIndexField(Exception):
    pass


class ReadOnlyError(Exception):
    pass


class BlobChunkNotFound(Exception):
    pass


class DeserializationError(Exception):
    """An error happened during deserialization of content."""

    def __init__(self, errors):
        super().__init__()
        self.msg = self.message = "Error deserializing content"
        self.errors = errors

    def __str__(self):
        return "{} ({})".format(self.msg, ujson.dumps(self.json_data()))  # pylint: disable=I1101

    def json_data(self):
        errors = []
        for error in self.errors:
            # need to clean raw exceptions out of this list here...
            error = error.copy()
            if "error" in error:
                error.pop("error")
            errors.append(error)
        return {"deserialization_errors": errors}


class ValueDeserializationError(Exception):
    """An error happened during deserialization of content."""

    def __init__(self, field, value, msg):
        super().__init__()
        self.msg = self.message = msg
        self.field = field
        self.value = value


class QueryParsingError(Exception):
    """An error happened while parsing a search query."""


class FileNotFoundException(Exception):
    pass


class ServerClosingException(Exception):
    """
    Server closing, can not perform action
    """


class NoPubSubUtility(Exception):
    """
    No PubSub Utility found
    """


class NoChannelConfigured(Exception):
    """
    No Channel Configured
    """


class TransactionObjectRegistrationMismatchException(Exception):
    def __init__(self, registered_object, object):
        self.registered_object = registered_object
        self.object = object
        super().__init__(
            f"Object already registered for this transaction with same uid "
            f"but different object instance: {registered_object.uuid}"
        )

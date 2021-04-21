from guillotina import configure
from guillotina import error_reasons
from guillotina.exceptions import ConflictIdOnContainer
from guillotina.exceptions import DeserializationError
from guillotina.exceptions import InvalidContentType
from guillotina.exceptions import MaxDepthReached
from guillotina.exceptions import NotAllowedContentType
from guillotina.exceptions import PreconditionFailed
from guillotina.exceptions import Unauthorized
from guillotina.exceptions import UnRetryableRequestError
from guillotina.interfaces import IErrorResponseException
from guillotina.response import HTTPConflict
from guillotina.response import HTTPExpectationFailed
from guillotina.response import HTTPPreconditionFailed
from guillotina.response import HTTPUnauthorized
from guillotina.response import Response

import json


def render_error_response(error, reason, eid=None):
    data = {"reason": reason.name, "details": reason.details, "type": error}
    if eid is not None:
        data["eid"] = eid
    return data


def exception_handler_factory(
    reason, name="PreconditionFailed", klass=HTTPPreconditionFailed, serialize_exc=False
):
    def handler(exc, error="", eid=None):
        data = render_error_response(name, reason, eid)
        if serialize_exc:
            data["message"] = repr(exc)
        return klass(content=data)

    return handler


def deserialization_error_handler(exc, error="", eid=None) -> Response:
    data = render_error_response("DeserializationError", error_reasons.DESERIALIZATION_FAILED, eid)
    data["message"] = repr(exc)
    data.update(exc.json_data())
    return HTTPPreconditionFailed(content=data)


def register_handler_factory(ExceptionKlass, factory):
    configure.adapter(for_=ExceptionKlass, provides=IErrorResponseException)(factory)


register_handler_factory(json.decoder.JSONDecodeError, exception_handler_factory(error_reasons.JSON_DECODE))
register_handler_factory(
    PreconditionFailed, exception_handler_factory(error_reasons.PRECONDITION_FAILED, serialize_exc=True)
)
register_handler_factory(
    NotAllowedContentType, exception_handler_factory(error_reasons.NOT_ALLOWED, serialize_exc=True)
)
register_handler_factory(
    ConflictIdOnContainer,
    exception_handler_factory(
        error_reasons.CONFLICT_ID, "ConflictId", serialize_exc=True, klass=HTTPConflict
    ),
)
register_handler_factory(DeserializationError, deserialization_error_handler)

register_handler_factory(
    InvalidContentType,
    exception_handler_factory(
        error_reasons.DESERIALIZATION_FAILED, "DeserializationError", serialize_exc=True
    ),
)
register_handler_factory(
    UnRetryableRequestError,
    exception_handler_factory(
        error_reasons.UNRETRYALBE_REQUEST,
        "UnRetryableRequestError",
        serialize_exc=True,
        klass=HTTPExpectationFailed,
    ),
)


register_handler_factory(
    Unauthorized,
    exception_handler_factory(
        error_reasons.UNAUTHORIZED, "Unauthorized", serialize_exc=True, klass=HTTPUnauthorized
    ),
)

register_handler_factory(
    MaxDepthReached,
    exception_handler_factory(error_reasons.PRECONDITION_FAILED, "MaxDepthReached", serialize_exc=True),
)

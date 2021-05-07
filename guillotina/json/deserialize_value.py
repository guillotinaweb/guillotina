# -*- coding: utf-8 -*-

try:
    # Pendulum's parser is faster than dateutil.parser for dates with format
    # RFC 3339/ISO 8601. See GH issue #974 for details.
    from pendulum.parsing import parse as _parse
    from functools import partial

    # When parse is called with `strict=False` it calls dateutil.parse() as fallback
    parse = partial(_parse, strict=False)
except ImportError:
    from dateutil.parser import parse

from guillotina import configure
from guillotina.component import ComponentLookupError
from guillotina.component import get_adapter
from guillotina.exceptions import ValueDeserializationError
from guillotina.interfaces import IJSONToValue
from guillotina.profile import profilable
from guillotina.schema._bootstrapinterfaces import IFromUnicode
from guillotina.schema.exceptions import ValidationError
from guillotina.schema.exceptions import WrongType
from guillotina.schema.interfaces import IBool
from guillotina.schema.interfaces import IDate
from guillotina.schema.interfaces import IDatetime
from guillotina.schema.interfaces import IDict
from guillotina.schema.interfaces import IField
from guillotina.schema.interfaces import IFrozenSet
from guillotina.schema.interfaces import IJSONField
from guillotina.schema.interfaces import IList
from guillotina.schema.interfaces import IObject
from guillotina.schema.interfaces import ISet
from guillotina.schema.interfaces import ITuple
from guillotina.schema.interfaces import IUnionField
from zope.interface import Interface

import datetime


_type_conversions = (int, str, float, bool)


@profilable
def schema_compatible(value, schema_or_field, context=None):
    """The schema_compatible function converts any value to guillotina.schema
    compatible data when possible, raising a TypeError for unsupported values.
    This is done by using the ISchemaCompatible converters.
    """
    if value is None:
        return value

    try:
        return get_adapter(schema_or_field, IJSONToValue, args=[value, context])
    except ComponentLookupError:
        raise ValueDeserializationError(schema_or_field, value, "Deserializer not found for field")


def _optimized_lookup(value, field, context):
    if getattr(field, "_type", None) in _type_conversions:
        # for primitive types, all we really do is return the value back.
        # this is costly for all the lookups
        if not isinstance(value, field._type):
            if isinstance(value, _type_conversions):
                try:
                    value = field._type(value)  # convert other types over
                except ValueError:
                    raise WrongType(value, field._type, field.__name__)
            else:
                raise WrongType(value, field._type, field.__name__)
        return value
    else:
        try:
            return schema_compatible(value, field, context)
        except ValidationError as error:
            raise ValueDeserializationError(field, value, "Wrong contained type", errors=[error])


@profilable
@configure.value_deserializer(Interface)
def default_value_converter(schema, value, context=None):
    if value == {}:
        return {}

    if not isinstance(value, dict):
        return value

    result = {}
    for key in value.keys():
        if not isinstance(key, str):
            raise ValueDeserializationError(schema, value, "Invalid key type provided")
        result[key] = _optimized_lookup(value[key], schema[key], context)
    return result


@configure.value_deserializer(IJSONField)
def json_dict_converter(schemafield, value, context=None):
    if value == {}:
        return {}

    return value


@profilable
@configure.value_deserializer(for_=IField)
def default_converter(field, value, context=None):
    return value


@configure.value_deserializer(IBool)
def bool_converter(field, value, context=None):
    return bool(value)


@profilable
@configure.value_deserializer(IFromUnicode)
def from_unicode_converter(field, value, context=None):
    if value is not None:
        if field._type is not None:
            if not isinstance(value, field._type):
                if isinstance(value, _type_conversions):
                    # only auto convert primitive types
                    try:
                        value = field._type(value)  # convert other types over
                    except ValueError:
                        raise WrongType(value, field._type, field.__name__)
                else:
                    raise WrongType(value, field._type, field.__name__)
        else:
            value = field.from_unicode(value)
    return value


@profilable
@configure.value_deserializer(IList)
def list_converter(field, value, context=None):
    if not isinstance(value, list):
        raise ValueDeserializationError(field, value, "Not an array")
    return [_optimized_lookup(item, field.value_type, context) for item in value]


@profilable
@configure.value_deserializer(ITuple)
def tuple_converter(field, value, context=None):
    return tuple(list_converter(field, value, context))


@configure.value_deserializer(ISet)
def set_converter(field, value, context=None):
    return set(list_converter(field, value, context))


@configure.value_deserializer(IFrozenSet)
def frozenset_converter(field, value, context=None):
    return frozenset(list_converter(field, value, context))


@profilable
@configure.value_deserializer(IDict)
def dict_converter(field, value, context=None):
    if value == {}:
        return {}

    if not isinstance(value, dict):
        raise ValueDeserializationError(field, value, "Not an object")

    result = {}
    for key in value.keys():
        if getattr(field, "key_type", None) and getattr(field.key_type, "_type", None):
            if not isinstance(key, field.key_type._type):
                raise ValueDeserializationError(field, value, "Invalid key type provided")
        result[key] = _optimized_lookup(value[key], field.value_type, context)
    return result


@configure.value_deserializer(IDatetime)
def datetime_converter(field, value, context=None):
    if not isinstance(value, str):
        raise ValueDeserializationError(field, value, "Not a string")
    return parse(value)


@configure.value_deserializer(IDate)
def date_converter(field, value, context=None):
    if not isinstance(value, str):
        raise ValueDeserializationError(field, value, "Not a string")
    return datetime.datetime.strptime(value, "%Y-%m-%d").date()


@configure.value_deserializer(IObject)
def object_converter(field, value, context=None):
    if not isinstance(value, dict):
        raise ValueDeserializationError(field, value, "Not an object")
    result = {}
    for key, val in value.items():
        if key in field.schema:
            f = field.schema[key]
            if val is not None:
                result[key] = _optimized_lookup(val, f, context)
            else:
                result[key] = None
    return result


@configure.value_deserializer(IUnionField)
def union_converter(field, value, context=None):
    for f in field.fields:
        try:
            val = schema_compatible(value, f)
            if f.__implemented__(IObject) and value and not val:
                continue  # IObject doesn't match
            return val
        except Exception:
            pass
    raise ValueDeserializationError(field, value, "Doesn't match any field")

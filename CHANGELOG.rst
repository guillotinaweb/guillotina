CHANGELOG
=========

7.x (unreleased)
----------------

- Remove Cockroach support


6.0.9 (unreleased)
------------------

- Add id checker for move


6.0.8 (2020-09-24)
------------------

- mailer: import 'aiosmtplib' and 'html2text' lazily
  [masipcat]

- Cleanup travis logic from test fixtures [lferran]

- settings: always convert 'pool_size' to int
  [masipcat]


6.0.7 (2020-09-09)
------------------

- Add IFileNameGenerator adapter
  [qiwn]


6.0.6 (2020-08-25)
------------------

- Pass 'server_settings' in 'connection_options' to asyncpg pool
  [masipcat]


6.0.5 (2020-08-11)
------------------

- Fix register schema
  [bloodbare]

- Fix async test without pytest mark
  [masipcat]

6.0.4 (2020-07-29)
------------------

- fix release


6.0.3 (2020-07-29)
------------------

- Cookiecutter: fix test_install.py
  [masipcat]

- test deps: unpin pytest-asyncio
  [masipcat]

- doc: fix md headers (h1 -> h2) and other small fixes
  [masipcat]

- doc: fix example app
  [masipcat]

- Fix sphinx-build
  [masipcat]

- Make sure it does not fail on empty field
  [bloodbare]

6.0.2 (2020-07-10)
------------------

- Set load_catalog=true in test settings
  [masipcat]


6.0.1 (2020-07-09)
------------------

- Also allow JWT sub claim for loginid
  [allusa]


6.0.0 (2020-06-17)
------------------

- Nothing changed yet.


6.0.0b6 (2020-06-17)
--------------------

- Undo datetime object renderization on
  guillotina_json_default. [lferran]

- Be able to define optional requestBody [lferran]

- Fix registry update, when type provided mismatch with the one specified
  by the schema return an error HTTP status code instead of throwing an
  exception.
  [pfreixes]


6.0.0b5 (2020-06-08)
--------------------

- Few fixes & improvements: [lferran]
  - Fix JSONField validation error
  - Add unit tests for middleware generate error response
  - Add path_qs to Request object
  - Add content_length to Request object
  - Fix datetime objects renderization

- Optimize json schema ref resolution to not make so copies of all json schema definition
  for every validator instance
  [vangheem]

- Fix json schema ref resolution for nested objects
  [vangheem]

- Catalog subscribers conditional loading
  [bloodbre]

- Allow arbitrary path parameter within the path parameters
  [dmanchon]


6.0.0b4 (2020-05-23)
--------------------

- Allow to delete elements with the same id at cockroach
  [bloodbare]

- Split blob and objects initialization statements
  [bloodbare]

- Allow to ovewrite object table name and blob table name
  [bloodbare]

- Bug fix: handle raw strings in json payload [lferran]

- swagger tags fixes [ableeb]

- Move from travis to github actions [lferran]


6.0.0b3 (2020-04-24)
--------------------

- Provide patch operations for json field
  [vangheem]

- Optimize extend operation for bucket list field
  [vangheem]

- `.` and `..` should be blocked as valid ids. The browser will auto translate them
  to what current dir and parent dir respectively which gives unexpected results.
  [vangheem]

- Change in ISecurityPolicy that might improve performance during traversal for views
  with permission guillotina.Public
  [masipcat]

- Fix Response object responding with 'default_content' when 'content' evaluates to False
  [masipcat]

- Change log level for conflict errors to warning and fix locating tid of conflict error
  [vangheem]

- Fix security policy not taking into account IInheritPermissionMap for principals
  [masipcat,bloodbare]


- Fix use of int32 sql interpolation when it should have been bigint for tid
  [vangheem]

- Restore task vars after usage of Content API
- Zope.interface 5.0.1 upgrade
  [bloodbare]


6.0.0b2 (2020-03-25)
--------------------

- Fix move(obj) fires IBeforeObjectMovedEvent after modifying the object
  [masipcat]

- Error handling: ValueDeserializationError editing registry value
  [vangheem]

- Handle db transaction closed while acquiring transaction lock
  [vangheem]

- Handle db transaction closed while acquiring lock
  [vangheem]

- Handle connection errors on file head requests
  [vangheem]

- Update README
  [psanlorenzo]


6.0.0b1 (2020-03-18)
--------------------

- Use orjson instead of json/ujson
  [masipcat]

- AsgiStreamReader.read() can return bytes or bytearray
  [masipcat]


6.0.0a16 (2020-03-12)
---------------------

- Changes in ICatalogUtility, DefaultSearchUtility and @search endpoints
  [masipcat]

- Update react-gmi v 0.4.0
  [jordic]

- Fix more antipatterns [lferran]

- Fix integer query param validation [lferran]


6.0.0a15 (2020-03-02)
---------------------

- Handle http.disconnect (and other types of messages) while reading the request body
  [masipcat]

- Be able to have async schema invariants
  [vangheem]

- Provide better validation for json schema field
  [vangheem]


6.0.0a14 (2020-02-26)
---------------------

- Change AttributeError to HTTPPreconditionFailed in FileManager
  [masipcat]

- Reverted "Replaced Response.content_{type,length} with Response.set_content_{type,length}".
  Using setter to avoid breaking `Response.content_{type,length} = ...`
  [masipcat]

- Handle error when "None" value provided for behavior data
  [vangheem]

- Handle connection reset errors on file download
  [vangheem]


6.0.0a13 (2020-02-20)
---------------------

- Changed error handling logic: Guillotina (asgi app) catches all errors and returns a
  response for the ones that implements the handler IErrorResponseException. Otherwise
  raises the exception and is handled by ErrorsMiddleware
  [masipcat]

- Add "endpoint" in scope to let sentry know the view associated to the request
  [masipcat]

- Request.read() can return bytes or bytesarray
  [masipcat]

- Replaced Response.content_{type,length} with Response.set_content_{type,length}
  [masipcat]

- Breaking API change: Search GET
  Search get responds a json with items and items_total like plone rest api
  [bloodbare]

- Breaking Internal API change: Search
  Catalog utility search is the public search operation that is parsed and query
  the internal implementation
  [bloodbare]

- Fixing WS bugs and redis unsubscription
  [bloodbare]

- Add `max_ops` property to `PatchField`, `BucketListField` and `BucketDictField`
  [vangheem]

- Add clear action to list, dict and annotation patch fields
  [vangheem]


6.0.0a12 (2020-02-18)
---------------------

- Fix validation authorization in case token is expired
  [bloodbare]

- Set content type to response in renderers
  [masipcat]

- Import aiohttp only when recaptcha is configured
  [masipcat]

- Some asyncpg settings do not work with storages
  [vangheem]

- Improve performance of bucket dict field
  [vangheem]


6.0.0a11 (2020-02-09)
---------------------

- Moving validation endpoint from traversal to query param
  [bloodbare]

- Small improvement in asgi.py
- Call IIDGenerator with apply_coro
  [masipcat]


6.0.0a10 (2020-02-07)
---------------------

- Moved the ASGI logic from ASGIResponse and ASGISimpleResponse to class Response
  [masipcat]

- Add mail from on email validation
  [bloodbare]

- Validate POST @sharing payload too [lferran]

- Fix asyncpg integration with connection leaks on timeout
  [vangheem]


6.0.0a9 (2020-02-04)
--------------------

- Implemented endpoint @delete for IAttachments and IMultiAttachments
  [masipcat]

- Adding session manager support with redis backend
  [bloodbare]

- Registration workflow with generic validation package on contrib
  [bloodbare]

- Reset password workflow with generic validation package on contrib
  [bloodbare]

- Be able to customize pg db in test fixtures
  [vangheem]

- More type annotations
  [vangheem]

- Add pg db constraint for annotation data
  [vangheem]

- Fix DummyCache.set type signature to be the same as base class
  [vangheem]

- Jinja template engine to render on executors
  [bloodbare]

- Recaptcha support for public endpoints
  [bloodbare]

6.0.0a8 (2020-01-24)
--------------------

- Alpha version of @guillotinaweb/react-gmi available at /+manage
  [jordic]

- Improvements in contrib.dbusers
  [masipcat]

- Execute _clean_request() after middlewares execution
  [masipcat]

- Correctly bubble http errors for file downloads
  [vangheem]

- Fix command 'create'
  [masipcat]

- Remove unused methods in Response
  [masipcat]

- Add missing dependencies in `setup.py`
  [masipcat]


6.0.0a7 (2020-01-17)
--------------------

- Better error handling on redis connection issues
  [vangheem]

- Run _update_from_pytest_markers() after configuring db settings
  [masipcat]

- Fix validating array params in query parameters [lferran]

- Add open api tests and fix ones that do not pass tests
  [vangheem]

- Fix bug in traversal introduced when added support for asgi middlewares
  [masipcat]

- Fix value_deserializer() when field.key_type._type is None
  [masipcat]

- Fix automatic type conversion on nested fields. Fixes #832
  [vangheem]


6.0.0a6 (2020-01-13)
--------------------

- Fix bug on swagger with endpoints without explicit security declarations
  [jordic]

- Fix bug on pgcatalog when using it without a request
  [jordic]

- Be able to start database transaction before transaction has started it
  without causing errors
  [vangheem]

- More detailed information in ValidationErrors
  [masipcat]

- Provide way to configure content types as not globally addable
  [lferran]

- Fix Users and Groups to be addable only on manager folders [lferran]

- Fix optimized lookup to work with fields that do not have `_type`
  [vangheem]

- Prevent creating containers with empty id [lferran]

- Fix query param validation
  [vangheem]

- Optimize json deserialization
  [vangheem]


6.0.0a5 (2020-01-07)
--------------------

- Implemented 'ErrorsMiddleware' that catches all undhandled errors
  [masipcat]

- Small changes to the middleware logic
  [masipcat]

- Added `IIDChecker` adapter
  [vangheem]

- Schema fields default value for `required` is now `False`
  [vangheem]

- Denormalized group info when user is added to a group throught users endpoint (issue #806)
  [jordic]

- Add `Range` header support
  [vangheem]

- Be able to disable supporting range headers in `IFileManager.download`
  [vangheem]

- Fix validating None values in required fields
  [vangheem]

- Add localroles to @available-roles
  [jordic]

- Add `no-install-recommends` to Dockerfile (apt options)
  [svx]


6.0.0a4 (2019-12-23)
--------------------

- Improving ValidationErrors messages
  [masipcat]

- Fix error with requeued async queue tasks

- Added `valid_id_characters` app setting
  [vangheem]

- Better CancelledError handling in resolving a request
  [vangheem]

- Fix duplicate behaviors interfaces in get_all_behavior_interfaces()
  [qiwn]

- Fix adding duplicate behaviors
  [qiwn]


6.0.0a3 (2019-12-18)
--------------------

- Improved server command and added 'server_settings'
  [masipcat]

- Added property 'status' to Response
  [masipcat]


6.0.0a2 (2019-12-17)
--------------------

- Adapt to HTTP1.1 protocol on uvicorn by default
  [bloodbare]

- PatchField: added operation "multi"
  [masipcat]

- @duplicate: added option to reset acl

- Make pytest.mark.app_settings work in older pytest versions too [lferran]

- @move: destination id conflict should return 409 error, not 412
  [inaki]

- Explicit loop to execute on tests
  [bloodbare]

- Fix IAbsoluteUrl() returns request query
  [masipcat]

- Added attribute cookies to class Request()
  [masipcat]

- Added uvicorn as a guillotina requirement
  [masipcat]

- Added endpoint @available-roles on container
  [jordic]

- Add configurable expiration for jwt.tokens
  [jordic]


6.0.0a1 (2019-12-09)
--------------------

- Move tags to a context property to make it indexable on json
  [bloodbare]

- Added async property `Request.body_exists`
  [masipcat]

- Fixed fixture 'guillotina'
  [masipcat]

- Make sure that guillotina uses uvloop on starting if its installed
  [bloodbare]

- Make sure uvicorn uses the same loop as guillotina startup
  [bloodbare]

- Fix tests in 'test_cache_txn.py' and 'test_setup.py' being skipped
  [masipcat]

- Replaced aiohttp with ASGI (running with uvicorn by default)
  [dmanchon,masipcat,vangheem]

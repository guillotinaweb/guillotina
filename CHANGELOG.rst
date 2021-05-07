CHANGELOG
=========

6.3.5 (unreleased)
------------------

- Nothing changed yet.


6.3.4 (2021-05-06)
------------------

- Adding image with scale previews field
  [bloodbare]


6.3.3 (2021-05-04)
------------------

- Command: Implement graceful stop (like in asyncio.run())
  [masipcat]

- Command: Fix same txn copied to all tasks/requests
  [masipcat]


6.3.2 (2021-04-30)
------------------

- Command: fix typo introduced in #1125
  [masipcat]


6.3.1 (2021-04-30)
------------------

- On workflow change also trigger object modification
  [bloodbare]

- Command: run the startup/shutdown and main logic inside the loop
  [masipcat]


6.3.0 (2021-04-21)
------------------

- Use Context on default catalog security checks
  [bloodbare]

- Return 401 if NoPermissionToAdd is raised in defaultPOST
  [nilbacardit26]

- No longer have dedicated read connection and do not use any prepared statements
  [vangheem]


6.2.6 (2021-04-12)
------------------

- Fix bug on search results ids based on container path
  [bloodbare]


6.2.5 (2021-04-09)
------------------

- Fix PGCatalog Phrase search
  [bloodbare]

- Fix bug on empty waiting for empty tasks.
  [bloodbare]

6.2.4 (2021-04-07)
------------------

- Enable X-Wait header to wait futures. Use only in case you need to make sure all futures are finished before request ends.
  Alert: Afects performance on request response time.
  [bloodbare]

6.2.3 (2021-04-07)
------------------

- Search on pg catalog should check security on context
  [bloodbare]


6.2.2 (2021-04-01)
------------------

- Index on PG Catalog IDS should be table named
  [bloodbare]


6.2.1 (2021-03-12)
------------------

- Allow to skip pg catalog initialization based on SKIP_PGCATALOG_INIT environmental var.
  [bloodbare]


6.2.0 (2021-03-04)
------------------

- Write missing_value to object on deserialization
  [masipcat]

- BREAKING CHANGE: PG Catalog implementation splitted on multiple fields
  if you are import PGSearchUtility you need to change the import line from:
  `from guillotina.contrib.catalog.pg import PGSearchUtility` to `from guillotina.contrib.catalog.pg.utility import PGSearchUtility`
  [bloodbare]


6.1.7 (2021-03-03)
------------------

- ISecurityInfo: field 'id' was missing
  [masipcat]


6.1.6 (2021-02-25)
------------------

- Reuse modified objects on same transactions on traversal/async_get navigation
  [bloodbare]

- Improve memcached metrics probe [lferran]


6.1.5 (2021-02-09)
------------------

- Cleaner memcached_container pytest fixture [lferran]

- Fixing checking field permission on content creation
  [bloodbare]

- Fix memcached tests not able to start docker image [lferran]

- Fixing 6.1.4 release (anonymous users not working on search)
  [bloodbare]


6.1.4 (2021-01-31)
------------------

- Apply local roles on @search with pgcatalog
  [bloodbare]


6.1.3 (2021-01-18)
------------------

- Fix: patch a role on dbusers:groups don't remove users from them
  [jordic]

- Fix: patching password on a user hash it
  [jordic]

- Fix: only allow lowercase usernames on dbusers creation
  [jordic]

- Feat: db_users, being able to login by email
  [jordic]


6.1.2 (2021-01-18)
------------------

- Fix filter and sort by date field on pgcatalog
  [bloodbare]

- Add memcached support as cache driver
  [lferran]

- Fix: prevent caching large objects on fill_cache
  [lferran]

- Fix: dyncontent vocabularies json serialization
  [bloodbare]

- Fix: prevent caching large objects on fill_cache
  [lferran]

6.1.1 (2021-01-15)
------------------

- Support other languages on FTS at pgcatalog
  [bloodbare]

- DB Users storing group on DB due to pickling groups_cache leads to wrong objects
  [bloodbare]

- Improve markup (docs/index.md)
  [svx]

- Various documentation improvements
  [svx]

- Unify wording in dev docs
  [svx]


6.1.0 (2021-01-11)
------------------

- (Breaking change) Fixing TLS and STARTTLS
  At configuration starttls was used in case of tls: true. Its needed to change it to starttls: true
  Now you can configura tls with tls: true or starttls with starttls: true on the server configuration
  [bloodbare]

- Better exception on worflow
  [bloodbare]


6.0.26 (2021-01-10)
-------------------

- Bug on Tus Upload with dict fieldname, location is wrong on POST request
  [bloodbare]


6.0.25 (2021-01-09)
-------------------

- Adding config option for max result search value
  [bloodbare]


6.0.24 (2021-01-07)
-------------------

- (Breaking change) Fix download file name to query parameter so dictionary file field downloads with filename.
  API with filename on query path needs to change to filename query param
  [bloodbare]


6.0.23 (2021-01-05)
-------------------

- Dynamic content via config.yaml
  [bloodbare]

- Fix file not deleted in IMultiAttachments dict
  [masipcat]

- Keyword not pg catalog search and aggregation endpoint
  [bloodbare]


6.0.22 (2020-12-23)
-------------------

- Fixing addable-types, filtering not global addable types.
  [bloodbare]

- PyJwt > 2.0 breaks contract on decoding a JWT. Pinning to 1.6.0
  [bloodbare]


6.0.21 (2020-12-22)
-------------------

- Adding typing_extensions as dependency
  [bloodbare]


6.0.20 (2020-12-17)
-------------------

- Update uvicorn to 0.13.1
  [bloodbare]

- Adding widget field on json schema
  [bloodbare]

- Update orjson to 3.x
  [waghanza]


6.0.19 (2020-12-15)
-------------------

- Update gmi
  [jordic]

- Search by text by rank if its on search paramaters otherwise by alpha order
  [bloodbare]


6.0.18 (2020-12-05)
-------------------

- doc: training: fix websockets in G6
  [masipcat]

- doc: training: revert a change in api.md
  [masipcat]

- Fix watch/watch_lock when prometheus is not installed
  [masipcat]


6.0.17 (2020-12-04)
-------------------

- Adding timezone on email validation link expiration
  [bloodbare]

- Adding metadata endpoint to inspect query parameters for the search endpoint
  [bloodbare]

- Adding workflow/email_validation/vocabularies documentation
  [bloodbare]

- Bytes serializer
  [bloodbare]

- doc: improve training
  [masipcat]

- Record metrics on cache hit/misses
  [vangheem]

- Record metrics on time waiting for pg locks
  [vangheem]

- Record redis cache misses
  [vangheem]

- Add metrics to pg and redis operations
  [vangheem]


6.0.16 (2020-11-27)
-------------------
- Fixing workflow exception if not defined
  [bloodbare]

- Allow to define date format for recovery password
  [bloodbare]

- Abort transaction if tpc_commit() crashes
  [masipcat]


6.0.15 (2020-11-25)
-------------------

- Fix not defined workflow exception
  [bloodbare]


6.0.14 (2020-11-25)
-------------------

- Fix reset password flow to be equal to register
  [bloodbare]


6.0.13 (2020-11-23)
-------------------

- Allowing to define Owner roles users on creation
  [bloodbare]


6.0.12 (2020-11-15)
-------------------

- Fixing workflow subscriber for state history
  [bloodbare]

- Allow to search on basic workflow state publish
  [bloodbare]


6.0.11 (2020-11-08)
-------------------

- Adding Vocabularies API compatible to Plone REST API
  [bloodbare]

- Adding Workflow contrib package with API compatible to Plone REST API
  [bloodbare]

- Adding languages and contrib vocabulary
  [bloodbare]

- Avoid default value check on get for each get operation
  [bloodbare]

- Adding post serialize mechanism to modify JSON responses based on packages
  [bloodbare]

6.0.10 (2020-11-01)
-------------------

- Fix conflict cors response.
  [bloodbare]


6.0.9 (2020-10-30)
------------------

- Change transaction strategy 'simple'
  [masipcat]

- Fix bug on error deserialization

- Fix transaction context manager doesn't abort the txn when a exception is raised
  [masipcat]

- Add id checker for move
  [qiwn]


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

- Use pendulum's parser to deserialize datetime values (if it's installed).
  Otherwise use current one. [masipcat]

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

# Guillotina: The Python AsyncIO REST API Framework

Guillotina is the only full-featured Python AsyncIO REST Resource Application
Server designed for high-performance, horizontally scaling solutions.

## Quick Start

Install Guillotina:

```shell
pip install guillotina
g serve --port=8080
```

Then use curl, [Postman](https://www.postman.com/ "Link to Postman") or build something with it::

```shell
curl -XPOST --user root:root http://localhost:8080/db -d '{
  "@type": "Container",
  "id": "container"
}'
curl --user root:root http://localhost:8080/db/container
```

## Why Guillotina

 - **Performance**: Traditional Python web servers limit the number of simultaneous
   requests to the number of threads running the server. With AsyncIO, you are
   able to serve many more simultaneous requests.
 - **Front-end friendly**: Guillotina is designed to make your
   JavaScript engineers happy. With things like automatic Swagger documentation
   for endpoints, out of the box CORS and websockets, your front-end team will be happy
   to work with Guillotina. We speak JSON but can adapt to any content type
   payload request/response bodies.
 - **AsyncIO**: With AsyncIO, websockets are simple. More interestingly, AsyncIO
   is an ideal match with microservice architectures.
 - **Object model**: Guillotina uses a hierarchial object model. This hierarchy
   of objects then maps to URLs and is perfect for managing
   a large number of objects.
 - **Security**: Guillotina has a granular, hierarchical, multidimensional
   security system that allows you to manage the security of your content
   at a level not available to other frameworks.
 - **Scale**: With integrations like Redis, ElasticSearch, you
   have the tools to scale.

## Getting started

Are you new to Guillotina? This is the place to start!

The [quick tour](./quick-tour.html) gives an overview of the major features in Guillotina.

Need help? Join our [Gitter channel](https://gitter.im/plone/guillotina).

## Build a Guillotina app

You can even run Guillotina as a single page app if you so desire.

Here is an example with content type and service::

```python
from guillotina import configure
from guillotina import content
from guillotina import schema
from guillotina.factory import make_app
from zope import interface

import uvicorn


class IMyType(interface.Interface):
    foobar = schema.TextLine()


@configure.contenttype(
    type_name="MyType",
    schema=IMyType,
    behaviors=["guillotina.behaviors.dublincore.IDublinCore"],
)
class MyType(content.Resource):
    pass


@configure.service(
    context=IMyType,
    method="GET",
    permission="guillotina.ViewContent",
    name="@foobar",
)
async def foobar_service(context, request):
    return {"foobar": context.foobar}


if __name__ == "__main__":
    app = make_app(
        settings={
            "applications": ["__main__"],
            "root_user": {"password": "root"},
            "databases": {
                "db": {"storage": "DUMMY_FILE", "filename": "dummy_file.db",}
            },
            "port": 8080,
        }
    )
    uvicorn.run(app, host="localhost", port=8080)
```


## Training / Tutorial

Learn how to use Guillotina by following the [training](./training/index.html "Link to Guillotina trining docs").

```eval_rst
.. toctree::
   :maxdepth: 2

   training/index
```

## REST API

After you're up and running, primarily, Guillotina provides a REST API to work with
and it is what you should become the most familiar with.

Guillotina API structure mirrors the object tree structure. Within the object
tree structure, there are four major types of objects you'll want to be familiar
with:

- Application: The root of the tree: `/`
- Database: A configured database: `/(db)`
- Container: An main object to add data to: `/(db)/(container)`
- Content: Item or Folder by default. This is your dynamic object tree you create

The endpoints available around these objects are detailed below:

```eval_rst
.. toctree::
   :maxdepth: 1
   :glob:

   rest/application
   rest/db
   rest/container
   rest/item
   rest/folder
```

## Developer Documentation

After reading quick tour or training section,
Now you can start hands-on style guide to learn how to use it.

```eval_rst
.. toctree::
   :maxdepth: 2

   developer/narrative
   developer/security
   developer/roles
   developer/applications
   developer/addons
   developer/services
   developer/render
   developer/contenttypes
   developer/behavior
   developer/interfaces
   developer/events
   developer/commands
   developer/applicationconfiguration
   developer/design
   developer/persistence
   developer/blob
   developer/router
   developer/exceptions
   developer/fields
   developer/serialize
   developer/async_utils
   developer/component-architecture
   developer/debugging
```


## Deploying

- [Installing Guillotina](./installation/installation.html)
  is done with pip but if you need to run with docker,
  [we also have you covered](https://hub.docker.com/r/guillotina/guillotina/).
- Guillotina has an quite a few
  [configuration options](./installation/configuration.html)
  you might be curious about.
- You can also setup
  [logging configuration](./installation/logging.html).
- Finally, you may also need to put Guillotina
  [behind a proxy](./installation/production.html)
  when you deploy it.


## References

```eval_rst
.. toctree::
   :maxdepth: 2

   api/index
```

```eval_rst
.. toctree::
   :maxdepth: 2

   migration/index
```

```eval_rst
.. toctree::
   :maxdepth: 2

   installation/index
```

```eval_rst
.. toctree::
   :maxdepth: 2

   contrib/index
```

## About

- [Read about](./about.html) the rich history of the project

```eval_rst
.. toctree::
   :hidden:
   :glob:

   developer/*
   installation/*
   training/*
   *
```

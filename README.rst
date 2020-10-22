Introduction
============

.. image:: https://img.shields.io/badge/docs-latest-brightgreen.svg?style=flat
   :target: http://guillotina.readthedocs.io/en/latest/

.. image:: https://travis-ci.org/plone/guillotina.svg?branch=master
   :target: https://travis-ci.org/plone/guillotina

.. image:: https://codecov.io/gh/plone/guillotina/branch/master/graph/badge.svg
   :target: https://codecov.io/gh/plone/guillotina/branch/master
   :alt: Test Coverage

.. image:: https://img.shields.io/pypi/pyversions/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina/
   :alt: Python Versions

.. image:: https://img.shields.io/pypi/v/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina

.. image:: https://img.shields.io/pypi/l/guillotina.svg
   :target: https://pypi.python.org/pypi/guillotina/
   :alt: License

.. image:: https://badges.gitter.im/plone/guillotina.png
   :target: https://gitter.im/plone/guillotina
   :alt: Chat

.. image:: https://img.shields.io/docker/cloud/build/plone/guillotina
   :target: https://hub.docker.com/r/guillotina/guillotina
   :alt: Docker Cloud Build Status

Please `read the detailed docs <http://guillotina.readthedocs.io/en/latest/>`_


This is the working project of the next generation Guillotina server based on asyncio.


Dependencies
------------

* Python >= 3.7
* PostgreSQL >= 9.6


Quickstart
----------

We use pip

.. code-block:: shell

    pip install guillotina


Run PostgreSQL
--------------

If you don't have a PostgreSQL server to play with, you can run one with Docker.

Download and start the Docker container by running

.. code-block:: shell

    make run-postgres



Run the server
--------------

To run the server

.. code-block:: shell

    g


Then...

.. code-block:: shell

    curl http://localhost:8080


Or, better yet, use `Postman <https://www.getpostman.com/>`_ to start playing with API.

You can also navigate in your Guillotina server with its built-in web admin interface by visiting http://localhost:8080/+admin/.

Deploy on Heroku
----------------

Read more `Guillotina-Heroku <https://github.com/guillotinaweb/guillotina-heroku>`_.

.. image:: https://www.herokucdn.com/deploy/button.svg
   :target: https://www.heroku.com/deploy?template=https://github.com/guillotinaweb/guillotina-heroku

Getting started with development
--------------------------------

Using pip (requires Python > 3.7)

.. code-block:: shell

    git clone git@github.com:plone/guillotina.git
    cd guillotina
    python3.7 -m venv .
    ./bin/pip install -r requirements.txt
    ./bin/pip install -r contrib-requirements.txt
    ./bin/pip install -e '.[test]'
    ./bin/pre-commit install


Run tests
---------

We're using `pytest <https://docs.pytest.org/en/latest/>`_

.. code-block:: shell

    ./bin/pytest guillotina

and for test coverage

.. code-block:: shell

    ./bin/pytest --cov=guillotina guillotina/

With file watcher...

.. code-block:: shell

    ./bin/ptw guillotina --runner=./bin/py.test


Default
-------

Default root access can be done with AUTHORIZATION header : Basic root:root


Docker
------

You can also run Guillotina with Docker!


First, run PostgreSQL

.. code-block:: shell

    docker run --rm \
        -e POSTGRES_DB=guillotina \
        -e POSTGRES_USER=guillotina \
        -p 127.0.0.1:5432:5432 \
        --name postgres \
        postgres:9.6

Then, run Guillotina

.. code-block:: shell

    docker run --rm -it \
        --link=postgres -p 127.0.0.1:8080:8080 \
        plone/guillotina:latest \
        g -c '{"databases": [{"db": {"storage": "postgresql", "dsn": "postgres://guillotina:@postgres/guillotina"}}], "root_user": {"password": "root"}}'


This assumes you have a config.yaml in your current working directory


Chat
----

Join us to talk about Guillotina at https://gitter.im/plone/guillotina

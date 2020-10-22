from pytest_docker_fixtures import images


images.configure("postgresql", version="10.9")


pytest_plugins = ["guillotina.tests.fixtures"]

from guillotina import configure


app_settings = {}


def includeme(root, settings):
    configure.scan("guillotina.contrib.image.install")
    configure.scan("guillotina.contrib.image.api")
    configure.scan("guillotina.contrib.image.behaviors")

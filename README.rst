collective.zamqpdemo
====================

This package contains a few examples of
configuring and using AMQP-messaging with Plone and
`collective.zamqp <http://github.com/datakurre/collective.zamqp/>`_
(with or without ZEO-clustering).

After running the buildout, you must start RabbitMQ by ::

    $ source bin/rabbitmq-env
    $ bin/rabbitmq-server

and only then your Plone::

    $ bin/instance fg

RabbitMQ is initialized automatically for the demos using
``./etc/rabbit.config`` found within the buildout.

You can follow the rabbit with login username *amqpdemo* and password
*amqpdemo* at::

    http://localhost:55672/mgmt/

If you'd like to hack with the examples, you should also try the built-in
`sauna.reload <http://pypi.python.org/pypi/sauna.reload/>`_-support
of *collective.zamqp* with::

    $ RELOAD_PATH=src bin/instance fg

This initialize the AMQP-connections only after reload and eases hacking with
AMQP message consumers and producers.

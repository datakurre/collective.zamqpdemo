collective.zamqpdemo
====================

This package contains a few examples of
configuring and using AMQP-messaging with Plone and
`collective.zamqp <http://github.com/datakurre/collective.zamqp/>`_
(with or without ZEO-clustering).

After running the buildout, you must start RabbitMQ by::

    $ source bin/rabbitmq-env
    $ bin/rabbitmq-server

and only then your Plone::

    $ bin/instance fg

You can follow the rabbit with login username *amqpdemo* and password
*amqpdemo* at::

    http://localhost:55672/mgmt/

If you'd like to hack with the examples, you should also try the built-in
`sauna.reload <http://pypi.python.org/pypi/sauna.reload/>`_-support
of *collective.zamqp* with::

    $ RELOAD_PATH=src bin/instance fg

This initialize the AMQP-connections only after reload and eases hacking with
AMQP message consumers and producers.

**Note:**
If you have tried these demos before and have not cleared your buildout,
you might have to reset RabbitMQ by removing *./var/rabbitmq*. That's
because the demos have been simplified to use AMQP default virtualhost,
credentials and exchanges.

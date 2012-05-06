collective.zamqpdemo
====================

This package contains a few examples of
configuring and using AMQP-messaging with Plone and
`collective.zamqp <http://github.com/datakure/collective.zamqp/>`_
(with and without ZEO-clustering).

After running the buildout, you must start RabbitMQ::

    source bin/rabbitmq-env
    bin/rabbitmq-server

and configure it properly for the demos::

    source bin/rabbitmq-env
    bin/rabbitmqctl add_vhost /amqpdemo
    bin/rabbitmqctl add_user amqpdemo amqpdemo
    bin/rabbitmqctl set_permissions -p /amqpdemo amqpdemo "^collective\.zamqp.*|^amqpdemo.*" ".*" ".*"

If you'd like to hack with the examples, you should also try the built-in
`sauna.reload <http://pypi.python.org/pypi/sauna.reload/>`_-support
of *collective.zamqp* with::

    RELOAD_PATH=src bin/instance fg

This should initialize AMQP-connections only after the reload
and ease hacking with consumers and producers.

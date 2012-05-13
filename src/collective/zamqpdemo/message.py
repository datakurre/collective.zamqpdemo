# -*- coding: utf-8 -*-
"""Tests messaging with basic_get"""

from five import grok

from zope import schema
from zope.interface import Interface
from zope.component import getUtility, queryUtility

from z3c.form import button
from plone.directives import form

from Products.CMFCore.interfaces import ISiteRoot
from Products.statusmessages.interfaces import IStatusMessage

from collective.zamqp.interfaces import IProducer, IConsumer
from collective.zamqp.interfaces import IMessageArrivedEvent
from collective.zamqp.producer import Producer
from collective.zamqp.consumer import Consumer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")

import logging
logger = logging.getLogger("collective.zamqpdemo")


class IPurge(Interface):
    """Purge command marker interface"""


class IMessage(Interface):
    """Message marker interface"""


class QueueMessageProducer(Producer):
    """Produces queue message command"""
    grok.name("amqpdemo.queue")

    connection_id = "amqpdemo"
    exchange = "amqpdemo"
    serializer = "text/plain"

    auto_declare = True
    durable = False

    @property
    def routing_key(self):
        site = queryUtility(ISiteRoot)
        if site:
            return "amqpdemo.%s.queue" % site.getId()
        else:
            return "amqpdemo.queue"


class PurgeQueueProducer(Producer):
    """Produces purge queue command"""
    grok.name("amqpdemo.purge")

    connection_id = "amqpdemo"
    exchange = "amqpdemo"
    serializer = "text/plain"

    auto_declare = True
    durable = False

    @property
    def routing_key(self):
        site = queryUtility(ISiteRoot)
        if site:
            return "amqpdemo.%s.purge" % site.getId()
        else:
            return "amqpdemo.purge"


class PurgeQueueConsumer(Consumer):
    """Consumes purge-requests"""
    grok.name("amqpdemo.${site_id}.purge")  # is also the queue name

    connection_id = "amqpdemo"
    exchange = "amqpdemo"

    auto_declare = True
    durable = False

    marker = IPurge


class MessageConsumer(Consumer):
    """Consumes purge-requests"""
    grok.name("amqpdemo.${site_id}.queue")  # is also the queue name

    connection_id = "amqpdemo"
    exchange = "amqpdemo"

    auto_declare = True
    durable = False

    marker = IMessage

    def on_ready_to_consume(self):
        pass  # overrided to disable auto-consuming


class IQueueForm(form.Schema):
    """Status form schema"""

    message = schema.Text(
        title=_(u"Message")
        )


class MessageForm(form.SchemaForm):
    """Message form"""
    grok.name("queue-message")
    grok.context(Interface)

    schema = IQueueForm
    ignoreContext = True

    label = _(u"Queue Message")
    description = _(u"Tests 'basic.get'.")

    def update(self):
        self.request.set("disable_border", True)
        super(MessageForm, self).update()

    @button.buttonAndHandler(_(u"Send"))
    def queueMessage(self, action):
        data, errors = self.extractData()

        producer = getUtility(IProducer, name="amqpdemo.queue")
        producer._register()  # register for transaction
        producer.publish(data["message"])

        IStatusMessage(self.request).addStatusMessage(
                       u"Queued: %s" % data["message"],
                       "info")


class PurgeView(grok.View):
    """Purge queue view"""
    grok.name("purge-queue")
    grok.context(Interface)

    def update(self):
        producer = getUtility(IProducer, name="amqpdemo.purge")
        producer._register()  # register for transaction
        producer.publish(u"")  # empty message :)

        IStatusMessage(self.request).addStatusMessage(
                       u"Purge requested",
                       "info")

        self.request.response.redirect(self.context.absolute_url())

    def render(self):
        return u""


@grok.subscribe(IPurge, IMessageArrivedEvent)
def purgeQueue(message, event):
    site = getUtility(ISiteRoot)

    logger.info("Starting to purge amqpdemo.%s.queue" % site.getId())

    consumer = getUtility(
        IConsumer, name="amqpdemo.%s.queue" % site.getId())
    # basic_get sets its response callback in a way that is NOT
    # thread-safe; therefore basic_get is safe to be used only via
    # a ConsumingServer in a single-threaded ZEO client
    consumer._channel.basic_get(
        consumer.on_message_received,
        queue=consumer.queue)

    message.ack()


@grok.subscribe(IMessage, IMessageArrivedEvent)
def logMessage(message, event):
    logger.info("Purged: %s" % message.body)

    site = getUtility(ISiteRoot)

    count = message.method_frame.message_count
    if count:
        logger.info("Messages left: %s", count)

        consumer = getUtility(
            IConsumer, name="amqpdemo.%s.queue" % site.getId())
        # basic_get sets its response callback in a way that is NOT
        # thread-safe; therefore basic_get is safe to be used only via
        # a ConsumingServer in a single-threaded ZEO client
        consumer._channel.basic_get(
            consumer.on_message_received,
            queue=consumer.queue)

    message.ack()

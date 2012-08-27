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
from collective.zamqp.connection import BlockingChannel

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")

import logging
logger = logging.getLogger("collective.zamqpdemo")


class IMessage(Interface):
    """Message marker interface"""


class QueueMessageProducer(Producer):
    """Produces queue message command"""
    grok.name("amqpdemo.messages")

    connection_id = "superuser"
    exchange = "awaiting"
    serializer = "plain"

    auto_delete = False
    durable = False

    @property
    def routing_key(self):
        site = queryUtility(ISiteRoot)
        if site:
            return "amqpdemo.%s.messages" % site.getId()
        else:
            return "amqpdemo.${site}.messages"


class AwaitingMessages(Consumer):
    """Consumes purge-requests"""
    grok.name("amqpdemo.${site_id}.awaiting")  # is also the queue name

    connection_id = "superuser"
    exchange = "awaiting"
    queue_arguments = {
        "x-dead-letter-exchange": "messages",  # redirect messages with reject
    }
    routing_key = "amqpdemo.${site_id}.messages"
    marker = IMessage

    auto_delete = False
    durable = False

    def on_ready_to_consume(self):
        pass  # overrided to disable auto-consuming
              # we need this consumer to declare a site-specific queue


class MessageConsumer(Consumer):
    """Consumes purge-requests"""
    grok.name("amqpdemo.${site_id}.messages")  # is also the queue name

    connection_id = "superuser"
    exchange = "messages"
    queue = ""  # use generated queue name
    routing_key = "amqpdemo.${site_id}.messages"
    marker = IMessage

    durable = False


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

        producer = getUtility(IProducer, name="amqpdemo.messages")
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
        site = getUtility(ISiteRoot)
        queue = "amqpdemo.%s.awaiting" % site.getId()
        messages = len(getUtility(IConsumer, name=queue))
        if messages:
            with BlockingChannel("demo") as channel:
                method, properties, body = channel.basic_get(queue=queue)
                if properties and body:  # quick test for Basic.GetOk
                    channel.basic_reject(delivery_tag=method.delivery_tag,
                                         requeue=False)

        IStatusMessage(self.request).addStatusMessage(
                       u"Purge requested",
                       "info")

        self.request.response.redirect(self.context.absolute_url())

    def render(self):
        return u""


@grok.subscribe(IMessage, IMessageArrivedEvent)
def logMessage(message, event):
    logger.info("Purged: %s" % message.body)

    site = getUtility(ISiteRoot)
    queue = "amqpdemo.%s.awaiting" % site.getId()
    messages = len(getUtility(IConsumer, name=queue))
    logger.info("Messages left: %s", messages)
    if messages:
        with BlockingChannel("demo") as channel:
            method, properties, body = channel.basic_get(queue=queue)
            if properties and body:  # quick test for Basic.GetOk
                channel.basic_reject(delivery_tag=method.delivery_tag,
                                     requeue=False)
    message.ack()

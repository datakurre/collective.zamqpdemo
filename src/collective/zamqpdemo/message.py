# -*- coding: utf-8 -*-
"""Test messages with basic_get"""

from five import grok

from zope import schema
from zope.interface import Interface
from zope.component import getUtility

from z3c.form import button
from plone.directives import form

from Products.CMFCore.interfaces import ISiteRoot

from collective.zamqp.interfaces import IProducer, IConsumer
from collective.zamqp.interfaces import IMessageArrivedEvent
from collective.zamqp.producer import Producer
from collective.zamqp.consumer import Consumer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")

import logging
logger = logging.getLogger("collective.zamqpdemo")


class IMessage(Interface):
    """Message marker interface"""


class MessageProducer(Producer):
    """Produces message"""
    grok.name("amqpdemo.message")  # is also a routing key

    connection_id = "amqpdemo"
    exchange = "amqpdemo"
    serializer = "text/plain"

    auto_declare = True
    durable = False


class MessageConsumer(Consumer):
    """Consumes messages"""
    grok.name("amqpdemo.${site_id}.message")  # is also the queue name

    connection_id = "amqpdemo"
    exchange = "amqpdemo"
    routing_key = "amqpdemo.message"

    auto_declare = True
    durable = False

    marker = IMessage

    def on_ready_to_consume(self):
        pass  # disable auto-consuming


class IMessageForm(form.Schema):
    """Status form schema"""

    message = schema.Text(
        title=_(u"Message")
        )


class MessageForm(form.SchemaForm):
    """Message form"""
    grok.name("queue-message")
    grok.context(Interface)

    schema = IMessageForm
    ignoreContext = True

    label = _(u"Queue Message")
    description = _(u"Tests 'basic.get'.")

    def update(self):
        self.request.set("disable_border", True)
        super(MessageForm, self).update()

    @button.buttonAndHandler(_(u"Send"))
    def queueMessage(self, action):
        data, errors = self.extractData()
        site = getUtility(ISiteRoot)

        producer = getUtility(IProducer, name="amqpdemo.message")
        producer.publish(data["message"])
        producer.publish(data["message"])  # publish twice to increment count

        consumer = getUtility(
            IConsumer, name="amqpdemo.%s.message" % site.getId())
        consumer._channel.basic_get(
            consumer.on_message_received,
            queue=consumer.queue)


@grok.subscribe(IMessage, IMessageArrivedEvent)
def handleMessage(message, event):
    logger.info(message.body)
    logger.info("Messages left: %s", message.method_frame.message_count)
    message.ack()

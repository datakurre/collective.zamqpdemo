# -*- coding: utf-8 -*-
"""Content generation and deletion"""

import uuid
import random

from Acquisition import aq_parent

from five import grok

from zope.interface import Interface
from zope.component import getUtility

from plone.directives import form
from plone.uuid.interfaces import IUUID
from plone.app.uuid.utils import uuidToObject

from plone.app.layout.globals.interfaces import IViewView
from plone.app.layout.viewlets.interfaces import IAboveContentTitle

from plone.dexterity.utils import createContentInContainer

from collective.zamqp.interfaces import IProducer, IMessageArrivedEvent
from collective.zamqp.producer import Producer
from collective.zamqp.consumer import Consumer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")


class IContainer(form.Schema):
    """Dummy container"""


class IItem(form.Schema):
    """Dummy item"""


class ICreateItemMessage(Interface):
    """Marker interface for item creation message"""


class IDeleteItemMessage(Interface):
    """Marker interface for item deletion message"""


class CreateItemProducer(Producer):
    """Produces item creation requests"""
    grok.name("amqpdemo.create")  # is also the routing key

    connection_id = "demo"
    serializer = "msgpack"
    queue = "amqpdemo.create"

    durable = False


class DeleteItemProducer(Producer):
    """Produces item deletion requests"""
    grok.name("amqpdemo.delete")  # is also the routing key

    connection_id = "demo"
    serializer = "msgpack"
    queue = "amqpdemo.delete"

    durable = False


class CreateItemConsumer(Consumer):
    """Consumes item creation messages"""
    grok.name("amqpdemo.create")  # is also the queue name

    connection_id = "demo"
    marker = ICreateItemMessage

    durable = False


class DeleteItemConsumer(Consumer):
    """Consumes item deletion messages"""
    grok.name("amqpdemo.delete")  # is also the queue name

    connection_id = "demo"
    marker = IDeleteItemMessage

    durable = False


class CreateAndDeleteViewlet(grok.Viewlet):
    grok.context(IContainer)
    grok.viewletmanager(IAboveContentTitle)
    grok.view(IViewView)


class CreateAndDelete(grok.View):
    """Item creation request view"""
    grok.context(IContainer)
    grok.name("create-and-delete")

    def render(self):
        producer = getUtility(IProducer, name="amqpdemo.create")
        producer._register()

        title = str(uuid.uuid4())
        kwargs = {"title": title}

        producer.publish(kwargs, correlation_id=IUUID(self.context))

        self.request.response.redirect(self.context.absolute_url())


class CreateManyAndDelete(grok.View):
    """Item creation request view"""
    grok.context(IContainer)
    grok.name("create-many-and-delete")

    def render(self):
        producer = getUtility(IProducer, name="amqpdemo.create")
        producer._register()

        title = str(uuid.uuid4())

        for i in range(5):
            kwargs = {"title": "%s-%s" % (title, i + 1)}
            producer.publish(kwargs, correlation_id=IUUID(self.context))

        self.request.response.redirect(self.context.absolute_url())


class CreateRandomAndDelete(grok.View):
    """Item creation request view"""
    grok.context(IContainer)
    grok.name("create-random-and-delete")

    def render(self):
        producer = getUtility(IProducer, name="amqpdemo.create")
        producer._register()

        title = str(uuid.uuid4())

        for i in range(random.randint(1, 5)):
            kwargs = {"title": "%s-%s" % (title, i + 1)}
            producer.publish(kwargs, correlation_id=IUUID(self.context))

        self.request.response.redirect(self.context.absolute_url())


@grok.subscribe(ICreateItemMessage, IMessageArrivedEvent)
def createItem(message, event):
    """Consume item creation message"""

    uuid = message.header_frame.correlation_id
    container = uuidToObject(uuid)

    obj = createContentInContainer(container, "collective.zamqpdemo.item",
                                   checkConstraints=True, **message.body)
    kwargs = {"uuid": IUUID(obj)}

    producer = getUtility(IProducer, name="amqpdemo.delete")
    producer._register()
    producer.publish(kwargs)

    message.ack()


@grok.subscribe(IDeleteItemMessage, IMessageArrivedEvent)
def deleteItem(message, event):
    """Consume item deletion message"""

    uuid = message.body["uuid"]
    item = uuidToObject(uuid)

    container = aq_parent(item)
    container.manage_delObjects([item.id])

    message.ack()

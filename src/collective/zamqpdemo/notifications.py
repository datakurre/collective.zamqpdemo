# -*- coding: utf-8 -*-
"""Instant publishing notifications for all via web-stomp"""

from five import grok

from zope.interface import Interface
from zope.component import getUtility

from Products.CMFCore.interfaces import IActionSucceededEvent

from collective.zamqp.interfaces import IProducer
from collective.zamqp.producer import Producer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")


class NotificationProducer(Producer):
    """Produces instant notification on published documents"""
    grok.name("amqpdemo.notifications")

    connection_id = "demo"
    exchange = "amq.topic"
    routing_key = "notifications"
    serializer = "json"


@grok.subscribe(Interface, IActionSucceededEvent)
def workflowActionSucceeded(context, event):
    if getattr(event, "action") == "publish":
        notifications = getUtility(IProducer, name="amqpdemo.notifications")
        notifications.publish({
            "url": context.absolute_url(),
            "title": context.title_or_id()
        })

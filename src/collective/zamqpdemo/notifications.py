# -*- coding: utf-8 -*-
"""Instant publishing notifications for all via web-stomp"""

try:
    import json
    json  # pyflakes
except ImportError:
    import simplejson as json

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

    connection_id = "amqpdemo"
    exchange = "amqpdemo.notifications"
    exchange_type = "fanout"
    exchange_declare = True
    serializer = "text/plain"
    routing_key = "*"

    auto_declare = True
    durable = False


@grok.subscribe(Interface, IActionSucceededEvent)
def workflowActionSucceeded(context, event):
    if getattr(event, "action") == "publish":
        payload = {
            "url": context.absolute_url(),
            "title": context.title_or_id()
        }
        notifications = getUtility(IProducer, name="amqpdemo.notifications")
        notifications._register()
        notifications.publish(json.dumps(payload))

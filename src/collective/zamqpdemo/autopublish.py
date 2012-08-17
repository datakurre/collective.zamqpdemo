# -*- coding: utf-8 -*-
"""Auto-publishes content"""

import datetime

from Acquisition import aq_inner, aq_base
from ZODB.POSException import ConflictError

from five import grok

from zope.interface import Interface
from zope.component import getUtility

from plone.uuid.interfaces import IUUID
from plone.app.uuid.utils import uuidToObject

from Products.CMFCore.interfaces import IActionSucceededEvent
from Products.CMFCore.utils import getToolByName

from collective.zamqp.interfaces import IProducer, IMessageArrivedEvent
from collective.zamqp.producer import Producer
from collective.zamqp.consumer import Consumer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")

import logging
logger = logging.getLogger("collective.zamqpdemo")


class IAutoPublishMessage(Interface):
    """Marker interface for auto-publishing message"""


class AutoPublishProducer(Producer):
    """Produces auto-publishing requests"""
    grok.name("amqpdemo.autopublish")

    connection_id = "demo"
    serializer = "plain"

    queue = "amqpdemo.autopublish.wait"
    queue_arguments = {
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": "amqpdemo.autopublish",
        "x-message-ttl": 60000,  # 60s poll for autopublish
        }
    routing_key = "amqpdemo.autopublish.wait"

    durable = False


class AutoPublishConsumer(Consumer):
    """Consumes auto-publishing requests"""
    grok.name("amqpdemo.autopublish")  # is also the queue name

    connection_id = "demo"
    marker = IAutoPublishMessage

    durable = False


def publishOrWait(context):
    """Publishes the context if its publication date is in the past
    or produces an AMQP-message to try again later"""

    wftool = getToolByName(context, "portal_workflow")

    # Test the context state
    if wftool.getInfoFor(context, "review_state") != "auto_publishing":
        return  # not our state

    # Check the publication date
    obj = aq_inner(aq_base(context))
    if hasattr(obj, "getEffectiveDate"):
        date = obj.getEffectiveDate()
    elif hasattr(obj, "effective_date"):
        date = getattr(obj, "effective_date")
    else:
        date = datetime.now()
    if hasattr(date, "asdatetime"):
        date = date.asdatetime()

    # Publish immediately, if publication date is already in the past
    if date <= datetime.datetime.now(date.tzinfo):
        try:
            wftool.doActionFor(context, "publish", None, u"Scheduled publish.")
        except ConflictError:
            raise
        except Exception, e:
            logger.warning("Couldn't publish '%s' because of '%s", context, e)
        return

    # Get producer and publish the message to try later
    producer = getUtility(IProducer, name="amqpdemo.autopublish")
    producer._register()  # publish only after the transaction has succeeded
    producer.publish("", correlation_id=IUUID(context))  # empty message... :)


@grok.subscribe(Interface, IActionSucceededEvent)
def produceMessage(context, event):
    """Produce message"""

    # Check the succeeded action
    if event.action != "auto_publish":
        return  # not our transition

    publishOrWait(context)


@grok.subscribe(IAutoPublishMessage, IMessageArrivedEvent)
def consumeMessage(message, event):
    """Consume message"""

    uuid = message.header_frame.correlation_id
    context = uuidToObject(uuid)

    publishOrWait(context)

    message.ack()

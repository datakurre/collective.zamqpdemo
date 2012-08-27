# -*- coding: utf-8 -*-
"""Instant publishing notifications for all via web-stomp"""

from hashlib import md5

from five import grok

from zope.interface import Interface
from zope.component import getUtility

from plone.uuid.interfaces import IUUID

from Products.CMFCore.interfaces import ISiteRoot, IActionSucceededEvent
from Products.CMFCore.utils import getToolByName

from collective.zamqp.interfaces import IProducer
from collective.zamqp.producer import Producer
from collective.zamqp.connection import BlockingChannel

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")


class PublishedProducer(Producer):
    """Produces instant notification on published documents"""
    grok.name("amqpdemo.published")

    connection_id = "superuser"
    exchange = "amq.topic"
    routing_key = "published"
    serializer = "json"

    durable = False


class SubmittedProducer(Producer):
    """Produces instant notification on submitted documents"""
    grok.name("amqpdemo.submitted")

    connection_id = "superuser"
    exchange = "reviewers"
    exchange_topic = "topic"
    exchange_auto_delete = False
    routing_key = "submitted"
    serializer = "json"

    durable = False


class ConfigureMemberExchange(grok.View):
    grok.name("configure-member-exchange")
    grok.context(ISiteRoot)
    grok.require("zope2.View")

    def render(self):
        mtool = getToolByName(self.context, "portal_membership")

        # For unauthenticated users, return 'null'
        if mtool.isAnonymousUser():
            return u"null"

        member = mtool.getAuthenticatedMember()

        member_exchange = md5()
        member_exchange.update(self.request.cookies.get("__ac"))
        member_exchange = "member-%s" % member_exchange.hexdigest()

        can_review = \
            "Reviewer" in member.getRoles() or \
            "Manager" in member.getRoles()

        with BlockingChannel("superuser") as channel:
            ###
            # XXX: Pika 0.9.5 doesn't yet support exchange_bind. Here we
            # backport the support by monkeypatching it to use newer version
            # of pika.spec.DriverMixin.
            from collective.zamqpdemo.spec import DriverMixin
            channel.__class__.__bases__[0].__bases__ = (DriverMixin,)
            ###

            channel.exchange_declare(exchange=member_exchange,
                                     type="fanout",
                                     auto_delete=True,
                                     durable=False)
            channel.exchange_bind(source="amq.direct",
                                  destination=member_exchange,
                                  routing_key=str(member.getId()))

            if can_review:
                channel.exchange_bind(source="reviewers",
                                      destination=member_exchange,
                                      routing_key="submitted")

        return u'"%s"' % member_exchange


@grok.subscribe(Interface, IActionSucceededEvent)
def workflowActionSucceeded(context, event):
    if getattr(event, "action") == "publish":
        notifications = getUtility(IProducer, name="amqpdemo.published")
        notifications._register()
        notifications.publish({
            "url": event.object.absolute_url(),
            "title": event.object.title_or_id(),
        })
    elif getattr(event, "action") == "submit":
        # wftool = getToolByName(context, "portal_workflow")
        # actions = dict(((a["id"], a["name"])
        #                 for a in wftool.listActions(object=event.object)))
        # XXX: Ideally, we should look up the actions that are available with
        # 'Reviewer' role. Not sure, if that's possible without instantiating a
        # new security manager for 'Reviewer'.
        actions = {"publish": "Publish", "reject": "Reject"}
        notifications = getUtility(IProducer, name="amqpdemo.submitted")
        notifications._register()
        notifications.publish({
            "url": event.object.absolute_url(),
            "title": event.object.title_or_id(),
            "actions": actions,
            "uid": IUUID(event.object)
        })
    elif getattr(event, "action") == "reject":
        creator = None
        if hasattr(event.object, "Creator"):
            creator = event.object.Creator()
        notifications = getUtility(IProducer, name="superuser")
        notifications._register()
        notifications.publish("""\
<p>Submission rejected: <a href="%s">%s</a></p>""" % (
    event.object.absolute_url(), event.object.title_or_id()),
    exchange="amq.direct", routing_key=creator, serializer="text/plain")

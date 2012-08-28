# -*- coding: utf-8 -*-
"""Instant role-based notifications for authenticated and anonymous users"""

from hashlib import md5

from five import grok

from zope.interface import Interface
from zope.component import getUtility

from plone.uuid.interfaces import IUUID

from Products.CMFCore.interfaces import ISiteRoot, IActionSucceededEvent
from Products.CMFCore.utils import getToolByName

from collective.zamqp.interfaces import IProducer
from collective.zamqp.connection import BlockingChannel
from collective.zamqp.producer import Producer

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
    exchange_auto_delete = False  # don't self-destroy before broker shutdown
    routing_key = "submitted"
    serializer = "json"

    durable = False


class ConfigureMemberExchange(grok.View):
    """Register and bind personalized member exhange for authenticated users"""
    grok.name("configure-member-exchange")
    grok.context(ISiteRoot)
    grok.require("zope2.View")

    def render(self):
        mtool = getToolByName(self.context, "portal_membership")

        # For unauthenticated users, just return 'null' (JSON)
        if mtool.isAnonymousUser():
            return u"null"

        # We expect to find "__ac" cookie, otherwise just return 'null' (JSON)
        if not "__ac" in self.request.cookies:
            return u"null"

        member = mtool.getAuthenticatedMember()

        # Member exchange name is md5 hash of session cookie, for convenience
        member_exchange = md5()
        member_exchange.update(self.request.cookies.get("__ac"))
        member_exchange = "member-%s" % member_exchange.hexdigest()

        # Decide, should member get reviewer notifications
        can_review = \
            "Reviewer" in member.getRoles() or \
            "Manager" in member.getRoles()

        # Open synchronous blocking connection on broker and configure exchange
        with BlockingChannel("superuser") as channel:
            ###
            # XXX: Pika 0.9.5 doesn't yet support exchange_bind. Here we
            # backport the support by monkeypatching it to use newer version
            # of pika.spec.DriverMixin.
            from collective.zamqpdemo.spec import DriverMixin
            channel.__class__.__bases__[0].__bases__ = (DriverMixin,)
            ###

            # We must declare and bind member specific exchange instead of
            # queue, because the member may have multiple browser tab/window
            # connected and everyone of them should get all the messages.
            channel.exchange_declare(exchange=member_exchange, type="fanout",
                                     auto_delete=True, durable=False)
            # Bind personal notifications
            channel.exchange_bind(source="amq.direct",
                                  destination=member_exchange,
                                  routing_key=str(member.getId()))

            # Yet, because exchange with auto_delete=True would self-destroy
            # immediately after the last connected queue has been disconnected,
            # we need special keepalive queue to keep the exchange alive while
            # the user just moves from one page to another (and her browser
            # temporarily disconnects).
            channel.queue_declare(queue="%s-keepalive" % member_exchange,
                                  auto_delete=False, durable=False,
                                  arguments={"x-expires": 10000})
            channel.queue_bind(queue="%s-keepalive" % member_exchange,
                               exchange=member_exchange, routing_key="*")

            # Bind reviewer notifications
            if can_review:
                channel.exchange_bind(source="reviewers",
                                      destination=member_exchange,
                                      routing_key="submitted")

        # Return member exchange name (JSON)
        return u'"%s"' % member_exchange


@grok.subscribe(Interface, IActionSucceededEvent)
def workflowActionSucceeded(context, event):
    """Publish notifications after specificworkflow actions"""

    if getattr(event, "action") == "publish":
        notifications = getUtility(IProducer, name="amqpdemo.published")
        notifications._register()
        notifications.publish({
            "url": event.object.absolute_url(),
            "title": event.object.title_or_id(),
        })

    elif getattr(event, "action") == "submit":
        # XXX: We should look up the actions that are available with 'Reviewer'
        # role. Not sure, if that's possible without instantiating a new
        # security manager for 'Reviewer'. Well, this is a demo after all...
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
        notifications.publish(
            "<p>Submission rejected:<br/><a href=\"%s\">%s</a></p>" %
            (event.object.absolute_url(), event.object.title_or_id()),
            exchange="amq.direct", routing_key=creator,
            serializer="text/plain")

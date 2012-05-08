# -*- coding: utf-8 -*-
"""Meeting minutes with a PDF"""

import os.path
from StringIO import StringIO

from xhtml2pdf import pisa
from chameleon import PageTemplateFile

from five import grok

from zope.interface import Interface
from zope.component import getUtility
from zope.lifecycleevent.interfaces import\
    IObjectCreatedEvent, IObjectModifiedEvent

from plone.directives import form
from plone.uuid.interfaces import IUUID
from plone.app.uuid.utils import uuidToObject

from plone.app.layout.viewlets.interfaces import IAboveContentTitle
from plone.app.layout.globals.interfaces import IViewView

from plone.namedfile.field import NamedBlobFile as NamedBlobFileField
from plone.namedfile import NamedBlobFile
from plone.app.textfield import RichText

from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName

from collective.zamqp.interfaces import IProducer, IMessageArrivedEvent
from collective.zamqp.producer import Producer
from collective.zamqp.consumer import Consumer

from zope.i18nmessageid import MessageFactory as ZopeMessageFactory
_ = ZopeMessageFactory("collective.zamqpdemo")


class IMinutes(form.Schema):
    """Minutes document schema"""

    body = RichText(
        title=_(u"Body text"),
        default_mime_type="text/x-rst",
        output_mime_type="text/x-html-safe",
        allowed_mime_types=("text/x-rst", "text/html"),
        required=True
        )

    form.omitted("deliverable")
    deliverable = NamedBlobFileField(
        title=_(u"Deliverable"),
        required=False
        )


class IMinutesMessage(Interface):
    """Marker Interface for Minutes AMQP-messages"""


class View(grok.View):
    """Minutes view"""
    grok.context(IMinutes)


class AjaxView(grok.View):
    """Minutes view"""
    grok.context(IMinutes)


class Viewlet(grok.Viewlet):
    grok.context(IMinutes)
    grok.viewletmanager(IAboveContentTitle)
    grok.view(IViewView)


class MinutesProducer(Producer):
    """Produces requests for PDF"""
    grok.name("amqpdemo.minutes")  # is also the routing key

    connection_id = "amqpdemo"
    exchange = "amqpdemo"
    serializer = "text/plain"

    auto_declare = True
    durable = False


class MinutesConsumer(Consumer):
    """Consumes requests for PDF"""
    grok.name("amqpdemo.minutes")  # is also the queue name

    connection_id = "amqpdemo"
    exchange = "amqpdemo"

    auto_declare = True
    durable = False

    marker = IMinutesMessage


@grok.subscribe(IMinutes, IObjectModifiedEvent)
def produceMessage(minutes, event):
    """Produce message"""

    # Clear deliverable
    bound = IMinutes["deliverable"].bind(minutes)
    bound.set(minutes, None)

    # Get producer and publish the message
    producer = getUtility(IProducer, name="amqpdemo.minutes")
    producer._register()  # publish only after the transaction has succeeded
    producer.publish("", correlation_id=IUUID(minutes))  # empty message... :)


@grok.subscribe(IMinutes, IObjectCreatedEvent)
def produceMessageCreated(minutes, event):
    produceMessage(minutes, event)


@grok.subscribe(IMinutesMessage, IMessageArrivedEvent)
def consumeMessage(message, event):
    """Consume message"""

    uuid = message.header_frame.correlation_id
    minutes = uuidToObject(uuid)

    site = getUtility(ISiteRoot)
    mtool = getToolByName(site, "portal_membership")
    creator = mtool.getMemberById(minutes.creators[0])
    date = minutes.modified()

    kwargs = {
        "date": "%s.%s.%s" % (date.day(), date.month(), date.year()),
        "title": minutes.title,
        "author": creator.getProperty("fullname"),
        "email": creator.getProperty("email"),
        "body": minutes.body.output,
        "site": site.Title()
        }

    # Read receipt template from disk
    path = os.path.join(os.path.dirname(__file__), "sfs2487.pt")
    template = PageTemplateFile(path)

    # Render template into HTML
    html = template(**kwargs)

    # Create a PDF from HTML
    pdf = StringIO()
    pisa.CreatePDF(html, pdf)
    pdf.seek(0)

    # Save the PDF
    blob = NamedBlobFile(pdf.read(), filename=u"minutes.pdf")
    bound = IMinutes["deliverable"].bind(minutes)
    bound.set(minutes, blob)

    message.ack()

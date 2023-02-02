from django import template
from wiki.plugins.attachments import models


register = template.Library()


@register.filter
def attachments_for_article(article):
    return models.Attachment.objects.active().filter(articles=article, current_revision__deleted=False).exclude(current_revision__file=None).order_by("original_filename")

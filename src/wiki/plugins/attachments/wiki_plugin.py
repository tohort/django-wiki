from django.urls import include
from django.urls import re_path
from django.utils.translation import gettext as _
from wiki.core.plugins import registry
from wiki.core.plugins.base import BasePlugin
from wiki.plugins.attachments import models
from wiki.plugins.attachments import settings
from wiki.plugins.attachments import views
from wiki.plugins.attachments.markdown_extensions import AttachmentExtension
from wiki.plugins.notifications.settings import ARTICLE_EDIT
from wiki.plugins.notifications.util import truncate_title


class AttachmentPlugin(BasePlugin):
    slug = settings.SLUG
    urlpatterns = {
        "article": [re_path("", include("wiki.plugins.attachments.urls"))]
    }

    article_tab = (_("Attachments"), "fa fa-file")
    article_view = views.AttachmentView().dispatch
    
    sidebar = {
        "headline": _("Attachments"),
        "icon_class": "fa-file",
        "template": "wiki/plugins/attachments/sidebar.html",
        "form_class": None,
        "get_form_kwargs": (lambda a: {}),
    }


    # List of notifications to construct signal handlers for. This
    # is handled inside the notifications plugin.
    notifications = [
        {
            "model": models.AttachmentRevision,
            "message": lambda obj: (
                _("A file was changed: %s")
                if not obj.deleted
                else _("A file was deleted: %s")
            )
            % truncate_title(obj.get_filename()),
            "key": ARTICLE_EDIT,
            "created": True,
            "get_article": lambda obj: obj.attachment.article,
        }
    ]

    markdown_extensions = [AttachmentExtension()]


registry.register(AttachmentPlugin)

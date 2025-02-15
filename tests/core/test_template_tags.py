"""
Almost all test cases covers both tag calling and template using.
"""
from django.conf import settings as django_settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest
from wiki.conf import settings
from wiki.forms import CreateRootForm
from wiki.models import Article
from wiki.models import ArticleForObject
from wiki.models import ArticleRevision
from wiki.templatetags.wiki_tags import article_for_object
from wiki.templatetags.wiki_tags import login_url
from wiki.templatetags.wiki_tags import wiki_form
from wiki.templatetags.wiki_tags import wiki_render

from ..base import TemplateTestCase

if not django_settings.configured:
    django_settings.configure()


# XXX article_for_object accepts context, but not using it
class ArticleForObjectTemplatetagTest(TemplateTestCase):
    template = """
        {% load wiki_tags %}
        {% article_for_object obj as anything %}
        {{ anything }}
    """

    def setUp(self):
        super().setUp()
        from wiki.templatetags import wiki_tags

        wiki_tags._cache = {}

    def test_obj_arg_is_not_a_django_model(self):
        from wiki.templatetags import wiki_tags

        with self.assertRaises(TypeError):
            article_for_object({}, "")

        with self.assertRaises(TypeError):
            article_for_object({"request": 100500}, {})

        with self.assertRaises(TypeError):
            self.render({"obj": "tiger!"})

        self.assertEqual(len(wiki_tags._cache), 0)

    def test_obj_is_not_in__cache_and_articleforobject_is_not_exist(self):
        from wiki.templatetags.wiki_tags import _cache as cache

        obj = Article.objects.create()

        article_for_object({}, obj)

        self.assertIn(obj, cache)
        self.assertIsNone(cache[obj])
        self.assertEqual(len(cache), 1)

        self.render({"obj": obj})

        self.assertIn(obj, cache)
        self.assertIsNone(cache[obj])
        self.assertEqual(len(cache), 1)

    def test_obj_is_not_in__cache_and_articleforobjec_is_exist(self):
        from wiki.templatetags.wiki_tags import _cache as cache

        a = Article.objects.create()
        content_type = ContentType.objects.get_for_model(a)
        ArticleForObject.objects.create(
            article=a, content_type=content_type, object_id=1
        )

        output = article_for_object({}, a)

        self.assertEqual(output, a)
        self.assertIn(a, cache)
        self.assertEqual(cache[a], a)
        self.assertEqual(len(cache), 1)

        self.render({"obj": a})

        self.assertIn(a, cache)
        self.assertEqual(cache[a], a)
        self.assertEqual(len(cache), 1)

    def test_obj_in__cache_and_articleforobject_is_not_exist(self):
        model = Article.objects.create()

        from wiki.templatetags import wiki_tags

        wiki_tags._cache = {model: "spam"}

        article_for_object({}, model)

        self.assertIn(model, wiki_tags._cache)
        self.assertIsNone(wiki_tags._cache[model])
        self.assertEqual(len(wiki_tags._cache), 1)

        self.render({"obj": model})

        self.assertIn(model, wiki_tags._cache)
        self.assertIsNone(wiki_tags._cache[model])
        self.assertEqual(len(wiki_tags._cache), 1)

        self.assertNotIn("spam", wiki_tags._cache.values())

    def test_obj_in__cache_and_articleforobjec_is_exist(self):
        article = Article.objects.create()
        content_type = ContentType.objects.get_for_model(article)
        ArticleForObject.objects.create(
            article=article, content_type=content_type, object_id=1
        )

        from wiki.templatetags import wiki_tags

        wiki_tags._cache = {article: "spam"}

        output = article_for_object({}, article)

        self.assertEqual(output, article)
        self.assertIn(article, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[article], article)

        output = self.render({"obj": article})

        self.assertIn(article, wiki_tags._cache)
        self.assertEqual(wiki_tags._cache[article], article)

        expected = "Article without content (1)"

        self.assertIn(expected, output)


# TODO manage plugins in template
class WikiRenderTest(TemplateTestCase):
    template = """
        {% load wiki_tags %}
        {% wiki_render article pc %}
    """

    def tearDown(self):
        from wiki.core.plugins import registry

        registry._cache = {}
        super().tearDown()

    keys = [
        "article",
        "content",
        "preview",
        "plugins",
        "STATIC_URL",
        "CACHE_TIMEOUT",
    ]

    def test_if_preview_content_is_none(self):
        # monkey patch
        from wiki.core.plugins import registry

        registry._cache = {"ham": "spam"}

        article = Article.objects.create()

        output = wiki_render({}, article)

        self.assertCountEqual(self.keys, output)

        self.assertEqual(output["article"], article)
        self.assertIsNone(output["content"])
        self.assertIs(output["preview"], False)

        self.assertEqual(output["plugins"], {"ham": "spam"})
        self.assertEqual(output["STATIC_URL"], django_settings.STATIC_URL)
        self.assertEqual(output["CACHE_TIMEOUT"], settings.CACHE_TIMEOUT)

        # Additional check
        self.render({"article": article, "pc": None})

    def test_called_with_preview_content_and_article_have_current_revision(
        self
    ):
        article = Article.objects.create()
        ArticleRevision.objects.create(
            article=article,
            title="Test title",
            content="Some beauty test text",
        )

        content = (
            """This is a normal paragraph\n"""
            """\n"""
            """Headline\n"""
            """========\n"""
        )

        expected = (
            """(?s).*<p>This is a normal paragraph</p>\n"""
            """<h1 id="wiki-toc-headline">Headline"""
            """.*</h1>.*"""
        )

        # monkey patch
        from wiki.core.plugins import registry

        registry._cache = {"spam": "eggs"}

        output = wiki_render({}, article, preview_content=content)
        self.assertCountEqual(self.keys, output)
        self.assertEqual(output["article"], article)
        self.assertRegexpMatches(output["content"], expected)
        self.assertIs(output["preview"], True)
        self.assertEqual(output["plugins"], {"spam": "eggs"})
        self.assertEqual(output["STATIC_URL"], django_settings.STATIC_URL)
        self.assertEqual(output["CACHE_TIMEOUT"], settings.CACHE_TIMEOUT)

        output = self.render({"article": article, "pc": content})
        self.assertRegexpMatches(output, expected)

    def test_called_with_preview_content_and_article_dont_have_current_revision(
        self
    ):
        article = Article.objects.create()

        content = (
            """This is a normal paragraph\n"""
            """\n"""
            """Headline\n"""
            """========\n"""
        )

        # monkey patch
        from wiki.core.plugins import registry

        registry._cache = {"spam": "eggs"}

        output = wiki_render({}, article, preview_content=content)

        self.assertCountEqual(self.keys, output)

        self.assertEqual(output["article"], article)

        self.assertMultiLineEqual(output["content"], "")
        self.assertIs(output["preview"], True)

        self.assertEqual(output["plugins"], {"spam": "eggs"})
        self.assertEqual(output["STATIC_URL"], django_settings.STATIC_URL)
        self.assertEqual(output["CACHE_TIMEOUT"], settings.CACHE_TIMEOUT)

        self.render({"article": article, "pc": content})


class WikiFormTest(TemplateTestCase):
    template = """
        {% load wiki_tags %}
        {% wiki_form form_obj %}
    """

    def test_form_obj_is_not_baseform_instance(self):
        context = {"test_key": "test_value"}
        form_obj = "ham"

        with self.assertRaises(TypeError):
            wiki_form(context, form_obj)

        self.assertEqual(context, {"test_key": "test_value"})

        with self.assertRaises(TypeError):
            self.render({"test_key": 100500})

        self.assertEqual(context, {"test_key": "test_value"})

    def test_form_obj_is_baseform_instance(self):
        context = {"test_key": "test_value"}

        # not by any special reasons, just a form
        form_obj = CreateRootForm()

        wiki_form(context, form_obj)

        self.assertEqual(context, {"test_key": "test_value", "form": form_obj})

        self.render({"form_obj": form_obj})

        self.assertEqual(context, {"test_key": "test_value", "form": form_obj})


class LoginUrlTest(TemplateTestCase):
    template = """
        {% load wiki_tags %}
        {% login_url as some_url %}
        {{ some_url }}
    """

    def test_no_request_in_context(self):
        with self.assertRaises(KeyError):
            login_url({})

        with self.assertRaises(KeyError):
            self.render({})

    def test_login_url_if_no_query_string_in_request(self):
        r = HttpRequest()
        r.META = {}
        r.path = "best/test/page/ever/"

        output = login_url({"request": r})

        expected = "/_accounts/login/?next=best/test/page/ever/"

        self.assertEqual(output, expected)

        output = self.render({"request": r})

        self.assertIn(expected, output)

    def test_login_url_if_query_string_is_empty(self):
        r = HttpRequest()
        r.META = {"QUERY_STRING": ""}
        r.path = "best/test/page/ever/"

        output = login_url({"request": r})

        expected = "/_accounts/login/?next=best/test/page/ever/"

        self.assertEqual(output, expected)

        output = self.render({"request": r})

        self.assertIn(expected, output)

    def test_login_url_if_query_string_is_not_empty(self):
        r = HttpRequest()
        r.META = {"QUERY_STRING": "title=Main_page&action=raw"}
        r.path = "best/test/page/ever/"

        context = {"request": r}

        output = login_url(context)

        expected = (
            "/_accounts/login/"
            "?next=best/test/page/ever/%3Ftitle%3DMain_page%26action%3Draw"
        )

        self.assertEqual(output, expected)

        output = self.render({"request": r})

        self.assertIn(expected, output)

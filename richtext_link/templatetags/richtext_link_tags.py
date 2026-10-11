from django import template
from django.core.exceptions import ObjectDoesNotExist
from django.template.defaultfilters import stringfilter
from django.utils.encoding import force_str

from richtext_link import utils

register = template.Library()


@register.filter
@stringfilter
def richtext_link_add_links(html):
    link_model = utils.get_link_model()
    if not link_model:
        return html
    fragment = utils.parse_html_fragment(html)
    for link in utils.iter_link_elements(fragment):
        kwargs = utils.link_kwargs_from_element(link, link_model, pop_attrs=True)
        try:
            # this can go wrong with fk and the like
            real_link = link_model(**kwargs)
            link.set("href", force_str(real_link.get_link()))
            if getattr(real_link, "get_link_target", None):
                link.set("target", real_link.get_link_target())
            if getattr(real_link, "get_link_style", None):
                link.set("class", real_link.get_link_style())
            if getattr(real_link, "get_link_attrs", None):
                for attr, value in real_link.get_link_attrs().items():
                    link.set(attr, value)
        except (ValueError, ObjectDoesNotExist):
            continue
    return utils.serialize_html_fragment(fragment)

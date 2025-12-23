from django import template

register = template.Library()

@register.simple_tag
def querystring_without_page(request):
    params = request.GET.copy()
    params.pop('page', None)
    qs = params.urlencode()
    return f"&{qs}" if qs else ""

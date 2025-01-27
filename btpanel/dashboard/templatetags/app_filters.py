from django import template
import json

register = template.Library()

@register.filter
def json_parse(value):
    """将JSON字符串转换为Python对象"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value 
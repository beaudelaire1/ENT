from django import template

from planner.continuity import task_resources as collect_task_resources

register = template.Library()


@register.simple_tag
def task_resources(task):
    """`{% task_resources task as resources %}` : voir `planner.continuity.task_resources`."""
    return collect_task_resources(task)

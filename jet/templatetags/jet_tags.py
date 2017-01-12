from __future__ import unicode_literals
import json
from django import template
from django.core.urlresolvers import reverse
from django.forms import CheckboxInput, ModelChoiceField, Select, ModelMultipleChoiceField, SelectMultiple
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.utils.formats import get_format
from django.utils.safestring import mark_safe
from django.utils.encoding import smart_text
from ..import settings
from ..utils import get_app_list, get_model_instance_label, get_admin_site


register = template.Library()


@register.simple_tag
def jet_get_date_format():
    return get_format('DATE_INPUT_FORMATS')[0]


@register.simple_tag
def jet_get_time_format():
    return get_format('TIME_INPUT_FORMATS')[0]


@register.simple_tag
def jet_get_datetime_format():
    return get_format('DATETIME_INPUT_FORMATS')[0]


@register.assignment_tag(takes_context=True)
def jet_get_menu(context):
    if settings.JET_SIDE_MENU_CUSTOM_APPS not in (None, False):
        app_list = get_app_list(context, False)
        app_dict = {}
        models_dict = {}

        for app in app_list:
            app_label = app.get('app_label', app.get('name'))
            app_dict[app_label] = app

            for model in app['models']:
                if app_label not in models_dict:
                    models_dict[app_label] = {}

                models_dict[app_label][model['object_name']] = model

            app['models'] = []

        app_list = []
        settings_app_list = settings.JET_SIDE_MENU_CUSTOM_APPS

        if isinstance(settings_app_list, dict):
            admin_site = get_admin_site(context)
            settings_app_list = settings_app_list.get(admin_site.name, [])

        for item in settings_app_list:
            app_label, models = item

            if app_label in app_dict:
                app = app_dict[app_label]

                for model_label in models:
                    if model_label == '__all__':
                        app['models'] = models_dict[app_label].values()
                        break
                    elif model_label in models_dict[app_label]:
                        model = models_dict[app_label][model_label]
                        app['models'].append(model)

                app_list.append(app)
    else:
        app_list = get_app_list(context)

    current_found = False

    apps = []

    for app in app_list:
        if not current_found:
            for model in app['models']:
                if 'admin_url' in model and context['request'].path.startswith(model['admin_url']):
                    model['current'] = True
                    current_found = True
                    break

            if not current_found and context['request'].path.startswith(app['app_url']):
                app['current'] = True
                current_found = True

        apps.append(app)

    return {'apps': apps}


@register.filter
def jet_is_checkbox(field):
    return field.field.widget.__class__.__name__ == CheckboxInput().__class__.__name__


@register.filter
def jet_select2_lookups(field):
    if hasattr(field, 'field') and \
            (isinstance(field.field, ModelChoiceField) or isinstance(field.field, ModelMultipleChoiceField)):
        qs = field.field.queryset
        model = qs.model
        if getattr(model, 'autocomplete_search_fields', None) and getattr(field.field, 'autocomplete', True):
            choices = []
            app_label = model._meta.app_label
            model_name = model._meta.object_name

            attrs = {
                'class': 'ajax',
                'data-app-label': app_label,
                'data-model': model_name,
                'data-ajax--url': reverse('jet:model_lookup')
            }
            form = field.form
            initial_value = form.data.get(field.name) if form.data != {} else form.initial.get(field.name)

            if hasattr(field, 'field') and isinstance(field.field, ModelMultipleChoiceField):
                if initial_value:
                    initial_objects = model.objects.filter(pk__in=initial_value)
                    choices.extend(
                        [(initial_object.pk, get_model_instance_label(initial_object))
                            for initial_object in initial_objects]
                    )

                if isinstance(field.field.widget, RelatedFieldWidgetWrapper):
                    field.field.widget.widget = SelectMultiple(attrs)
                else:
                    field.field.widget = SelectMultiple(attrs)
                field.field.choices = choices
            elif hasattr(field, 'field') and isinstance(field.field, ModelChoiceField):
                if initial_value:
                    initial_object = model.objects.get(pk=initial_value)
                    attrs['data-object-id'] = initial_value
                    choices.append((initial_object.pk, get_model_instance_label(initial_object)))

                if isinstance(field.field.widget, RelatedFieldWidgetWrapper):
                    field.field.widget.widget = Select(attrs)
                else:
                    field.field.widget = Select(attrs)
                field.field.choices = choices

    return field


@register.assignment_tag(takes_context=True)
def jet_popup_response_data(context):
    if context.get('popup_response_data'):
        return context['popup_response_data']

    return json.dumps({
        'action': context.get('action'),
        'value': context.get('value') or context.get('pk_value'),
        'obj': smart_text(context.get('obj')),
        'new_value': context.get('new_value')
    })


@register.simple_tag(takes_context=True)
def jet_delete_confirmation_context(context):
    if context.get('deletable_objects') is None and context.get('deleted_objects') is None:
        return ''
    return mark_safe('<div class="delete-confirmation-marker"></div>')

from django.contrib import admin

from dynamic_template.models import DynamicRelationContext


class DynamicRelationContextInline(admin.TabularInline):
    model = DynamicRelationContext
    extra = 0

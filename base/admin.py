from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'username', 'auth_provider', 'is_staff', 'is_active', 'bio', "credits",'date_joined', 'avi', 'isPrivate',"allow_Calendar")
    list_filter = ('email', 'username', 'is_staff', 'is_active', 'auth_provider',)
    fieldsets = (
        (None, {'fields': ('email', 'username', 'password',"google_calendar_token","google_calendar_refresh_token","google_calendar_token_expiry")}),
        ('Personal Info', {'fields': ('bio', 'date_joined', 'avi', "credits",'auth_provider',"tjobs","usessions","csessions","passed", "failed",)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'user_permissions', 'isPrivate')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser', 'isPrivate','user_permissions', 'bio', 'avi', 'auth_provider', "credits","tjobs","usessions","csessions","passed", "failed","google_calendar_token","google_calendar_refresh_token","google_calendar_token_expiry" ),
        }),
    )
    search_fields = ('email',)
    ordering = ('email',)
    readonly_fields = ('date_joined',)  # Make date_joined non-editable



admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Job)
admin.site.register(Interview)
admin.site.register(PreparationMaterial)
admin.site.register(PreparationBlock)
admin.site.register(Notification)
admin.site.register(InterviewSession)
admin.site.register(InterviewBlock)
admin.site.register(YouTubeLink)
admin.site.register(GoogleSearchResult)
admin.site.register(CodingQuestion)
admin.site.register(InterviewCodingQuestion)
admin.site.register(Code)
admin.site.register(Asisstant)


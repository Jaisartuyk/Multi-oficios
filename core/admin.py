from django.contrib import admin
from .models import Category, Professional, Service, UserProfile, JobRequest, Notification

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'demand', 'icon')
    search_fields = ('name',)

@admin.register(Professional)
class ProfessionalAdmin(admin.ModelAdmin):
    list_display = ('name', 'specialty', 'level', 'rating', 'credits', 'location')
    search_fields = ('name', 'specialty')
    list_filter = ('level', 'rating', 'credits')

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'range', 'time')
    search_fields = ('name',)

@admin.register(JobRequest)
class JobRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'client', 'professional', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'description')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'notif_type', 'is_read', 'created_at')
    list_filter = ('notif_type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__username')
    actions = ['mark_as_read']

    @admin.action(description='Marcar como leídas')
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)

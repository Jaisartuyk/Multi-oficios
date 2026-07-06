from django.contrib import admin
from .models import (
    AiUsage,
    Category,
    JobRequest,
    Notification,
    Payment,
    PortfolioItem,
    Professional,
    Quote,
    Recharge,
    Review,
    Service,
    UserProfile,
)

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

@admin.register(Recharge)
class RechargeAdmin(admin.ModelAdmin):
    list_display = ('professional', 'amount_paid', 'credits_added', 'payment_method', 'created_at')
    list_filter = ('payment_method', 'created_at')
    search_fields = ('professional__name', 'professional__user__username')
    date_hierarchy = 'created_at'


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('job', 'professional', 'amount', 'estimated_days', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('job__title', 'professional__name')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('job', 'professional', 'rating', 'punctuality', 'quality', 'created_at')
    list_filter = ('rating', 'created_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('job', 'client', 'professional', 'amount', 'status', 'guarantee_status')
    list_filter = ('status', 'guarantee_status', 'method')
    search_fields = ('job__title', 'receipt_reference', 'client__username')


admin.site.register(PortfolioItem)
admin.site.register(AiUsage)

from django.contrib import admin
from scheduler_api.models import Employee, TimetableFile, Schedule


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(TimetableFile)
class TimetableFileAdmin(admin.ModelAdmin):
    list_display = ['file', 'uploaded_at']
    readonly_fields = ['uploaded_at']


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ['employee', 'day_of_week', 'start_time', 'end_time', 'task_name', 'is_proxy', 'proxy_teacher_name']
    list_filter = ['day_of_week', 'is_proxy']
    search_fields = ['employee__name', 'task_name']
    ordering = ['day_of_week', 'start_time']

from django.urls import path
from scheduler_api.views import (
    IndexView,
    TimetableUploadView,
    TimetableConfirmView,
    ChatAssistantView,
    ProxyManualView,
    AuthLoginView,
    AuthLogoutView,
    AuthRegisterView,
    SwapRequestCreateView,
    SwapRequestActionView,
    SyllabusLogCreateView,
    ProfileAlertUpdateView,
    UpdateRoomView,
    ResetDemoDatabaseView,
)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('api/upload/', TimetableUploadView.as_view(), name='timetable_upload'),
    path('api/confirm/', TimetableConfirmView.as_view(), name='timetable_confirm'),
    path('api/chat/', ChatAssistantView.as_view(), name='chat_assistant'),
    path('api/proxy/', ProxyManualView.as_view(), name='proxy_manual'),
    path('api/auth/login/', AuthLoginView.as_view(), name='auth_login'),
    path('api/auth/logout/', AuthLogoutView.as_view(), name='auth_logout'),
    path('api/auth/register/', AuthRegisterView.as_view(), name='auth_register'),
    path('api/swap-request/create/', SwapRequestCreateView.as_view(), name='swap_request_create'),
    path('api/swap-request/action/', SwapRequestActionView.as_view(), name='swap_request_action'),
    path('api/syllabus-log/create/', SyllabusLogCreateView.as_view(), name='syllabus_log_create'),
    path('api/profile/update-alerts/', ProfileAlertUpdateView.as_view(), name='profile_alert_update'),
    path('api/schedule/update-room/', UpdateRoomView.as_view(), name='update_room'),
    path('api/reset-demo-db/', ResetDemoDatabaseView.as_view(), name='reset_demo_db'),
]

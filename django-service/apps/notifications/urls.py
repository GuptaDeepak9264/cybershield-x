from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("send/", views.send_notification, name="send"),
    path("sent/", views.sent_list, name="sent_list"),
    path("inbox/", views.inbox, name="inbox"),
    path("<int:notification_id>/mark-read/", views.mark_read, name="mark_read"),
]

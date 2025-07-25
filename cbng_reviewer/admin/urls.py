from django.urls import path

from cbng_reviewer.admin import views

urlpatterns = [
    path("", views.dashboard, name="admin"),
    path("users/", views.users, name="admin-users"),
    path("users/<int:id>/change-flag/", views.user_change_flag, name="admin-change-user-flags"),
    path("edit-groups/", views.edit_groups, name="admin-edit-groups"),
    path("edit-groups/<int:id>/", views.view_edit_group, name="admin-edit-group"),
    path("edit/<int:id>/", views.view_edit, name="admin-edit"),
]

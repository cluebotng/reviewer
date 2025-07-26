from django.urls import include, path
from rest_framework import routers

from cbng_reviewer.api import views

v1_router = routers.DefaultRouter()
v1_router.register("edit-groups", views.EditGroupViewSet, basename="edit-group")

urlpatterns = [
    path("v1/", include(v1_router.urls)),
    path("v1/reviewer/next-edit/", views.get_next_edit_id_for_review),
    path("v1/reviewer/classify-edit/", views.store_edit_classification),
    path("v1/edit/<int:edit_id>/dump-wpedit/", views.dump_edit_as_wp_edit),
]

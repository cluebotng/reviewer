from django.shortcuts import render, redirect, get_object_or_404

from cbng_reviewer.admin.forms import EditGroupForm
from cbng_reviewer.libs.django import admin_required
from cbng_reviewer.libs.utils import notify_user_review_rights_granted, notify_user_admin_rights_granted
from cbng_reviewer.models import User, EditGroup, Edit, Classification


@admin_required()
def dashboard(request):
    return render(request, "cbng_reviewer/admin/dashboard.html")


@admin_required()
def users(request):
    return render(
        request,
        "cbng_reviewer/admin/users.html",
        {
            "admin_users": User.objects.filter(is_admin=1).order_by("date_joined"),
            "reviewer_users": User.objects.filter(is_reviewer=1).order_by("date_joined"),
            "registered_users": User.objects.filter(is_admin=0, is_reviewer=0).order_by("date_joined"),
        },
    )


@admin_required()
def user_change_flag(request, id: int):
    if request.method == "POST":
        user = get_object_or_404(User, id=id)

        if reviewer_flag := request.POST.get("reviewer"):
            user.is_reviewer = reviewer_flag == "1"
            if user.is_reviewer:
                notify_user_review_rights_granted(user)

        if admin_flag := request.POST.get("admin"):
            user.is_admin = admin_flag == "1"
            if user.is_admin:
                notify_user_admin_rights_granted(user)

        user.save()

    return redirect("/admin/users/")


@admin_required()
def edit_groups(request):
    return render(
        request,
        "cbng_reviewer/admin/edit_groups.html",
        {
            "edit_groups": EditGroup.objects.all(),
        },
    )


@admin_required()
def view_edit_group(request, id: int):
    edit_group = get_object_or_404(EditGroup, id=id)

    if request.method == "POST":
        form = EditGroupForm(request.POST, instance=edit_group)
        if form.is_valid():
            form.save()
            return redirect("/admin/edit-groups/")
    else:
        form = EditGroupForm(instance=edit_group)

    return render(
        request,
        "cbng_reviewer/admin/edit_group.html",
        {
            "edit_group": edit_group,
            "form": form,
        },
    )


@admin_required()
def view_edit(request, id: int):
    edit = get_object_or_404(Edit, id=id)
    return render(
        request,
        "cbng_reviewer/admin/edit.html",
        {
            "edit": edit,
            "classifications": Classification.objects.filter(edit=edit).prefetch_related("user"),
        },
    )

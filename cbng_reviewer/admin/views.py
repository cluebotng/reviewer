from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from cbng_reviewer.admin.forms import EditGroupForm, AddUserForm
from cbng_reviewer.libs.django import admin_required
from cbng_reviewer.libs.irc import IrcRelay
from cbng_reviewer.libs.messages import Messages
from cbng_reviewer.libs.utils import create_user_with_central_auth_mapping
from cbng_reviewer.models import User, EditGroup, Edit, Classification


@admin_required()
def dashboard(request):
    return render(request, "cbng_reviewer/admin/dashboard.html")


@admin_required()
def users(request):
    if request.method == "POST":
        form = AddUserForm(request.POST)
        if form.is_valid():
            if user := create_user_with_central_auth_mapping(form.cleaned_data["username"]):
                if not user.is_reviewer:
                    user.is_reviewer = True
                    user.save()
                    # Note: Don't send the user an email, assume this is a special case of discussion elsewhere
                    IrcRelay().send_message(Messages().notify_irc_about_granted_admin_access(user))

                    messages.add_message(request, messages.SUCCESS, "User created with reviewer rights")
                else:
                    messages.add_message(request, messages.SUCCESS, "User is already reviewer")
            else:
                messages.add_message(
                    request, messages.ERROR, "The specified username could not be found in the central auth database"
                )
            return redirect("/admin/users/")
    else:
        form = AddUserForm

    return render(
        request,
        "cbng_reviewer/admin/users.html",
        {
            "add_user_form": form,
            "admin_users": User.objects.filter(is_admin=1).order_by("date_joined"),
            "reviewer_users": User.objects.filter(is_reviewer=1).order_by("date_joined"),
            "registered_users": User.objects.filter(is_admin=0, is_reviewer=0).order_by("date_joined"),
        },
    )


@admin_required()
def user_change_flag(request, id: int):
    if request.method == "POST":
        user = get_object_or_404(User, id=id)
        messages = Messages()
        irc_relay = IrcRelay()

        if reviewer_flag := request.POST.get("reviewer"):
            user.is_reviewer = reviewer_flag == "1"
            irc_relay.send_message(
                messages.notify_irc_about_granted_reviewer_access(user)
                if user.is_reviewer
                else messages.notify_irc_about_removed_reviewer_access(user)
            )

        if admin_flag := request.POST.get("admin"):
            user.is_admin = admin_flag == "1"
            irc_relay.send_message(
                messages.notify_irc_about_granted_admin_access(user)
                if user.is_admin
                else messages.notify_irc_about_removed_admin_access(user)
            )

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

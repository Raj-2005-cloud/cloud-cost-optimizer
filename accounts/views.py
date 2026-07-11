import boto3
from botocore.exceptions import ClientError

from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from .forms import AWSAccountForm
from .models import AWSAccount


def register_view(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard")

    else:
        form = UserCreationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            login(request, form.get_user())
            return redirect("dashboard")

    else:
        form = AuthenticationForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


def connect_aws(request):

    if request.method == "POST":

        form = AWSAccountForm(request.POST)

        if form.is_valid():

            access_key = form.cleaned_data["access_key"]
            secret_key = form.cleaned_data["secret_key"]

            try:

                # Verify credentials
                sts = boto3.client(
                    "sts",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name="us-east-1",
                )

                sts.get_caller_identity()

                AWSAccount.objects.update_or_create(
                    user=request.user,
                    defaults={
                        "access_key": access_key,
                        "secret_key": secret_key,
                        # default region only
                        "region": "ap-south-1",
                    },
                )

                return redirect("dashboard")

            except ClientError:

                form.add_error(None, "Invalid AWS Credentials")

    else:

        form = AWSAccountForm()

    return render(
        request,
        "dashboard/connect_aws.html",
        {
            "form": form
        },
    )
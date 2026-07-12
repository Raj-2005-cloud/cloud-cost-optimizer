import boto3

from datetime import datetime, timedelta

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

from accounts.models import AWSAccount


@login_required
def cost_dashboard(request):

    aws = AWSAccount.objects.filter(user=request.user).first()
    if not aws:
        return redirect("connect_aws")

    ce = boto3.client(
        "ce",
        aws_access_key_id=aws.access_key,
        aws_secret_access_key=aws.secret_key,
        region_name="us-east-1",      # Cost Explorer always uses us-east-1
    )

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)

    services = []
    total = 0
    error = None

    try:

        response = ce.get_cost_and_usage(
            TimePeriod={
                "Start": str(start),
                "End": str(end),
            },
            Granularity="MONTHLY",
            Metrics=["UnblendedCost"],
            GroupBy=[
                {
                    "Type": "DIMENSION",
                    "Key": "SERVICE",
                }
            ],
        )

        print(response)

        groups = response["ResultsByTime"][0]["Groups"]

        for group in groups:

            service = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])

            total += cost

            services.append({
                "service": service,
                "cost": round(cost, 2),
            })

    except Exception as e:
        error = str(e)

    context = {
        "services": services,
        "total": round(total, 2),
        "error": error,
    }

    return render(
        request,
        "billing/dashboard.html",
        context,
    )
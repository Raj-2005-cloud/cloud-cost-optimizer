from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from accounts.models import AWSAccount

import boto3
from datetime import datetime, timedelta


def home(request):
    return render(request, "home.html")


@login_required
def dashboard(request):
    aws_account = AWSAccount.objects.filter(user=request.user).first()

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "aws_account": aws_account,
        },
    )


@login_required
def analytics(request):

    aws = AWSAccount.objects.filter(user=request.user).first()

    if not aws:
        return render(request, "dashboard/analytics.html")

    access_key = aws.access_key
    secret_key = aws.secret_key
    region = aws.region

    # ==========================
    # EC2
    # ==========================

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    reservations = ec2.describe_instances()["Reservations"]

    ec2_count = sum(len(r["Instances"]) for r in reservations)

    # ==========================
    # S3
    # ==========================

    s3 = boto3.client(
        "s3",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    bucket_count = len(s3.list_buckets()["Buckets"])

    # ==========================
    # EBS
    # ==========================

    ebs_count = len(ec2.describe_volumes()["Volumes"])

    # ==========================
    # RDS
    # ==========================

    rds = boto3.client(
        "rds",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    try:
        rds_count = len(rds.describe_db_instances()["DBInstances"])
    except Exception:
        rds_count = 0

    # ==========================
    # TOTAL RESOURCES
    # ==========================

    total_resources = (
        ec2_count +
        bucket_count +
        ebs_count +
        rds_count
    )

    # ==========================
    # BILLING
    # ==========================

    ce = boto3.client(
        "ce",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
    )

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)

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

    pie_labels = []
    pie_values = []

    total_cost = 0

    for group in response["ResultsByTime"][0]["Groups"]:

        service = group["Keys"][0]
        cost = round(
            float(group["Metrics"]["UnblendedCost"]["Amount"]),
            2,
        )

        pie_labels.append(service)
        pie_values.append(cost)

        total_cost += cost

    # ==========================
    # DASHBOARD METRICS
    # ==========================

    savings = 250
    score = 92

    trend = [
        total_cost,
        total_cost,
        total_cost,
        total_cost,
    ]

    recommendations = [
        {
            "service": "EC2",
            "text": "Stop idle EC2 instances",
            "savings": 120,
        },
        {
            "service": "EBS",
            "text": "Delete unattached EBS volumes",
            "savings": 60,
        },
        {
            "service": "S3",
            "text": "Enable Intelligent Tiering",
            "savings": 40,
        },
        {
            "service": "RDS",
            "text": "Resize idle database",
            "savings": 30,
        },
    ]

    return render(
        request,
        "dashboard/analytics.html",
        {
            "total_cost": round(total_cost, 2),
            "total_resources": total_resources,
            "savings": savings,
            "score": score,
            "pie_labels": pie_labels,
            "pie_values": pie_values,
            "trend": trend,
            "recommendations": recommendations,
        },
    )
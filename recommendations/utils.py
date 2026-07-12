def analyze_ec2(instance):

    cpu = instance["cpu"]
    state = instance["state"]

    if state == "stopped":
        return {
            "recommendation": "Terminate unused instance",
            "severity": "warning",
            "savings": 15,
        }

    elif state == "running" and cpu < 5:
        return {
            "recommendation": "Stop idle instance",
            "severity": "warning",
            "savings": 25,
        }

    else:
        return {
            "recommendation": "Instance is healthy",
            "severity": "success",
            "savings": 0,
        }


def analyze_ebs(volume):

    if not volume["attached"]:
        return {
            "recommendation": "Delete unattached EBS volume",
            "severity": "warning",
            "savings": 8,
        }

    return {
        "recommendation": "Volume is healthy",
        "severity": "success",
        "savings": 0,
    }


def analyze_s3(bucket):

    return {
        "recommendation": "Enable Intelligent Tiering",
        "severity": "info",
        "savings": 3,
    }


def analyze_rds(db):

    if db["status"] != "available":
        return {
            "recommendation": "Review database status",
            "severity": "warning",
            "savings": 0,
        }

    return {
        "recommendation": "Database is healthy",
        "severity": "success",
        "savings": 0,
    }


def send_email_alert(to_email, subject, message):
    if not to_email:
        return
    print(f"\n==========================================")
    print(f"[EMAIL] SIMULATED EMAIL SENT TO: {to_email}")
    print(f"Subject: {subject}")
    print(f"Message: {message}")
    print(f"==========================================\n")

    # Optional real SMTP sending if credentials provided
    from django.core.mail import send_mail
    from django.conf import settings
    if getattr(settings, 'EMAIL_HOST_USER', None):
        try:
            send_mail(
                subject,
                message,
                settings.EMAIL_HOST_USER,
                [to_email],
                fail_silently=False,
            )
            print(f"Real email alert dispatched to {to_email} via Gmail SMTP.")
        except Exception as e:
            print(f"Failed to dispatch Gmail email: {e}")
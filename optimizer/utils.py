def analyze_ec2(instance):

    recommendation = "Healthy"
    savings = 0
    severity = "success"

    if instance["state"] == "stopped":
        recommendation = "Terminate if unused"
        savings = 150
        severity = "warning"

    elif instance["state"] == "running":

        if instance["cpu"] < 5:
            recommendation = "Low CPU usage. Consider stopping."
            savings = 250
            severity = "warning"

    return {
        "recommendation": recommendation,
        "savings": savings,
        "severity": severity,
    }


def analyze_ebs(volume):

    if not volume["attached"]:
        return {
            "recommendation": "Delete unattached volume",
            "savings": 100,
            "severity": "warning",
        }

    return {
        "recommendation": "Healthy",
        "savings": 0,
        "severity": "success",
    }


def analyze_rds(db):

    if db["status"] != "available":
        return {
            "recommendation": "Database needs attention",
            "savings": 0,
            "severity": "warning",
        }

    return {
        "recommendation": "Healthy",
        "savings": 0,
        "severity": "success",
    }


def analyze_s3(bucket):

    return {
        "recommendation": "Review lifecycle policy",
        "savings": 0,
        "severity": "info",
    }
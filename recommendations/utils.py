def analyze_ec2(instance):

    state = instance["state"]
    cpu = instance["cpu"]

    recommendation = "Healthy"
    savings = 0
    severity = "success"

    # -----------------------------
    # TERMINATED
    # -----------------------------
    if state == "terminated":
        recommendation = "Already terminated."
        severity = "secondary"

    # -----------------------------
    # STOPPED
    # -----------------------------
    elif state == "stopped":
        recommendation = "Delete if not required."
        savings = 150
        severity = "warning"

    # -----------------------------
    # RUNNING
    # -----------------------------
    elif state == "running":

        if cpu <= 5:
            recommendation = (
                "Very low CPU usage. Stop or resize this EC2 instance."
            )
            savings = 400
            severity = "danger"

        elif cpu <= 20:
            recommendation = (
                "Low CPU usage. Consider downsizing."
            )
            savings = 200
            severity = "warning"

        elif cpu <= 60:
            recommendation = (
                "Healthy utilization."
            )
            savings = 0
            severity = "success"

        else:
            recommendation = (
                "High CPU utilization. Upgrade instance if performance is affected."
            )
            savings = 0
            severity = "primary"

    return {
        "recommendation": recommendation,
        "savings": savings,
        "severity": severity,
    }

from flask import Flask, jsonify, request
import boto3
import os
import random
import logging

app = Flask(__name__)

APP_VERSION = os.getenv("APP_VERSION", "v1")
APP_ENVIRONMENT = os.getenv("APP_ENVIRONMENT", "dev")
FAIL_PERCENT = float(os.getenv("FAIL_PERCENT", "0"))

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
CW_NAMESPACE = os.getenv("CLOUDWATCH_NAMESPACE", "DevOpsDemo")

logging.basicConfig(level=logging.INFO)

cloudwatch = boto3.client(
    "cloudwatch",
    region_name=AWS_REGION
)


def publish_metrics(status_code):

    dimensions = [
        {
            "Name": "Environment",
            "Value": APP_ENVIRONMENT
        },
        {
            "Name": "Version",
            "Value": APP_VERSION
        }
    ]

    metric_data = [
        {
            "MetricName": "RequestCount",
            "Dimensions": dimensions,
            "Value": 1,
            "Unit": "Count"
        }
    ]

    if status_code >= 500:
        metric_data.append({
            "MetricName": "ErrorCount",
            "Dimensions": dimensions,
            "Value": 1,
            "Unit": "Count"
        })

    try:
        cloudwatch.put_metric_data(
            Namespace=CW_NAMESPACE,
            MetricData=metric_data
        )
    except Exception:
        # Monitoring failures must not break the application.
        app.logger.exception("CloudWatch metric publishing failed")


@app.after_request
def record_request(response):

    # Only count business requests, not Kubernetes probes.
    if request.path == "/":
        publish_metrics(response.status_code)

    return response


@app.route("/")
def home():

    if random.random() * 100 < FAIL_PERCENT:

        app.logger.error(
            "Simulated failure: version=%s",
            APP_VERSION
        )

        return jsonify({
            "status": "ERROR",
            "version": APP_VERSION,
            "message": "Order service unavailable"
        }), 500

    return jsonify({
        "application": "DevOps Demo Order Service",
        "status": "HEALTHY",
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT,
        "message": "Order service running successfully"
    }), 200


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/ready")
def ready():
    return jsonify({"status": "ready"}), 200


@app.route("/version")
def version():
    return jsonify({
        "version": APP_VERSION,
        "environment": APP_ENVIRONMENT
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

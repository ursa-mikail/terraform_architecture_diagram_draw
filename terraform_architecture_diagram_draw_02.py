# !pip install diagrams requests python-hcl2

import os
import requests
import hcl2
from diagrams import Diagram, Cluster, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.network import Subnet
from diagrams.onprem.monitoring import Prometheus
from diagrams.onprem.network import Internet
from diagrams.onprem.client import Users
from diagrams.programming.framework import React
from diagrams.saas.alerting import Pagerduty
from diagrams.saas.chat import Slack

def download_terraform_file(url, output_path):
    """Download Terraform file from URL"""
    print(f"⬇️ Downloading Terraform file from: {url}")
    response = requests.get(url)
    if response.status_code == 200:
        with open(output_path, "w") as f:
            f.write(response.text)
        print(f"✅ main.tf saved to: {output_path}")
        return True
    else:
        print(f"❌ Failed to download file (status code {response.status_code})")
        return False

def parse_checkly_resources(tf_path):
    """Parse Terraform file and extract Checkly resources"""
    resources = {
        'checks': [],
        'check_groups': [],
        'alert_channels': [],
        'dashboards': [],
        'maintenance_windows': []
    }

    try:
        with open(tf_path, "r") as f:
            parsed = hcl2.load(f)

        for block in parsed.get("resource", []):
            for resource_type, instances in block.items():
                for resource_name, config in instances.items():
                    if resource_type == "checkly_check":
                        resources['checks'].append({
                            'name': resource_name,
                            'display_name': config.get('name', resource_name),
                            'type': config.get('type', 'API'),
                            'group_id': config.get('group_id'),
                            'locations': config.get('locations', [])
                        })
                    elif resource_type == "checkly_check_group":
                        resources['check_groups'].append({
                            'name': resource_name,
                            'display_name': config.get('name', resource_name),
                            'locations': config.get('locations', [])
                        })
                    elif resource_type == "checkly_alert_channel":
                        resources['alert_channels'].append({
                            'name': resource_name,
                            'type': 'slack' if 'slack' in config else 'pagerduty' if 'pagerduty' in config else 'unknown'
                        })
                    elif resource_type == "checkly_dashboard":
                        resources['dashboards'].append({
                            'name': resource_name,
                            'custom_url': config.get('custom_url', ''),
                            'custom_domain': config.get('custom_domain', '')
                        })
                    elif resource_type == "checkly_maintenance_windows":
                        resources['maintenance_windows'].append({
                            'name': resource_name,
                            'display_name': config.get('name', resource_name)
                        })

    except Exception as e:
        print(f"❌ Error parsing Terraform file: {e}")
        return None

    return resources

def create_checkly_diagram(resources, output_path):
    """Create architecture diagram for Checkly infrastructure"""

    with Diagram("Checkly Monitoring Architecture", filename=output_path, direction="TB", show=False):
        # External services being monitored
        with Cluster("External Services"):
            target_api = Internet("Target API\n(danube-webshop)")

        # Checkly monitoring locations
        with Cluster("Checkly Monitoring Locations"):
            locations = []
            all_locations = set()

            # Collect all unique locations
            for check in resources['checks']:
                all_locations.update(check.get('locations', []))
            for group in resources['check_groups']:
                all_locations.update(group.get('locations', []))

            # Create location nodes
            for location in sorted(all_locations):
                locations.append(Subnet(f"Location\n{location}"))

        # Check groups and checks
        with Cluster("Monitoring Configuration"):
            # API Checks
            api_checks = []
            browser_checks = []

            for check in resources['checks']:
                if check['type'] == 'API':
                    api_checks.append(Prometheus(f"API Check\n{check['display_name']}"))
                elif check['type'] == 'BROWSER':
                    browser_checks.append(React(f"Browser Check\n{check['display_name']}"))

            # Check Groups
            groups = []
            for group in resources['check_groups']:
                groups.append(Rack(f"Group\n{group['display_name']}"))

        # Alert channels
        with Cluster("Alert Channels"):
            alert_nodes = []
            for channel in resources['alert_channels']:
                if channel['type'] == 'slack':
                    alert_nodes.append(Slack("Slack Notifications"))
                elif channel['type'] == 'pagerduty':
                    alert_nodes.append(Pagerduty("PagerDuty Alerts"))

        # Dashboard
        if resources['dashboards']:
            dashboard = Users("Public Dashboard")

        # Create connections
        # Locations monitor target API
        for location in locations:
            location >> Edge(label="monitors") >> target_api

        # Checks run from locations
        if locations:
            for check in api_checks + browser_checks:
                locations[0] >> check  # Simplified connection

        # Groups contain checks (simplified representation)
        if groups and (api_checks or browser_checks):
            for group in groups:
                if api_checks:
                    group >> api_checks[0]
                if browser_checks:
                    group >> browser_checks[0]

        # Alerts flow from checks
        if alert_nodes and (api_checks or browser_checks):
            all_checks = api_checks + browser_checks
            if all_checks:
                for alert in alert_nodes:
                    all_checks[0] >> Edge(label="alerts") >> alert

        # Dashboard shows results
        if resources['dashboards'] and (api_checks or browser_checks):
            all_checks = api_checks + browser_checks
            if all_checks:
                all_checks[0] >> Edge(label="displays") >> dashboard

def main():
    # Configuration
    RAW_URL = "https://raw.githubusercontent.com/checkly/terraform-sample-advanced/master/main.tf"
    OUTPUT_DIR = "/sample_data/out/checkly_diagram"  # Changed to use /tmp for better compatibility
    LOCAL_TF_PATH = os.path.join(OUTPUT_DIR, "main.tf")
    DIAGRAM_PATH = os.path.join(OUTPUT_DIR, "checkly_architecture")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Download Terraform file
    if not download_terraform_file(RAW_URL, LOCAL_TF_PATH):
        return

    # Step 2: Parse Checkly resources
    print("\n🔍 Parsing Checkly resources...")
    resources = parse_checkly_resources(LOCAL_TF_PATH)

    if not resources:
        print("❌ Failed to parse resources")
        return

    # Print summary
    print(f"📊 Found resources:")
    print(f"   - {len(resources['checks'])} checks")
    print(f"   - {len(resources['check_groups'])} check groups")
    print(f"   - {len(resources['alert_channels'])} alert channels")
    print(f"   - {len(resources['dashboards'])} dashboards")
    print(f"   - {len(resources['maintenance_windows'])} maintenance windows")

    # Step 3: Create architecture diagram
    print(f"\n🎨 Creating architecture diagram...")
    create_checkly_diagram(resources, DIAGRAM_PATH)
    print(f"✅ Architecture diagram saved to: {DIAGRAM_PATH}.png")

    # Show file locations
    print(f"\n📁 Output files:")
    print(f"   - Terraform file: {LOCAL_TF_PATH}")
    print(f"   - Diagram: {DIAGRAM_PATH}.png")

if __name__ == "__main__":
    main()

"""
⬇️ Downloading Terraform file from: https://raw.githubusercontent.com/checkly/terraform-sample-advanced/master/main.tf
✅ main.tf saved to: /sample_data/out/checkly_diagram/main.tf

🔍 Parsing Checkly resources...
📊 Found resources:
   - 7 checks
   - 3 check groups
   - 2 alert channels
   - 1 dashboards
   - 1 maintenance windows

🎨 Creating architecture diagram...
✅ Architecture diagram saved to: /sample_data/out/checkly_diagram/checkly_architecture.png

📁 Output files:
   - Terraform file: /sample_data/out/checkly_diagram/main.tf
   - Diagram: /sample_data/out/checkly_diagram/checkly_architecture.png
"""

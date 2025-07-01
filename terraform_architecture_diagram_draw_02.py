# !pip install diagrams requests python-hcl2

import os
import requests
import hcl2
from diagrams import Diagram, Cluster, Edge
from diagrams.generic.compute import Rack
from diagrams.generic.network import Subnet, Router
from diagrams.onprem.monitoring import Prometheus, Grafana
from diagrams.onprem.network import Internet
from diagrams.onprem.client import Users, User
from diagrams.programming.framework import React
from diagrams.saas.alerting import Pagerduty
from diagrams.saas.chat import Slack
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.database import Postgresql
from diagrams.aws.general import General
from diagrams.generic.blank import Blank
from collections import defaultdict

def download_terraform_file(url, output_path):
    """Download Terraform file from URL"""
    print(f"⬇️ Downloading Terraform file from: {url}")
    try:
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open(output_path, "w", encoding='utf-8') as f:
                f.write(response.text)
            print(f"✅ main.tf saved to: {output_path}")
            return True
        else:
            print(f"❌ Failed to download file (status code {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ Error downloading file: {e}")
        return False

def parse_checkly_resources(tf_path):
    """Parse Terraform file and extract Checkly resources with detailed information"""
    resources = {
        'checks': [],
        'check_groups': [],
        'alert_channels': [],
        'dashboards': [],
        'maintenance_windows': [],
        'triggers': [],
        'snippets': []
    }

    try:
        with open(tf_path, "r", encoding='utf-8') as f:
            content = f.read()
            
        # Parse HCL2 content
        parsed = hcl2.loads(content)
        
        # Debug: Print the structure to understand the format
        print("🔍 Analyzing Terraform structure...")
        
        # Extract resources
        if "resource" in parsed:
            for resource_block in parsed["resource"]:
                for resource_type, instances in resource_block.items():
                    for resource_name, config in instances.items():
                        print(f"   Found: {resource_type}.{resource_name}")
                        
                        if resource_type == "checkly_check":
                            check_info = {
                                'name': resource_name,
                                'display_name': config.get('name', resource_name),
                                'type': config.get('type', 'API'),
                                'group_id': config.get('group_id'),
                                'locations': config.get('locations', []),
                                'frequency': config.get('frequency', 300),
                                'activated': config.get('activated', True),
                                'should_fail': config.get('should_fail', False),
                                'runtime_id': config.get('runtime_id'),
                                'script': config.get('script', ''),
                                'request': config.get('request', {}),
                                'tags': config.get('tags', [])
                            }
                            resources['checks'].append(check_info)
                            
                        elif resource_type == "checkly_check_group":
                            group_info = {
                                'name': resource_name,
                                'display_name': config.get('name', resource_name),
                                'locations': config.get('locations', []),
                                'activated': config.get('activated', True),
                                'tags': config.get('tags', []),
                                'environment_variables': config.get('environment_variables', []),
                                'concurrency': config.get('concurrency', 1)
                            }
                            resources['check_groups'].append(group_info)
                            
                        elif resource_type == "checkly_alert_channel":
                            channel_info = {
                                'name': resource_name,
                                'type': 'unknown',
                                'config': config
                            }
                            
                            # Determine channel type based on configuration
                            if 'slack' in config:
                                channel_info['type'] = 'slack'
                                channel_info['webhook_url'] = config.get('slack', {}).get('webhook_url', '')
                            elif 'pagerduty' in config:
                                channel_info['type'] = 'pagerduty'
                                channel_info['account'] = config.get('pagerduty', {}).get('account', '')
                            elif 'email' in config:
                                channel_info['type'] = 'email'
                                channel_info['address'] = config.get('email', {}).get('address', '')
                            elif 'webhook' in config:
                                channel_info['type'] = 'webhook'
                                channel_info['url'] = config.get('webhook', {}).get('url', '')
                            elif 'sms' in config:
                                channel_info['type'] = 'sms'
                                channel_info['number'] = config.get('sms', {}).get('number', '')
                            
                            resources['alert_channels'].append(channel_info)
                            
                        elif resource_type == "checkly_dashboard":
                            dashboard_info = {
                                'name': resource_name,
                                'custom_url': config.get('custom_url', ''),
                                'custom_domain': config.get('custom_domain', ''),
                                'logo': config.get('logo', ''),
                                'header': config.get('header', ''),
                                'refresh_rate': config.get('refresh_rate', 60),
                                'paginate': config.get('paginate', True),
                                'pagination_rate': config.get('pagination_rate', 30),
                                'hide_tags': config.get('hide_tags', False)
                            }
                            resources['dashboards'].append(dashboard_info)
                            
                        elif resource_type == "checkly_maintenance_window":
                            mw_info = {
                                'name': resource_name,
                                'display_name': config.get('name', resource_name),
                                'starts_at': config.get('starts_at', ''),
                                'ends_at': config.get('ends_at', ''),
                                'repeat_unit': config.get('repeat_unit', ''),
                                'repeat_ends_at': config.get('repeat_ends_at', ''),
                                'tags': config.get('tags', [])
                            }
                            resources['maintenance_windows'].append(mw_info)
                            
                        elif resource_type == "checkly_trigger":
                            trigger_info = {
                                'name': resource_name,
                                'tags': config.get('tags', [])
                            }
                            resources['triggers'].append(trigger_info)
                            
                        elif resource_type == "checkly_snippet":
                            snippet_info = {
                                'name': resource_name,
                                'script': config.get('script', '')
                            }
                            resources['snippets'].append(snippet_info)

    except Exception as e:
        print(f"❌ Error parsing Terraform file: {e}")
        import traceback
        traceback.print_exc()
        return None

    return resources

def create_detailed_checkly_diagram(resources, output_path):
    """Create detailed architecture diagram for Checkly infrastructure"""
    
    with Diagram("Checkly Monitoring Architecture", filename=output_path, direction="TB", show=False):
        
        # 1. External Services/Targets
        with Cluster("Monitored Services"):
            # Analyze check requests to identify targets
            target_services = []
            unique_targets = set()
            
            for check in resources['checks']:
                request = check.get('request', {})
                if 'url' in request:
                    url = request['url']
                    if 'danube' in url.lower():
                        unique_targets.add("Danube Webshop")
                    elif 'api' in url.lower():
                        unique_targets.add("API Service")
                    else:
                        unique_targets.add("Web Service")
            
            if not unique_targets:
                unique_targets.add("Target Services")
            
            for target in sorted(unique_targets):
                target_services.append(Internet(target))
        
        # 2. Checkly Monitoring Locations
        with Cluster("Global Monitoring Locations"):
            location_nodes = []
            all_locations = set()
            
            # Collect all unique locations
            for check in resources['checks']:
                all_locations.update(check.get('locations', []))
            for group in resources['check_groups']:
                all_locations.update(group.get('locations', []))
            
            # Default locations if none specified
            if not all_locations:
                all_locations = {"us-east-1", "eu-west-1", "ap-southeast-1"}
            
            # Create location nodes (limit to prevent clutter)
            for location in sorted(list(all_locations)[:6]):
                location_nodes.append(Subnet(f"{location}\nMonitoring"))
        
        # 3. Check Groups and Organization
        check_group_nodes = []
        if resources['check_groups']:
            with Cluster("Check Groups"):
                for group in resources['check_groups']:
                    concurrency = group.get('concurrency', 1)
                    locations_count = len(group.get('locations', []))
                    group_label = f"{group['display_name']}\n({locations_count} locations)"
                    check_group_nodes.append(Rack(group_label))
        
        # 4. Individual Checks
        api_checks = []
        browser_checks = []
        
        with Cluster("Monitoring Checks"):
            # Categorize checks by type
            api_check_count = 0
            browser_check_count = 0
            
            for check in resources['checks']:
                check_type = check.get('type', 'API')
                frequency = check.get('frequency', 300)
                activated = check.get('activated', True)
                
                status_indicator = "✅" if activated else "⏸️"
                check_label = f"{status_indicator} {check['display_name']}\n({frequency}s interval)"
                
                if check_type == 'API':
                    api_checks.append(Prometheus(check_label))
                    api_check_count += 1
                elif check_type == 'BROWSER':
                    browser_checks.append(React(check_label))
                    browser_check_count += 1
                else:
                    api_checks.append(General(check_label))
                    api_check_count += 1
            
            # Create summary nodes if too many checks
            if api_check_count > 5:
                api_checks = [Prometheus(f"API Checks\n({api_check_count} total)")]
            if browser_check_count > 5:
                browser_checks = [React(f"Browser Checks\n({browser_check_count} total)")]
        
        # 5. Alert Channels
        alert_channel_nodes = []
        if resources['alert_channels']:
            with Cluster("Alert Channels"):
                channel_types = defaultdict(int)
                
                for channel in resources['alert_channels']:
                    channel_type = channel.get('type', 'unknown')
                    channel_types[channel_type] += 1
                
                # Create nodes for each channel type
                for channel_type, count in channel_types.items():
                    if channel_type == 'slack':
                        label = f"Slack\n({count} channels)" if count > 1 else "Slack"
                        alert_channel_nodes.append(Slack(label))
                    elif channel_type == 'pagerduty':
                        label = f"PagerDuty\n({count} channels)" if count > 1 else "PagerDuty"
                        alert_channel_nodes.append(Pagerduty(label))
                    elif channel_type == 'email':
                        label = f"Email\n({count} channels)" if count > 1 else "Email"
                        alert_channel_nodes.append(User(label))
                    elif channel_type == 'webhook':
                        label = f"Webhook\n({count} channels)" if count > 1 else "Webhook"
                        alert_channel_nodes.append(Router(label))
                    elif channel_type == 'sms':
                        label = f"SMS\n({count} channels)" if count > 1 else "SMS"
                        alert_channel_nodes.append(User(label))
                    else:
                        alert_channel_nodes.append(General(f"Alert Channel\n({channel_type})"))
        
        # 6. Dashboards
        dashboard_nodes = []
        if resources['dashboards']:
            with Cluster("Public Dashboards"):
                for dashboard in resources['dashboards']:
                    refresh_rate = dashboard.get('refresh_rate', 60)
                    custom_domain = dashboard.get('custom_domain', '')
                    
                    if custom_domain:
                        label = f"Dashboard\n{custom_domain}\n({refresh_rate}s refresh)"
                    else:
                        label = f"Public Dashboard\n({refresh_rate}s refresh)"
                    
                    dashboard_nodes.append(Grafana(label))
        
        # 7. Maintenance Windows & Triggers
        maintenance_nodes = []
        if resources['maintenance_windows']:
            with Cluster("Maintenance & Control"):
                for mw in resources['maintenance_windows']:
                    repeat_unit = mw.get('repeat_unit', '')
                    label = f"Maintenance Window\n({repeat_unit})" if repeat_unit else "Maintenance Window"
                    maintenance_nodes.append(General(label))
                
                if resources['triggers']:
                    maintenance_nodes.append(General(f"Triggers\n({len(resources['triggers'])})"))
        
        # 8. Code Snippets
        if resources['snippets']:
            snippet_node = General(f"Reusable Snippets\n({len(resources['snippets'])})")
        
        # Create Connections
        all_checks = api_checks + browser_checks
        
        # 1. Locations monitor target services
        if location_nodes and target_services:
            for location in location_nodes:
                for target in target_services:
                    location >> Edge(label="monitors", style="dashed") >> target
        
        # 2. Check groups coordinate checks
        if check_group_nodes and all_checks:
            for group in check_group_nodes:
                for check in all_checks[:2]:  # Connect to first few checks to avoid clutter
                    group >> Edge(label="contains") >> check
        
        # 3. Checks run from locations
        if location_nodes and all_checks:
            for location in location_nodes[:2]:  # Connect first few locations
                for check in all_checks:
                    location >> Edge(label="executes", style="dotted") >> check
        
        # 4. Failed checks trigger alerts
        if all_checks and alert_channel_nodes:
            for check in all_checks:
                for alert in alert_channel_nodes:
                    check >> Edge(label="alerts on failure", color="red") >> alert
        
        # 5. Results displayed on dashboards
        if all_checks and dashboard_nodes:
            for check in all_checks:
                for dashboard in dashboard_nodes:
                    check >> Edge(label="displays results", color="blue") >> dashboard
        
        # 6. Maintenance windows affect checks
        if maintenance_nodes and all_checks:
            for mw in maintenance_nodes:
                for check in all_checks[:2]:  # Connect to first few checks
                    mw >> Edge(label="suspends", style="dashed", color="orange") >> check
        
        # 7. Snippets used by checks
        if resources['snippets'] and all_checks:
            for check in all_checks:
                snippet_node >> Edge(label="provides code", style="dotted") >> check

def main():
    # Configuration
    RAW_URL = "https://raw.githubusercontent.com/checkly/terraform-sample-advanced/master/main.tf"
    
    OUTPUT_DIR = "/sample_data/out/checkly_diagram"
    LOCAL_TF_PATH = os.path.join(OUTPUT_DIR, "main.tf")
    DIAGRAM_PATH = os.path.join(OUTPUT_DIR, "checkly_architecture")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Step 1: Download Terraform file
    if not download_terraform_file(RAW_URL, LOCAL_TF_PATH):
        print("❌ Failed to download Terraform file")
        return

    # Step 2: Parse Checkly resources
    print("\n🔍 Parsing Checkly resources...")
    resources = parse_checkly_resources(LOCAL_TF_PATH)

    if not resources:
        print("❌ Failed to parse resources")
        return

    # Print detailed summary
    print(f"\n📊 Detailed Resource Summary:")
    print(f"   📋 Checks: {len(resources['checks'])}")
    for check in resources['checks']:
        status = "✅" if check.get('activated', True) else "⏸️"
        print(f"      {status} {check['display_name']} ({check['type']}, {check.get('frequency', 300)}s)")
    
    print(f"   📁 Check Groups: {len(resources['check_groups'])}")
    for group in resources['check_groups']:
        locations = len(group.get('locations', []))
        print(f"      📁 {group['display_name']} ({locations} locations)")
    
    print(f"   🚨 Alert Channels: {len(resources['alert_channels'])}")
    for channel in resources['alert_channels']:
        print(f"      🚨 {channel['name']} ({channel['type']})")
    
    print(f"   📊 Dashboards: {len(resources['dashboards'])}")
    for dashboard in resources['dashboards']:
        domain = dashboard.get('custom_domain', 'default')
        print(f"      📊 {dashboard['name']} ({domain})")
    
    print(f"   🔧 Maintenance Windows: {len(resources['maintenance_windows'])}")
    print(f"   ⚡ Triggers: {len(resources['triggers'])}")
    print(f"   📝 Snippets: {len(resources['snippets'])}")

    # Step 3: Create detailed architecture diagram
    print(f"\n🎨 Creating detailed architecture diagram...")
    create_detailed_checkly_diagram(resources, DIAGRAM_PATH)
    print(f"✅ Architecture diagram saved to: {DIAGRAM_PATH}.png")

    # Show file locations
    print(f"\n📁 Output files:")
    print(f"   - Terraform file: {LOCAL_TF_PATH}")
    print(f"   - Architecture diagram: {DIAGRAM_PATH}.png")
    
    print(f"\n🎯 Diagram includes:")
    print(f"   - Monitoring locations and target services")
    print(f"   - Check groups and individual checks with details")
    print(f"   - Alert channels by type")
    print(f"   - Public dashboards with configuration")
    print(f"   - Maintenance windows and triggers")
    print(f"   - Logical connections showing monitoring flow")

if __name__ == "__main__":
    main()

""" incomplete [debug in progress]
Installing collected packages: lark, python-hcl2
Successfully installed lark-1.2.2 python-hcl2-7.2.1
⬇️ Downloading Terraform file from: https://raw.githubusercontent.com/checkly/terraform-sample-advanced/master/main.tf
✅ main.tf saved to: /sample_data/out/checkly_diagram/main.tf

🔍 Parsing Checkly resources...
🔍 Analyzing Terraform structure...
   Found: checkly_check.get-users
   Found: checkly_check.post-user
   Found: checkly_check_group.users-api
   Found: checkly_check.create-order
   Found: checkly_check.update-order
   Found: checkly_check.cancel-order
   Found: checkly_check.add-to-wishlist
   Found: checkly_check_group.orders-api
   Found: checkly_alert_channel.pagerduty_ac
❌ Error parsing Terraform file: 'list' object has no attribute 'get'
❌ Failed to parse resources
Traceback (most recent call last):
  File "/tmp/ipython-input-16-1698360909.py", line 109, in parse_checkly_resources
    channel_info['account'] = config.get('pagerduty', {}).get('account', '')
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'list' object has no attribute 'get'
"""
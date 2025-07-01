#!pip install python-hcl2 diagrams requests

import os
import re
import requests
import json
from io import StringIO
try:
    import hcl2
    HCL2_AVAILABLE = True
except ImportError:
    HCL2_AVAILABLE = False
    print("⚠️ hcl2 library not available, using regex parsing only")

from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, ECS, Lambda, AutoScaling
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.network import ELB, ALB, NLB, Route53, CloudFront, VPC, PrivateSubnet
from diagrams.aws.security import WAF, IAM, Cognito
from diagrams.aws.storage import S3, EBS, EFS
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.management import Cloudwatch
from diagrams.aws.general import General
from diagrams.k8s.compute import Pod, Deployment
from diagrams.k8s.network import Service, Ingress
from diagrams.generic.compute import Rack
from diagrams.onprem.database import PostgreSQL, MySQL
from diagrams.onprem.inmemory import Redis

# Config
RAW_URL = "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/refs/heads/main/07-managing-multiple-environments/file-structure/production/main.tf"
RAW_URL = "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/refs/heads/main/04-variables-and-outputs/web-app/main.tf""

TARGET_DIR = "/content/sample_data/out/checkly_diagram"
TF_FILE = os.path.join(TARGET_DIR, "main.tf")

def download_main_tf_from_url(url, save_path):
    """Download Terraform file from URL"""
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    print(f"⬇️ Downloading Terraform file from:\n   {url}")
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"❌ Failed to download file: {r.status_code}")
    with open(save_path, "w") as f:
        f.write(r.text)
    print(f"✅ Saved to: {save_path}")
    return r.text

def parse_terraform_file(tf_file_path):
    """Parse Terraform file with multiple parsing strategies"""
    resources = {}
    
    try:
        with open(tf_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📄 File content preview (first 500 chars):")
        print(content[:500] + "..." if len(content) > 500 else content)
        print()
        
        if HCL2_AVAILABLE:
            print("🔍 Attempting HCL2 parsing...")
            try:
                with open(tf_file_path, 'r') as f:
                    parsed = hcl2.load(f)
                
                print("✅ HCL2 parsing successful!")
                print(f"Parsed keys: {list(parsed.keys())}")
                
                # Extract resources from parsed HCL
                if 'resource' in parsed:
                    for resource_block in parsed['resource']:
                        for resource_type, instances in resource_block.items():
                            if resource_type not in resources:
                                resources[resource_type] = []
                            for instance_name, config in instances.items():
                                resources[resource_type].append({
                                    'name': instance_name,
                                    'config': config
                                })
                                
            except Exception as hcl_err:
                print(f"⚠️ HCL2 parsing failed: {hcl_err}")
                print("🔄 Falling back to regex parsing...")
                resources = parse_with_regex(content)
        else:
            print("🔄 Using regex parsing (HCL2 not available)...")
            resources = parse_with_regex(content)
            
    except Exception as e:
        print(f"❌ Error reading file: {e}")
    
    return resources

def parse_with_regex(content):
    """Enhanced regex parsing for Terraform files"""
    print("🔍 Using enhanced regex parsing...")
    resources = {}
    
    # Improved regex patterns with better matching
    patterns = [
        # Standard resource block: resource "type" "name" {
        (r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{', 'resource'),
        # Module block: module "name" {
        (r'module\s+"([^"]+)"\s*\{([^}]*source\s*=\s*"([^"]+)"[^}]*)\}', 'module'),
        # Data source: data "type" "name" {
        (r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{', 'data'),
        # Variable: variable "name" {
        (r'variable\s+"([^"]+)"\s*\{', 'variable'),
        # Output: output "name" {
        (r'output\s+"([^"]+)"\s*\{', 'output'),
        # Provider: provider "name" {
        (r'provider\s+"([^"]+)"\s*\{', 'provider'),
    ]
    
    total_matches = 0
    
    for pattern, block_type in patterns:
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        print(f"   {block_type.title()}: {len(matches)} matches")
        
        for match in matches:
            if block_type == 'module':
                # Special handling for modules - extract source info
                if isinstance(match, tuple) and len(match) >= 3:
                    name = match[0]
                    source = match[2] if len(match) > 2 else "unknown"
                    resource_type = f"module_{source.split('/')[-1]}" if '/' in source else f"module_{name}"
                else:
                    name = match if isinstance(match, str) else match[0]
                    resource_type = f"module_{name}"
            elif block_type in ['variable', 'output', 'provider']:
                # Single name blocks
                name = match if isinstance(match, str) else match[0]
                resource_type = block_type
            else:
                # Resource and data blocks
                if isinstance(match, tuple) and len(match) >= 2:
                    resource_type, name = match[0], match[1]
                    if block_type == 'data':
                        resource_type = f"data_{resource_type}"
                else:
                    continue
            
            if resource_type not in resources:
                resources[resource_type] = []
            resources[resource_type].append({
                'name': name,
                'config': {},
                'type': block_type
            })
            total_matches += 1
    
    print(f"✅ Enhanced regex parsing found {total_matches} total items")
    
    if total_matches == 0:
        print("🔍 Analyzing file structure for debugging...")
        lines = content.split('\n')
        print(f"   Total lines: {len(lines)}")
        
        # Show lines that might contain terraform blocks
        terraform_lines = []
        for i, line in enumerate(lines, 1):
            line_clean = line.strip()
            if any(keyword in line_clean.lower() for keyword in ['resource', 'module', 'data', 'variable', 'output']):
                terraform_lines.append(f"   Line {i}: {line_clean}")
        
        if terraform_lines:
            print("   Potential Terraform blocks found:")
            for line in terraform_lines[:10]:  # Show first 10
                print(line)
    
    return resources

def get_resource_mapping():
    """Get comprehensive resource to diagram component mapping"""
    return {
        # AWS Compute
        'aws_instance': (EC2, 'compute'),
        'aws_lambda_function': (Lambda, 'compute'),
        'aws_ecs_service': (ECS, 'compute'),
        'aws_ecs_cluster': (ECS, 'compute'),
        'aws_autoscaling_group': (AutoScaling, 'compute'),
        'aws_launch_configuration': (AutoScaling, 'compute'),
        'aws_launch_template': (AutoScaling, 'compute'),
        
        # AWS Database
        'aws_db_instance': (RDS, 'database'),
        'aws_rds_cluster': (RDS, 'database'),
        'aws_dynamodb_table': (Dynamodb, 'database'),
        'aws_elasticache_cluster': (ElastiCache, 'database'),
        'aws_elasticache_replication_group': (ElastiCache, 'database'),
        'aws_redshift_cluster': (Redshift, 'database'),
        
        # AWS Network
        'aws_lb': (ALB, 'network'),
        'aws_alb': (ALB, 'network'),
        'aws_elb': (ELB, 'network'),
        'aws_lb_target_group': (ALB, 'network'),
        'aws_route53_record': (Route53, 'network'),
        'aws_route53_zone': (Route53, 'network'),
        'aws_cloudfront_distribution': (CloudFront, 'network'),
        'aws_vpc': (VPC, 'network'),
        'aws_subnet': (PrivateSubnet, 'network'),
        'aws_internet_gateway': (VPC, 'network'),
        'aws_nat_gateway': (VPC, 'network'),
        'aws_route_table': (VPC, 'network'),
        
        # AWS Storage
        'aws_s3_bucket': (S3, 'storage'),
        'aws_ebs_volume': (EBS, 'storage'),
        'aws_efs_file_system': (EFS, 'storage'),
        
        # AWS Security
        'aws_security_group': (WAF, 'security'),
        'aws_waf_web_acl': (WAF, 'security'),
        'aws_iam_role': (IAM, 'security'),
        'aws_iam_policy': (IAM, 'security'),
        'aws_iam_user': (IAM, 'security'),
        'aws_cognito_user_pool': (Cognito, 'security'),
        
        # AWS Integration
        'aws_sqs_queue': (SQS, 'integration'),
        'aws_sns_topic': (SNS, 'integration'),
        'aws_cloudwatch_log_group': (Cloudwatch, 'monitoring'),
        'aws_cloudwatch_metric_alarm': (Cloudwatch, 'monitoring'),
        
        # Modules (common patterns)
        'module_vpc': (VPC, 'network'),
        'module_web_app': (General, 'application'),
        'module_database': (RDS, 'database'),
        'module_security': (WAF, 'security'),
        
        # Generic fallbacks
        'variable': (General, 'config'),
        'output': (General, 'config'),
        'provider': (General, 'config'),
    }

def create_diagram_data(resources):
    """Prepare diagram data structure without creating components yet"""
    mapping = get_resource_mapping()
    
    diagram_data = {
        'compute': [],
        'database': [],
        'network': [],
        'storage': [],
        'security': [],
        'integration': [],
        'monitoring': [],
        'application': [],
        'config': [],
    }
    
    for resource_type, instances in resources.items():
        for instance in instances:
            # Create a clean label
            label = f"{resource_type.replace('aws_', '').replace('_', ' ').title()}\n{instance['name']}"
            
            if resource_type in mapping:
                comp_class, category = mapping[resource_type]
            else:
                # Try partial matching for unknown resources
                comp_class, category = General, 'application'
                for known_type in mapping:
                    if known_type in resource_type or resource_type in known_type:
                        comp_class, category = mapping[known_type]
                        break
                
                # If still unknown, categorize by common patterns
                if 'database' in resource_type or 'db_' in resource_type:
                    category = 'database'
                elif 'network' in resource_type or 'vpc' in resource_type or 'subnet' in resource_type:
                    category = 'network'
                elif 'compute' in resource_type or 'instance' in resource_type:
                    category = 'compute'
                elif 'storage' in resource_type or 's3' in resource_type:
                    category = 'storage'
                elif 'security' in resource_type or 'iam' in resource_type:
                    category = 'security'
            
            diagram_data[category].append({
                'class': comp_class,
                'label': label,
                'resource_type': resource_type,
                'name': instance['name']
            })
    
    return diagram_data

def create_diagram(diagram_data, out_path, title="Terraform Architecture"):
    """Create the architecture diagram with proper context management"""
    # Filter out empty categories
    non_empty_data = {k: v for k, v in diagram_data.items() if v}
    
    if not non_empty_data:
        print("⚠️ No components to diagram")
        with Diagram(title, filename=out_path, direction="TB", show=False):
            General("No Resources Found")
        return
    
    print(f"🎨 Creating diagram with {sum(len(v) for v in non_empty_data.values())} components")
    
    with Diagram(title, filename=out_path, direction="TB", show=False):
        created_components = {}
        
        # Create components grouped by category
        for category, items in non_empty_data.items():
            if not items:
                continue
                
            print(f"   Creating {len(items)} {category} components")
            
            if len(items) > 1:
                # Multiple components - use cluster
                with Cluster(f"{category.title()} Layer"):
                    components = []
                    for item in items:
                        comp = item['class'](item['label'])
                        components.append(comp)
                    created_components[category] = components
            else:
                # Single component - no cluster needed
                comp = items[0]['class'](items[0]['label'])
                created_components[category] = [comp]
        
        # Create logical connections between layers
        create_connections(created_components)

def create_connections(component_layers):
    """Create logical connections between component layers"""
    # Define connection patterns (source -> target)
    connection_patterns = [
        ('network', 'security'),     # Load balancer -> Security groups
        ('security', 'compute'),     # Security -> Compute instances
        ('network', 'compute'),      # Direct network -> compute
        ('compute', 'database'),     # Compute -> Database
        ('compute', 'storage'),      # Compute -> Storage
        ('integration', 'compute'),  # Queues/Topics -> Compute
        ('network', 'integration'),  # Network -> Integration services
        ('monitoring', 'compute'),   # Monitoring -> Compute
        ('application', 'compute'),  # Application modules -> Compute
    ]
    
    connections_made = 0
    for source_category, target_category in connection_patterns:
        if source_category in component_layers and target_category in component_layers:
            source_components = component_layers[source_category]
            target_components = component_layers[target_category]
            
            # Connect first component of each layer (simplified approach)
            if source_components and target_components:
                try:
                    source_components[0] >> target_components[0]
                    connections_made += 1
                except Exception as e:
                    print(f"   ⚠️ Connection failed {source_category} -> {target_category}: {e}")
    
    print(f"   Created {connections_made} connections between layers")

def try_alternative_files():
    """Try alternative Terraform files if main file has no resources"""
    alternative_urls = [
        "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/main/03-basics/web-app/main.tf",
        "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/main/04-variables-and-outputs/web-app/main.tf",
        "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/main/06-organization-and-modules/web-app-module/main.tf",
        "https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/main/05-backends-and-workspaces/web-app/main.tf"
    ]
    
    for i, alt_url in enumerate(alternative_urls):
        try:
            print(f"\n🔄 Trying alternative file {i+1}: {alt_url.split('/')[-2:]}")
            response = requests.get(alt_url)
            if response.status_code != 200:
                print(f"   ❌ HTTP {response.status_code}")
                continue
                
            alt_content = response.text
            print(f"   📏 Size: {len(alt_content)} chars, {len(alt_content.splitlines())} lines")
            
            # Quick check for terraform content
            if any(keyword in alt_content.lower() for keyword in ['resource "', 'module "', 'provider "']):
                alt_file = TF_FILE.replace("main.tf", f"alt_{i}.tf")
                with open(alt_file, 'w') as f:
                    f.write(alt_content)
                
                alt_resources = parse_terraform_file(alt_file)
                if alt_resources and any(len(instances) > 0 for instances in alt_resources.values()):
                    print(f"   ✅ Found {sum(len(instances) for instances in alt_resources.values())} resources!")
                    return alt_resources, alt_file
                else:
                    print(f"   ⚠️ No parseable resources found")
            else:
                print(f"   ⚠️ No terraform syntax detected")
                
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            continue
    
    return None, None

def main():
    """Main execution function"""
    print("🚀 Starting Enhanced Terraform Diagram Generator")
    
    # Download the Terraform file
    content = download_main_tf_from_url(RAW_URL, TF_FILE)
    
    print(f"\n📋 Downloaded file info:")
    print(f"   Size: {len(content)} characters")
    print(f"   Lines: {len(content.splitlines())}")
    
    # Parse the Terraform file
    print(f"\n🔍 Parsing Terraform file: {TF_FILE}")
    resources = parse_terraform_file(TF_FILE)
    
    # Check if we found meaningful resources (not just config)
    meaningful_resources = {k: v for k, v in resources.items() 
                          if k not in ['variable', 'output', 'provider'] and v}
    
    if not meaningful_resources:
        print("⚠️ No infrastructure resources found in primary file")
        print("🔄 Trying alternative files...")
        
        alt_resources, alt_file = try_alternative_files()
        if alt_resources:
            resources = alt_resources
            print(f"✅ Using alternative file: {alt_file}")
        else:
            print("❌ No suitable Terraform files found with infrastructure resources")
            return
    
    # Print summary of found resources
    total_resources = sum(len(instances) for instances in resources.values())
    print(f"\n📊 Found {total_resources} resources across {len(resources)} types:")
    for resource_type, instances in resources.items():
        print(f"   - {len(instances):2d} {resource_type}")
    
    # Prepare diagram data
    diagram_data = create_diagram_data(resources)
    
    # Show what will be diagrammed
    meaningful_categories = {k: v for k, v in diagram_data.items() if v}
    if meaningful_categories:
        print(f"\n🏗️ Diagram will include:")
        for category, items in meaningful_categories.items():
            print(f"   - {len(items):2d} {category} components")
    
    # Create the diagram
    diagram_path = os.path.join(TARGET_DIR, "terraform_architecture")
    print(f"\n🎨 Creating architecture diagram: {diagram_path}.png")
    
    try:
        create_diagram(diagram_data, diagram_path, "Terraform Infrastructure Architecture")
        print(f"✅ Diagram generation complete!")
        print(f"📁 Diagram saved at: {diagram_path}.png")
    except Exception as e:
        print(f"❌ Diagram creation failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # List output directory contents
    if os.path.exists(TARGET_DIR):
        print(f"\n📂 Output directory contents:")
        for item in sorted(os.listdir(TARGET_DIR)):
            item_path = os.path.join(TARGET_DIR, item)
            if os.path.isfile(item_path):
                size = os.path.getsize(item_path)
                print(f"   📄 {item} ({size:,} bytes)")
            else:
                print(f"   📁 {item}/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()

"""
🚀 Starting Enhanced Terraform Diagram Generator
⬇️ Downloading Terraform file from:
   https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/refs/heads/main/07-managing-multiple-environments/file-structure/production/main.tf
✅ Saved to: /content/sample_data/out/checkly_diagram/main.tf

📋 Downloaded file info:
   Size: 1097 characters
   Lines: 46

🔍 Parsing Terraform file: /content/sample_data/out/checkly_diagram/main.tf
📄 File content preview (first 500 chars):
terraform {
  # Assumes s3 bucket and dynamo DB table already set up
  # See /code/03-basics/aws-backend
  backend "s3" {
    bucket         = "devops-directive-tf-state"
    key            = "07-managing-multiple-environments/production/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-locking"
    encrypt        = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region =...

🔍 Attempting HCL2 parsing...
⚠️ HCL2 parsing failed: module 'hcl2' has no attribute 'load'
🔄 Falling back to regex parsing...
🔍 Using enhanced regex parsing...
   Resource: 0 matches
   Module: 1 matches
   Data: 0 matches
   Variable: 1 matches
   Output: 0 matches
   Provider: 1 matches
✅ Enhanced regex parsing found 3 total items

📊 Found 3 resources across 3 types:
   -  1 module_web-app-module
   -  1 variable
   -  1 provider

🏗️ Diagram will include:
   -  1 application components
   -  2 config components

🎨 Creating architecture diagram: /content/sample_data/out/checkly_diagram/terraform_architecture.png
🎨 Creating diagram with 3 components
   Creating 1 application components
   Creating 2 config components
   Created 0 connections between layers
✅ Diagram generation complete!
📁 Diagram saved at: /content/sample_data/out/checkly_diagram/terraform_architecture.png

📂 Output directory contents:
   📁 .ipynb_checkpoints/
   📄 main.tf (1,097 bytes)
   📄 terraform_architecture.png (29,205 bytes)
"""     
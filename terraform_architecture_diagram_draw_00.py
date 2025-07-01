#!pip install gitpython diagrams python-hcl2

import os
import re
from git import Repo
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2, Lambda, ECS, AutoScaling
from diagrams.aws.database import RDS, Dynamodb, ElastiCache
from diagrams.aws.network import ELB, ALB, NLB, Route53, VPC, PrivateSubnet, PublicSubnet, InternetGateway, NATGateway
from diagrams.aws.security import WAF, IAM
from diagrams.aws.storage import S3
#from diagrams.aws.analytics import CloudwatchLogs
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.general import General
from collections import defaultdict
import json

# Try to import hcl2, fallback to regex parsing if not available
try:
    import hcl2
    HCL2_AVAILABLE = True
except ImportError:
    HCL2_AVAILABLE = False
    print("⚠️  hcl2 not available, using regex parsing")

# Constants
REPO_URL = "https://github.com/sidpalas/devops-directive-terraform-course.git"
CLONE_DIR = os.path.expanduser("sample_data/out/devops-directive-terraform-course")
OUTPUT_DIR = "/sample_data"

# Resource type to diagram component mapping
RESOURCE_MAPPING = {
    # Compute
    'aws_instance': EC2,
    'aws_launch_template': EC2,
    'aws_launch_configuration': EC2,
    'aws_autoscaling_group': AutoScaling,
    'aws_lambda_function': Lambda,
    'aws_ecs_service': ECS,
    'aws_ecs_cluster': ECS,
    
    # Database
    'aws_db_instance': RDS,
    'aws_rds_cluster': RDS,
    'aws_dynamodb_table': Dynamodb,
    'aws_elasticache_cluster': ElastiCache,
    
    # Network
    'aws_lb': ALB,
    'aws_alb': ALB,
    'aws_elb': ELB,
    'aws_lb_target_group': ALB,
    'aws_route53_record': Route53,
    'aws_route53_zone': Route53,
    'aws_vpc': VPC,
    'aws_internet_gateway': InternetGateway,
    'aws_nat_gateway': NATGateway,
    
    # Security
    'aws_wafv2_web_acl': WAF,
    'aws_waf_web_acl': WAF,
    #'aws_security_group': SecurityGroup,
    'aws_iam_role': IAM,
    'aws_iam_policy': IAM,
    
    # Storage
    'aws_s3_bucket': S3,
    
    # Monitoring
    #'aws_cloudwatch_log_group': CloudwatchLogs,
    
    # Integration
    'aws_sqs_queue': SQS,
    'aws_sns_topic': SNS,
}

def parse_terraform_file_hcl2(file_path):
    """Parse Terraform file using hcl2 library"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            parsed = hcl2.load(file)
        
        resources = []
        if 'resource' in parsed:
            for resource_type, resource_instances in parsed['resource'].items():
                for resource_name, resource_config in resource_instances.items():
                    resources.append({
                        'type': resource_type,
                        'name': resource_name,
                        'config': resource_config
                    })
        return resources
    except Exception as e:
        print(f"Error parsing {file_path} with hcl2: {e}")
        return []

def parse_terraform_file_regex(file_path):
    """Parse Terraform file using regex patterns"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Remove comments
        content = re.sub(r'#.*$', '', content, flags=re.MULTILINE)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Find resource blocks
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        resources = []
        
        for match in re.finditer(resource_pattern, content):
            resource_type = match.group(1)
            resource_name = match.group(2)
            resources.append({
                'type': resource_type,
                'name': resource_name,
                'config': {}
            })
        
        return resources
    except Exception as e:
        print(f"Error parsing {file_path} with regex: {e}")
        return []

def parse_terraform_file(file_path):
    """Parse Terraform file using available method"""
    if HCL2_AVAILABLE:
        resources = parse_terraform_file_hcl2(file_path)
        if resources:  # If hcl2 parsing successful
            return resources
    
    # Fallback to regex parsing
    return parse_terraform_file_regex(file_path)

def categorize_resources(resources):
    """Categorize resources by their function"""
    categories = {
        'networking': [],
        'compute': [],
        'database': [],
        'security': [],
        'storage': [],
        'monitoring': [],
        'integration': [],
        'other': []
    }
    
    category_map = {
        'aws_vpc': 'networking',
        'aws_subnet': 'networking', 
        'aws_internet_gateway': 'networking',
        'aws_nat_gateway': 'networking',
        'aws_route_table': 'networking',
        'aws_security_group': 'networking',
        
        'aws_instance': 'compute',
        'aws_launch_template': 'compute',
        'aws_autoscaling_group': 'compute',
        'aws_lambda_function': 'compute',
        'aws_ecs_service': 'compute',
        'aws_ecs_cluster': 'compute',
        
        'aws_lb': 'networking',
        'aws_alb': 'networking',
        'aws_elb': 'networking',
        'aws_lb_target_group': 'networking',
        
        'aws_db_instance': 'database',
        'aws_rds_cluster': 'database',
        'aws_dynamodb_table': 'database',
        'aws_elasticache_cluster': 'database',
        
        'aws_wafv2_web_acl': 'security',
        'aws_waf_web_acl': 'security',
        'aws_iam_role': 'security',
        'aws_iam_policy': 'security',
        
        'aws_s3_bucket': 'storage',
        
        'aws_cloudwatch_log_group': 'monitoring',
        
        'aws_sqs_queue': 'integration',
        'aws_sns_topic': 'integration',
    }
    
    for resource in resources:
        category = category_map.get(resource['type'], 'other')
        categories[category].append(resource)
    
    return categories

def create_diagram_components(categories, diagram_title):
    """Create diagram components based on categorized resources"""
    components = {}
    
    # Create networking components
    if categories['networking']:
        load_balancers = [r for r in categories['networking'] if r['type'] in ['aws_lb', 'aws_alb', 'aws_elb']]
        if load_balancers:
            if len(load_balancers) == 1:
                lb_type = load_balancers[0]['type']
                if lb_type in ['aws_lb', 'aws_alb']:
                    components['load_balancer'] = ALB(f"Load Balancer ({load_balancers[0]['name']})")
                else:
                    components['load_balancer'] = ELB(f"Load Balancer ({load_balancers[0]['name']})")
            else:
                components['load_balancer'] = [ALB(f"LB-{i+1}") for i in range(len(load_balancers))]
        
        route53_resources = [r for r in categories['networking'] if r['type'] in ['aws_route53_record', 'aws_route53_zone']]
        if route53_resources:
            components['dns'] = Route53("DNS")
    
    # Create compute components
    if categories['compute']:
        ec2_instances = [r for r in categories['compute'] if r['type'] in ['aws_instance', 'aws_launch_template']]
        lambda_functions = [r for r in categories['compute'] if r['type'] == 'aws_lambda_function']
        ecs_services = [r for r in categories['compute'] if r['type'] in ['aws_ecs_service', 'aws_ecs_cluster']]
        asg_resources = [r for r in categories['compute'] if r['type'] == 'aws_autoscaling_group']
        
        if ec2_instances:
            if len(ec2_instances) == 1:
                components['compute'] = EC2(f"EC2 ({ec2_instances[0]['name']})")
            else:
                components['compute'] = [EC2(f"EC2-{i+1}") for i in range(min(len(ec2_instances), 3))]
        
        if lambda_functions:
            if len(lambda_functions) == 1:
                components['lambda'] = Lambda(f"Lambda ({lambda_functions[0]['name']})")
            else:
                components['lambda'] = [Lambda(f"Lambda-{i+1}") for i in range(min(len(lambda_functions), 3))]
        
        if ecs_services:
            components['ecs'] = ECS("ECS Service")
        
        if asg_resources:
            components['asg'] = AutoScaling("Auto Scaling Group")
    
    # Create database components
    if categories['database']:
        rds_instances = [r for r in categories['database'] if r['type'] in ['aws_db_instance', 'aws_rds_cluster']]
        dynamodb_tables = [r for r in categories['database'] if r['type'] == 'aws_dynamodb_table']
        
        if rds_instances:
            components['rds'] = RDS(f"RDS ({rds_instances[0]['name']})")
        
        if dynamodb_tables:
            components['dynamodb'] = Dynamodb(f"DynamoDB ({dynamodb_tables[0]['name']})")
    
    # Create security components
    if categories['security']:
        waf_resources = [r for r in categories['security'] if r['type'] in ['aws_wafv2_web_acl', 'aws_waf_web_acl']]
        if waf_resources:
            components['waf'] = WAF("WAF")
    
    # Create storage components
    if categories['storage']:
        s3_buckets = [r for r in categories['storage'] if r['type'] == 'aws_s3_bucket']
        if s3_buckets:
            if len(s3_buckets) == 1:
                components['s3'] = S3(f"S3 ({s3_buckets[0]['name']})")
            else:
                components['s3'] = S3(f"S3 Buckets ({len(s3_buckets)})")
    
    return components

def generate_architecture_diagram(tf_file, resources):
    """Generate architecture diagram for a specific Terraform file"""
    if not resources:
        print(f"No resources found in {tf_file}")
        return
    
    output_dir = os.path.dirname(tf_file)
    diagram_filename = os.path.join(output_dir, "architecture")
    
    # Get relative path for diagram title
    rel_path = os.path.relpath(tf_file, CLONE_DIR)
    diagram_title = f"Architecture: {os.path.dirname(rel_path)}"
    
    print(f"📌 Generating architecture for: {tf_file}")
    print(f"   Found resources: {[r['type'] for r in resources]}")
    
    # Categorize resources
    categories = categorize_resources(resources)
    
    # Create diagram
    with Diagram(
        diagram_title,
        filename=diagram_filename,
        direction="TB",
        show=False
    ):
        components = create_diagram_components(categories, diagram_title)
        
        if not components:
            # Fallback for unrecognized resources
            generic_resources = [General(f"{r['type']}\n({r['name']})") for r in resources[:5]]
            if len(generic_resources) > 1:
                generic_resources[0] >> generic_resources[1:]
        else:
            # Create connections based on typical AWS architecture patterns
            prev_component = None
            
            # DNS -> WAF -> Load Balancer -> Compute -> Database flow
            flow_order = ['dns', 'waf', 'load_balancer', 'compute', 'lambda', 'ecs', 'asg']
            
            for component_key in flow_order:
                if component_key in components:
                    current = components[component_key]
                    if prev_component is not None:
                        if isinstance(prev_component, list):
                            prev_component = prev_component[0]
                        if isinstance(current, list):
                            prev_component >> current
                        else:
                            prev_component >> current
                    prev_component = current
            
            # Connect to databases
            if prev_component and ('rds' in components or 'dynamodb' in components):
                if 'rds' in components:
                    if isinstance(prev_component, list):
                        prev_component >> components['rds']
                    else:
                        prev_component >> components['rds']
                if 'dynamodb' in components:
                    if isinstance(prev_component, list):
                        prev_component >> components['dynamodb']
                    else:
                        prev_component >> components['dynamodb']
            
            # Add storage if present
            if 's3' in components and prev_component:
                # S3 typically connected to compute layer
                if 'compute' in components:
                    if isinstance(components['compute'], list):
                        components['compute'][0] >> components['s3']
                    else:
                        components['compute'] >> components['s3']

# Step 1: Clone the repo if not already
if not os.path.exists(CLONE_DIR):
    print(f"Cloning repo into: {CLONE_DIR}")
    Repo.clone_from(REPO_URL, CLONE_DIR)
else:
    print(f"Repo already exists at: {CLONE_DIR}")

# Step 2: Recursively find all main.tf files
main_tf_paths = []
for root, dirs, files in os.walk(CLONE_DIR):
    if "main.tf" in files:
        main_tf_paths.append(os.path.join(root, "main.tf"))

print(f"\n✅ Found {len(main_tf_paths)} main.tf files.\n")

# Step 3: Parse each Terraform file and generate accurate diagrams
for tf_file in main_tf_paths:
    try:
        resources = parse_terraform_file(tf_file)
        generate_architecture_diagram(tf_file, resources)
    except Exception as e:
        print(f"❌ Error processing {tf_file}: {e}")

print("\n✅ Done. All architecture diagrams saved as architecture.png beside each main.tf.")
print("\n📊 Summary:")
print(f"   - Processed {len(main_tf_paths)} Terraform files")
print(f"   - Generated architecture diagrams based on actual resource definitions")
print(f"   - Diagrams saved as 'architecture.png' in each directory")

"""
⚠️  hcl2 not available, using regex parsing
Repo already exists at: sample_data/out/devops-directive-terraform-course

✅ Found 16 main.tf files.

📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/03-basics/aws-backend/main.tf
   Found resources: ['aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration', 'aws_dynamodb_table']
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/03-basics/web-app/main.tf
   Found resources: ['aws_instance', 'aws_instance', 'aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration', 'aws_security_group', 'aws_security_group_rule', 'aws_lb_listener', 'aws_lb_target_group', 'aws_lb_target_group_attachment', 'aws_lb_target_group_attachment', 'aws_lb_listener_rule', 'aws_security_group', 'aws_security_group_rule', 'aws_security_group_rule', 'aws_lb', 'aws_route53_zone', 'aws_route53_record', 'aws_db_instance']
No resources found in sample_data/out/devops-directive-terraform-course/03-basics/terraform-cloud-backend/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/06-organization-and-modules/consul/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/02-overview/main.tf
   Found resources: ['aws_instance']
No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/workspaces/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global/main.tf
   Found resources: ['aws_route53_zone']
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/main.tf
   Found resources: ['aws_instance', 'aws_db_instance']
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/main.tf
   Found resources: ['aws_instance', 'aws_instance', 'aws_s3_bucket', 'aws_s3_bucket_versioning', 'aws_s3_bucket_server_side_encryption_configuration', 'aws_security_group', 'aws_security_group_rule', 'aws_lb_listener', 'aws_lb_target_group', 'aws_lb_target_group_attachment', 'aws_lb_target_group_attachment', 'aws_lb_listener_rule', 'aws_security_group', 'aws_security_group_rule', 'aws_security_group_rule', 'aws_lb', 'aws_route53_zone', 'aws_route53_record', 'aws_db_instance']
No resources found in sample_data/out/devops-directive-terraform-course/08-testing/examples/hello-world/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/08-testing/deployed/staging/main.tf
No resources found in sample_data/out/devops-directive-terraform-course/08-testing/deployed/production/main.tf

✅ Done. All architecture diagrams saved as architecture.png beside each main.tf.

📊 Summary:
   - Processed 16 Terraform files
   - Generated architecture diagrams based on actual resource definitions
   - Diagrams saved as 'architecture.png' in each directory
"""
#!pip install gitpython diagrams hcl2

import os
import re
from git import Repo
import hcl2
from diagrams import Diagram, Cluster, Edge
from diagrams.aws.compute import EC2, ECS, Lambda, AutoScaling
from diagrams.aws.database import RDS, Dynamodb, ElastiCache, Redshift
from diagrams.aws.network import ELB, ALB, NLB, Route53, CloudFront, VPC, PrivateSubnet, PublicSubnet
from diagrams.aws.security import WAF, IAM, Cognito
from diagrams.aws.storage import S3, EBS, EFS
from diagrams.aws.integration import SQS, SNS
from diagrams.aws.analytics import Kinesis, Athena
from diagrams.aws.ml import Sagemaker
from diagrams.aws.devtools import Codebuild, Codedeploy, Codepipeline
from diagrams.aws.management import Cloudwatch, Cloudtrail
from diagrams.aws.general import General
from diagrams.k8s.compute import Pod, Deployment
from diagrams.k8s.network import Service, Ingress
from diagrams.onprem.database import PostgreSQL, MySQL
from diagrams.onprem.inmemory import Redis
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.network import Firewall

# Constants
REPO_URL = "https://github.com/sidpalas/devops-directive-terraform-course.git"
#CLONE_DIR = os.path.expanduser("~/devops-directive-terraform-course")
CLONE_DIR = os.path.expanduser("sample_data/out/devops-directive-terraform-course")
OUTPUT_DIR = "/tmp/terraform_diagrams"

def clone_or_update_repo(repo_url, clone_dir):
    """Clone repository or update if it already exists"""
    if not os.path.exists(clone_dir):
        print(f"🔄 Cloning repo into: {clone_dir}")
        Repo.clone_from(repo_url, clone_dir)
        print("✅ Repository cloned successfully")
    else:
        print(f"📁 Repository already exists at: {clone_dir}")
        try:
            repo = Repo(clone_dir)
            repo.remotes.origin.pull()
            print("✅ Repository updated successfully")
        except Exception as e:
            print(f"⚠️ Could not update repository: {e}")

def find_terraform_files(directory):
    """Recursively find all Terraform files"""
    tf_files = []
    for root, dirs, files in os.walk(directory):
        # Skip hidden directories and common non-terraform directories
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__']]
        
        for file in files:
            if file.endswith(('.tf', '.tf.json')):
                tf_files.append(os.path.join(root, file))
    
    return tf_files

def parse_terraform_file(tf_file):
    """Parse a Terraform file and extract resources"""
    resources = {}
    
    try:
        with open(tf_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Try to parse with HCL2
        try:
            parsed = hcl2.loads(content)
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
        except Exception as hcl_error:
            # Fallback to regex parsing for problematic files
            print(f"⚠️ HCL parsing failed for {tf_file}, using regex fallback: {hcl_error}")
            resources = parse_with_regex(content)
            
    except Exception as e:
        print(f"❌ Error parsing {tf_file}: {e}")
        
    return resources

def parse_with_regex(content):
    """Fallback regex-based parsing for Terraform files"""
    resources = {}
    
    # Pattern to match resource blocks
    resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
    matches = re.findall(resource_pattern, content, re.MULTILINE)
    
    for resource_type, resource_name in matches:
        if resource_type not in resources:
            resources[resource_type] = []
        resources[resource_type].append({
            'name': resource_name,
            'config': {}
        })
    
    return resources

def get_diagram_components(resources):
    """Map Terraform resources to diagram components"""
    components = {
        'compute': [],
        'database': [],
        'network': [],
        'storage': [],
        'security': [],
        'other': []
    }
    
    # Resource type to component mapping
    resource_mappings = {
        # Compute
        'aws_instance': ('compute', EC2),
        'aws_ecs_service': ('compute', ECS),
        'aws_ecs_cluster': ('compute', ECS),
        'aws_lambda_function': ('compute', Lambda),
        'aws_autoscaling_group': ('compute', AutoScaling),
        
        # Database
        'aws_db_instance': ('database', RDS),
        'aws_rds_cluster': ('database', RDS),
        'aws_dynamodb_table': ('database', Dynamodb),
        'aws_elasticache_cluster': ('database', ElastiCache),
        'aws_redshift_cluster': ('database', Redshift),
        
        # Network
        'aws_lb': ('network', ALB),
        'aws_alb': ('network', ALB),
        'aws_elb': ('network', ELB),
        'aws_nlb': ('network', NLB),
        'aws_route53_record': ('network', Route53),
        'aws_cloudfront_distribution': ('network', CloudFront),
        'aws_vpc': ('network', VPC),
        'aws_subnet': ('network', PrivateSubnet),
        
        # Storage
        'aws_s3_bucket': ('storage', S3),
        'aws_ebs_volume': ('storage', EBS),
        'aws_efs_file_system': ('storage', EFS),
        
        # Security
        'aws_waf_web_acl': ('security', WAF),
        'aws_iam_role': ('security', IAM),
        'aws_iam_policy': ('security', IAM),
        'aws_cognito_user_pool': ('security', Cognito),
        
        # Integration
        'aws_sqs_queue': ('other', SQS),
        'aws_sns_topic': ('other', SNS),
        'aws_cloudwatch_log_group': ('other', Cloudwatch),
        
        # Kubernetes
        'kubernetes_deployment': ('compute', Deployment),
        'kubernetes_service': ('network', Service),
        'kubernetes_ingress': ('network', Ingress),
        'kubernetes_pod': ('compute', Pod),
        
        # Generic resources
        'docker_container': ('compute', Rack),
        'docker_image': ('compute', Rack),
    }
    
    for resource_type, instances in resources.items():
        if resource_type in resource_mappings:
            category, component_class = resource_mappings[resource_type]
            for instance in instances:
                label = f"{resource_type}\n{instance['name']}"
                components[category].append((component_class, label))
        else:
            # Create generic component for unknown resource types
            label = f"{resource_type}\n{instances[0]['name'] if instances else 'unknown'}"
            components['other'].append((General, label))
    
    return components

def create_architecture_diagram(resources, output_path, title="Terraform Architecture"):
    """Create architecture diagram based on parsed resources"""
    
    if not resources:
        print("⚠️ No resources found, creating empty diagram")
        with Diagram(title, filename=output_path, direction="TB", show=False):
            General("No Resources Found")
        return
    
    components = get_diagram_components(resources)
    
    # Filter out empty categories
    non_empty_components = {k: v for k, v in components.items() if v}
    
    if not non_empty_components:
        print("⚠️ No mappable resources found, creating generic diagram")
        with Diagram(title, filename=output_path, direction="TB", show=False):
            General("Generic Resources")
        return
    
    with Diagram(title, filename=output_path, direction="TB", show=False):
        created_components = {}
        
        # Create components by category
        for category, component_list in non_empty_components.items():
            if len(component_list) > 1:
                # Create cluster for multiple components of same category
                with Cluster(f"{category.title()} Layer"):
                    category_components = []
                    for component_class, label in component_list:
                        comp = component_class(label)
                        category_components.append(comp)
                    created_components[category] = category_components
            else:
                # Single component, no cluster needed
                component_class, label = component_list[0]
                created_components[category] = [component_class(label)]
        
        # Create logical connections between layers
        create_logical_connections(created_components)

def create_logical_connections(components):
    """Create logical connections between different component layers"""
    
    # Define typical connection patterns
    connection_patterns = [
        ('network', 'security'),  # Network -> Security (e.g., ALB -> WAF)
        ('security', 'compute'),  # Security -> Compute (e.g., WAF -> EC2)
        ('network', 'compute'),   # Network -> Compute (e.g., ALB -> EC2)
        ('compute', 'database'),  # Compute -> Database (e.g., EC2 -> RDS)
        ('compute', 'storage'),   # Compute -> Storage (e.g., EC2 -> S3)
        ('other', 'compute'),     # Other -> Compute (e.g., SQS -> Lambda)
    ]
    
    for source_category, target_category in connection_patterns:
        if source_category in components and target_category in components:
            source_components = components[source_category]
            target_components = components[target_category]
            
            # Connect first component of each category (simplified)
            if source_components and target_components:
                source_components[0] >> target_components[0]

def generate_diagrams_for_directory(directory):
    """Generate diagrams for all Terraform files in a directory"""
    tf_files = find_terraform_files(directory)
    
    if not tf_files:
        print("❌ No Terraform files found")
        return
    
    print(f"📊 Found {len(tf_files)} Terraform files")
    
    # Group files by directory to create one diagram per directory
    directories = {}
    for tf_file in tf_files:
        dir_path = os.path.dirname(tf_file)
        if dir_path not in directories:
            directories[dir_path] = []
        directories[dir_path].append(tf_file)
    
    for dir_path, files in directories.items():
        print(f"\n📁 Processing directory: {dir_path}")
        
        # Combine resources from all .tf files in the directory
        all_resources = {}
        
        for tf_file in files:
            print(f"   📄 Parsing: {os.path.basename(tf_file)}")
            resources = parse_terraform_file(tf_file)
            
            # Merge resources
            for resource_type, instances in resources.items():
                if resource_type not in all_resources:
                    all_resources[resource_type] = []
                all_resources[resource_type].extend(instances)
        
        # Generate diagram for this directory
        if all_resources:
            relative_path = os.path.relpath(dir_path, directory)
            diagram_title = f"Terraform Architecture - {relative_path}"
            output_path = os.path.join(dir_path, "architecture")
            
            print(f"   🎨 Creating diagram: {output_path}.png")
            create_architecture_diagram(all_resources, output_path, diagram_title)
            
            # Print summary of resources found
            total_resources = sum(len(instances) for instances in all_resources.values())
            print(f"   ✅ Found {total_resources} resources across {len(all_resources)} types")
            for resource_type, instances in all_resources.items():
                print(f"      - {len(instances)} {resource_type}")
        else:
            print(f"   ⚠️ No resources found in {dir_path}")

def main():
    """Main execution function"""
    print("🚀 Starting Terraform Architecture Diagram Generator")
    
    # Step 1: Clone or update repository
    clone_or_update_repo(REPO_URL, CLONE_DIR)
    
    # Step 2: Generate diagrams
    print(f"\n🔍 Scanning for Terraform files in: {CLONE_DIR}")
    generate_diagrams_for_directory(CLONE_DIR)
    
    print(f"\n✅ Architecture diagram generation complete!")
    print(f"📁 Diagrams saved as 'architecture.png' in each Terraform directory")

if __name__ == "__main__":
    # Install required packages check
    try:
        import hcl2
        from diagrams import Diagram
        from git import Repo
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("📦 Install with: pip install python-hcl2 diagrams gitpython")
        exit(1)
    
    main()

"""
🚀 Starting Terraform Architecture Diagram Generator
📁 Repository already exists at: sample_data/out/devops-directive-terraform-course
✅ Repository updated successfully

🔍 Scanning for Terraform files in: sample_data/out/devops-directive-terraform-course
📊 Found 28 Terraform files

📁 Processing directory: sample_data/out/devops-directive-terraform-course/03-basics/aws-backend
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/03-basics/aws-backend/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/03-basics/aws-backend/architecture.png
   ✅ Found 4 resources across 4 types
      - 1 aws_s3_bucket
      - 1 aws_s3_bucket_versioning
      - 1 aws_s3_bucket_server_side_encryption_configuration
      - 1 aws_dynamodb_table

📁 Processing directory: sample_data/out/devops-directive-terraform-course/03-basics/web-app
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/03-basics/web-app/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/03-basics/web-app/architecture.png
   ✅ Found 19 resources across 14 types
      - 2 aws_instance
      - 1 aws_s3_bucket
      - 1 aws_s3_bucket_versioning
      - 1 aws_s3_bucket_server_side_encryption_configuration
      - 2 aws_security_group
      - 3 aws_security_group_rule
      - 1 aws_lb_listener
      - 1 aws_lb_target_group
      - 2 aws_lb_target_group_attachment
      - 1 aws_lb_listener_rule
      - 1 aws_lb
      - 1 aws_route53_zone
      - 1 aws_route53_record
      - 1 aws_db_instance

📁 Processing directory: sample_data/out/devops-directive-terraform-course/03-basics/terraform-cloud-backend
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/03-basics/terraform-cloud-backend/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/03-basics/terraform-cloud-backend

📁 Processing directory: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/consul
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/consul/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/06-organization-and-modules/consul

📁 Processing directory: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app

📁 Processing directory: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module
   📄 Parsing: database.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/database.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: compute.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/compute.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: outputs.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/outputs.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: storage.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/storage.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: networking.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/networking.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: variables.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/variables.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: dns.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/dns.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/architecture.png
   ✅ Found 19 resources across 14 types
      - 1 aws_db_instance
      - 2 aws_instance
      - 1 aws_s3_bucket
      - 1 aws_s3_bucket_versioning
      - 1 aws_s3_bucket_server_side_encryption_configuration
      - 2 aws_security_group
      - 3 aws_security_group_rule
      - 1 aws_lb_listener
      - 1 aws_lb_target_group
      - 2 aws_lb_target_group_attachment
      - 1 aws_lb_listener_rule
      - 1 aws_lb
      - 1 aws_route53_zone
      - 1 aws_route53_record

📁 Processing directory: sample_data/out/devops-directive-terraform-course/02-overview
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/02-overview/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/02-overview/architecture.png
   ✅ Found 1 resources across 1 types
      - 1 aws_instance

📁 Processing directory: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/workspaces
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/workspaces/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/workspaces

📁 Processing directory: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging

📁 Processing directory: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production

📁 Processing directory: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global/architecture.png
   ✅ Found 1 resources across 1 types
      - 1 aws_route53_zone

📁 Processing directory: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples
   📄 Parsing: outputs.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/outputs.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: variables.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/variables.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/architecture.png
   ✅ Found 2 resources across 2 types
      - 1 aws_instance
      - 1 aws_db_instance

📁 Processing directory: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app
   📄 Parsing: outputs.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/outputs.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   📄 Parsing: variables.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/variables.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/architecture.png
   ✅ Found 19 resources across 14 types
      - 2 aws_instance
      - 1 aws_s3_bucket
      - 1 aws_s3_bucket_versioning
      - 1 aws_s3_bucket_server_side_encryption_configuration
      - 2 aws_security_group
      - 3 aws_security_group_rule
      - 1 aws_lb_listener
      - 1 aws_lb_target_group
      - 2 aws_lb_target_group_attachment
      - 1 aws_lb_listener_rule
      - 1 aws_lb
      - 1 aws_route53_zone
      - 1 aws_route53_record
      - 1 aws_db_instance

📁 Processing directory: sample_data/out/devops-directive-terraform-course/08-testing/modules/hello-world
   📄 Parsing: instance.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/08-testing/modules/hello-world/instance.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   🎨 Creating diagram: sample_data/out/devops-directive-terraform-course/08-testing/modules/hello-world/architecture.png
   ✅ Found 3 resources across 3 types
      - 1 aws_instance
      - 1 aws_security_group
      - 1 aws_security_group_rule

📁 Processing directory: sample_data/out/devops-directive-terraform-course/08-testing/examples/hello-world
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/08-testing/examples/hello-world/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/08-testing/examples/hello-world

📁 Processing directory: sample_data/out/devops-directive-terraform-course/08-testing/deployed/staging
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/08-testing/deployed/staging/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/08-testing/deployed/staging

📁 Processing directory: sample_data/out/devops-directive-terraform-course/08-testing/deployed/production
   📄 Parsing: main.tf
⚠️ HCL parsing failed for sample_data/out/devops-directive-terraform-course/08-testing/deployed/production/main.tf, using regex fallback: module 'hcl2' has no attribute 'loads'
   ⚠️ No resources found in sample_data/out/devops-directive-terraform-course/08-testing/deployed/production

✅ Architecture diagram generation complete!
📁 Diagrams saved as 'architecture.png' in each Terraform directory
"""
import os
import re
import requests
import hcl2
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
TARGET_DIR = "/content/sample_data/out/checkly_diagram"
TF_FILE = os.path.join(TARGET_DIR, "main.tf")

# Download main.tf
def download_main_tf_from_url(url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    print(f"⬇️ Downloading Terraform file from:\n   {url}")
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"❌ Failed to download file: {r.status_code}")
    with open(save_path, "w") as f:
        f.write(r.text)
    print(f"✅ Saved to: {save_path}")

# Parse main.tf with fallback
def parse_terraform_file(tf_file):
    resources = {}
    try:
        with open(tf_file, 'r', encoding='utf-8') as f:
            content = f.read()
        try:
            parsed = hcl2.loads(content)
            for block in parsed.get("resource", []):
                for resource_type, instances in block.items():
                    for name, config in instances.items():
                        resources.setdefault(resource_type, []).append({
                            'name': name, 'config': config
                        })
        except Exception as hcl_err:
            print(f"⚠️ HCL parse failed: {hcl_err}")
            resources = parse_with_regex(content)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
    return resources

def parse_with_regex(content):
    pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
    matches = re.findall(pattern, content)
    resources = {}
    for rtype, name in matches:
        resources.setdefault(rtype, []).append({'name': name, 'config': {}})
    return resources

# Map to diagram components
def get_diagram_components(resources):
    mapping = {
        # Compute
        'aws_instance': (EC2, 'compute'),
        'aws_lambda_function': (Lambda, 'compute'),
        'aws_ecs_service': (ECS, 'compute'),
        'aws_autoscaling_group': (AutoScaling, 'compute'),
        # DB
        'aws_db_instance': (RDS, 'database'),
        'aws_dynamodb_table': (Dynamodb, 'database'),
        # Network
        'aws_alb': (ALB, 'network'),
        'aws_elb': (ELB, 'network'),
        'aws_nlb': (NLB, 'network'),
        'aws_route53_record': (Route53, 'network'),
        # Storage
        'aws_s3_bucket': (S3, 'storage'),
        # Security
        'aws_waf_web_acl': (WAF, 'security'),
        # Generic
        'docker_container': (Rack, 'compute'),
        'aws_sqs_queue': (SQS, 'other'),
        'aws_sns_topic': (SNS, 'other'),
    }
    components = {
        'compute': [],
        'database': [],
        'network': [],
        'storage': [],
        'security': [],
        'other': [],
    }
    for rtype, instances in resources.items():
        for inst in instances:
            label = f"{rtype}\n{inst['name']}"
            if rtype in mapping:
                comp_class, category = mapping[rtype]
            else:
                comp_class, category = General, 'other'
            components[category].append(comp_class(label))
    return components

# Draw diagram
def create_diagram(components, out_path):
    with Diagram("Terraform Architecture", filename=out_path, direction="TB", show=False):
        created = {}
        for cat, comps in components.items():
            if comps:
                with Cluster(cat.title()):
                    created[cat] = comps

        # Connect layers (simple chain if exists)
        layers = ['network', 'security', 'compute', 'database', 'storage']
        for i in range(len(layers) - 1):
            src, tgt = layers[i], layers[i+1]
            if src in created and tgt in created:
                created[src][0] >> created[tgt][0]

# Run
download_main_tf_from_url(RAW_URL, TF_FILE)
resources = parse_terraform_file(TF_FILE)
components = get_diagram_components(resources)
create_diagram(components, os.path.join(TARGET_DIR, "architecture"))

print("\n✅ Architecture diagram saved at:")
!ls -al /content/sample_data/out/checkly_diagram/

""
⬇️ Downloading Terraform file from:
   https://raw.githubusercontent.com/sidpalas/devops-directive-terraform-course/refs/heads/main/07-managing-multiple-environments/file-structure/production/main.tf
✅ Saved to: /content/sample_data/out/checkly_diagram/main.tf
⚠️ HCL parse failed: module 'hcl2' has no attribute 'loads'

✅ Architecture diagram saved at:
total 20
drwxr-xr-x 2 root root 4096 Jul  1 02:07 .
drwxr-xr-x 4 root root 4096 Jul  1 02:07 ..
-rw-r--r-- 1 root root 5339 Jul  1 02:07 architecture.png
-rw-r--r-- 1 root root 1097 Jul  1 02:07 main.tf
"""
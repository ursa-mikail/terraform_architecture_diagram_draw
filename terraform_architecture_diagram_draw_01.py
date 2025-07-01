# !pip install gitpython diagrams

import os
from git import Repo
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB, Route53
from diagrams.aws.security import WAF

# Constants
REPO_URL = "https://github.com/sidpalas/devops-directive-terraform-course.git"
CLONE_DIR = os.path.expanduser("~/devops-directive-terraform-course")
OUTPUT_DIR = "/content/sample_data/out"

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Step 1: Clone the repo if needed
if not os.path.exists(CLONE_DIR):
    print(f"Cloning repo into: {CLONE_DIR}")
    Repo.clone_from(REPO_URL, CLONE_DIR)
else:
    print(f"Repo already exists at: {CLONE_DIR}")

# Step 2: Search for all main.tf files
main_tf_paths = []
for root, dirs, files in os.walk(CLONE_DIR):
    if "main.tf" in files:
        main_tf_paths.append(os.path.join(root, "main.tf"))

print(f"\n✅ Found {len(main_tf_paths)} main.tf files.\n")

# Step 3: Generate diagrams
for idx, tf_file in enumerate(main_tf_paths, 1):
    diagram_name = f"architecture_{idx}"
    diagram_path = os.path.join(OUTPUT_DIR, diagram_name)

    print(f"📌 Drawing architecture for: {tf_file}")

    with Diagram(
        f"Terraform Architecture #{idx}",
        filename=diagram_path,
        direction="TB",
        show=False
    ):
        dns = Route53("Route53")
        waf = WAF("WAF")

        with Cluster("Load Balancing"):
            lb = ELB("ELB")

        with Cluster("Application Layer"):
            ec2_group = [EC2("App1"), EC2("App2")]

        with Cluster("Database Layer"):
            db = RDS("RDS")

        dns >> waf >> lb >> ec2_group >> db

print(f"\n✅ Done. All diagrams saved to: {OUTPUT_DIR}")

"""
Repo already exists at: /root/devops-directive-terraform-course

✅ Found 16 main.tf files.

📌 Drawing architecture for: /root/devops-directive-terraform-course/03-basics/aws-backend/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/03-basics/web-app/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/03-basics/terraform-cloud-backend/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/06-organization-and-modules/consul/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/06-organization-and-modules/web-app/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/06-organization-and-modules/web-app-module/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/02-overview/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/07-managing-multiple-environments/workspaces/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/04-variables-and-outputs/examples/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/04-variables-and-outputs/web-app/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/08-testing/examples/hello-world/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/08-testing/deployed/staging/main.tf
📌 Drawing architecture for: /root/devops-directive-terraform-course/08-testing/deployed/production/main.tf

✅ Done. All diagrams saved to: /content/sample_data/out
"""

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
#CLONE_DIR = os.path.expanduser("~/devops-directive-terraform-course")
#CLONE_DIR = os.path.expanduser("content/sample_data/out/devops-directive-terraform-course")
CLONE_DIR = os.path.expanduser("sample_data/out/devops-directive-terraform-course")
OUTPUT_DIR = "/sample_data"

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

# Step 3: Generate placeholder architecture diagrams
for tf_file in main_tf_paths:
    output_dir = os.path.dirname(tf_file)
    diagram_filename = os.path.join(output_dir, "architecture")

    print(f"📌 Generating architecture for: {tf_file}")

    with Diagram(
        "Sample Terraform Architecture",
        filename=diagram_filename,
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

print("\n✅ Done. All architecture diagrams saved as architecture.png beside each main.tf.")

"""
Cloning repo into: sample_data/out/devops-directive-terraform-course

✅ Found 16 main.tf files.

📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/03-basics/aws-backend/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/03-basics/web-app/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/03-basics/terraform-cloud-backend/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/consul/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/06-organization-and-modules/web-app-module/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/02-overview/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/workspaces/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/staging/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/production/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/07-managing-multiple-environments/file-structure/global/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/examples/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/04-variables-and-outputs/web-app/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/08-testing/examples/hello-world/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/08-testing/deployed/staging/main.tf
📌 Generating architecture for: sample_data/out/devops-directive-terraform-course/08-testing/deployed/production/main.tf

✅ Done. All architecture diagrams saved as architecture.png beside each main.tf.
"""

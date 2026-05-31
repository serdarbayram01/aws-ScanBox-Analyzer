"""
News module — Canonical AWS service vocabulary.
Ported from 0-Referans/aws-whats-new/scripts/aws-services.js.
Used by fetcher.py to extract service mentions from RSS title + categories.
"""

AWS_SERVICES = [
    # Compute
    'EC2', 'Lambda', 'Lightsail', 'Batch', 'Outposts', 'Wavelength', 'Local Zones',
    'Elastic Beanstalk', 'Serverless Application Repository', 'App Runner',
    # Containers
    'ECS', 'EKS', 'ECR', 'Fargate', 'App Mesh', 'Cloud Map',
    # Storage
    'S3', 'EBS', 'EFS', 'FSx', 'Storage Gateway', 'Backup', 'Snow Family',
    'Snowball', 'Snowcone', 'Snowmobile', 'S3 Glacier', 'S3 Intelligent-Tiering',
    # Database
    'RDS', 'Aurora', 'DynamoDB', 'ElastiCache', 'Neptune', 'QLDB', 'Timestream',
    'DocumentDB', 'Keyspaces', 'MemoryDB', 'Redshift', 'OpenSearch',
    # Networking
    'VPC', 'CloudFront', 'Route 53', 'API Gateway', 'Direct Connect', 'Transit Gateway',
    'Global Accelerator', 'PrivateLink', 'Elastic Load Balancing', 'ELB', 'ALB', 'NLB',
    'AWS Network Firewall', 'Shield', 'WAF',
    # Security & Identity
    'IAM', 'Cognito', 'Secrets Manager', 'Certificate Manager', 'ACM', 'KMS',
    'CloudHSM', 'GuardDuty', 'Inspector', 'Macie', 'Security Hub', 'Detective',
    'Artifact', 'Audit Manager', 'SSO', 'IAM Identity Center', 'Verified Access',
    # AI & ML
    'SageMaker', 'Bedrock', 'Rekognition', 'Textract', 'Comprehend', 'Translate',
    'Polly', 'Transcribe', 'Lex', 'Forecast', 'Personalize', 'Fraud Detector',
    'CodeGuru', 'DevOps Guru', 'Lookout', 'Panorama', 'Monitron', 'HealthLake',
    'Augmented AI', 'Kendra', 'Nova', 'Titan', 'Claude', 'Q',
    # Developer Tools
    'CodeCommit', 'CodeBuild', 'CodeDeploy', 'CodePipeline', 'CodeStar',
    'Cloud9', 'CloudShell', 'X-Ray', 'CodeArtifact', 'CodeCatalyst',
    # Management & Governance
    'CloudWatch', 'CloudTrail', 'Config', 'Systems Manager', 'SSM',
    'OpsWorks', 'Service Catalog', 'Trusted Advisor', 'Control Tower',
    'Organizations', 'License Manager', 'Well-Architected Tool', 'Health',
    'Chatbot', 'Incident Manager', 'Resilience Hub',
    # Analytics
    'Athena', 'EMR', 'Kinesis', 'Glue', 'Data Pipeline', 'QuickSight',
    'Lake Formation', 'MSK', 'Kafka', 'Data Exchange', 'Clean Rooms',
    'Entity Resolution', 'FinSpace',
    # Application Integration
    'SQS', 'SNS', 'EventBridge', 'Step Functions', 'MQ', 'AppFlow',
    'AppSync', 'SWF', 'Managed Workflows for Apache Airflow', 'MWAA',
    # Business Applications
    'WorkSpaces', 'AppStream', 'Connect', 'Chime', 'WorkMail', 'WorkDocs',
    'Pinpoint', 'SES', 'Amplify',
    # Infrastructure
    'CloudFormation', 'CDK', 'SAM', 'Terraform', 'Proton',
    # Edge & IoT
    'IoT Core', 'IoT Greengrass', 'IoT Analytics', 'IoT Events', 'IoT SiteWise',
    'IoT TwinMaker', 'IoT FleetWise', 'IoT RoboRunner', 'Sidewalk',
    # Migration
    'Migration Hub', 'DMS', 'Database Migration Service', 'Application Migration Service',
    'MGN', 'Server Migration Service', 'DataSync', 'Transfer Family',
    # Cost Management
    'Cost Explorer', 'Budgets', 'Cost and Usage Report', 'Savings Plans',
    # Media
    'Elemental', 'MediaConvert', 'MediaLive', 'MediaPackage', 'MediaStore',
    'MediaTailor', 'IVS', 'Interactive Video Service',
    # Robotics & Quantum
    'RoboMaker', 'Braket',
    # End User Computing
    'WorkSpaces Web', 'WorkSpaces Thin Client',
]

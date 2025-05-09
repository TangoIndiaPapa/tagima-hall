import boto3
import yaml
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class AWSCleanupWithCosts:
    def __init__(self):
        try:
            # Load config
            with open('config.yaml', 'r') as file:
                self.config = yaml.safe_load(file)
                self.bucket_name = self.config['aws']['bucket_name']

            # Initialize AWS clients
            self.s3 = boto3.client('s3')
            self.iam = boto3.client('iam')
            self.ce = boto3.client('ce')  # Cost Explorer
            self.rekognition = boto3.client('rekognition')
            self.bedrock = boto3.client('bedrock-runtime')
            
            logger.info("AWS clients initialized successfully")
            
        except Exception as e:
            logger.error(f"Initialization error: {str(e)}")
            raise

    def get_detailed_costs(self):
        """Get detailed AWS costs for all relevant services"""
        try:
            end_date = datetime.now()
            start_date = end_date.replace(day=1)  # Start of current month
            
            response = self.ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='MONTHLY',
                Metrics=['UnblendedCost', 'UsageQuantity'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'USAGE_TYPE'}
                ]
            )

            costs = {
                'S3': {
                    'storage': 0.0,
                    'requests': 0.0,
                    'data_transfer': 0.0
                },
                'Rekognition': {
                    'image_analysis': 0.0,
                    'inference_time': 0.0
                },
                'Bedrock': {
                    'inference': 0.0,
                    'processing': 0.0
                },
                'Total': 0.0
            }

            # Process cost data
            for group in response['ResultsByTime'][0]['Groups']:
                service = group['Keys'][0]
                usage_type = group['Keys'][1]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                quantity = float(group['Metrics']['UsageQuantity']['Amount'])

                if 'S3' in service:
                    if 'Storage' in usage_type:
                        costs['S3']['storage'] += cost
                    elif 'Request' in usage_type:
                        costs['S3']['requests'] += cost
                    else:
                        costs['S3']['data_transfer'] += cost
                elif 'Rekognition' in service:
                    if 'Analysis' in usage_type:
                        costs['Rekognition']['image_analysis'] += cost
                    else:
                        costs['Rekognition']['inference_time'] += cost
                elif 'Bedrock' in service:
                    if 'Inference' in usage_type:
                        costs['Bedrock']['inference'] += cost
                    else:
                        costs['Bedrock']['processing'] += cost

                costs['Total'] += cost

            return costs

        except Exception as e:
            logger.error(f"Error getting detailed costs: {str(e)}")
            return None

    def get_resource_usage(self):
        """Get detailed resource usage metrics"""
        try:
            usage = {
                'S3': {
                    'objects': 0,
                    'size_bytes': 0,
                    'requests': {
                        'get': 0,
                        'put': 0
                    }
                },
                'Rekognition': {
                    'images_analyzed': 0,
                    'labels_detected': 0
                },
                'Bedrock': {
                    'images_generated': 0,
                    'tokens_processed': 0
                }
            }

            # Get S3 metrics
            try:
                paginator = self.s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=self.bucket_name):
                    if 'Contents' in page:
                        usage['S3']['objects'] += len(page['Contents'])
                        usage['S3']['size_bytes'] += sum(obj['Size'] for obj in page['Contents'])
            except self.s3.exceptions.NoSuchBucket:
                pass

            return usage

        except Exception as e:
            logger.error(f"Error getting resource usage: {str(e)}")
            return None

    def cleanup_s3(self):
        """Delete S3 bucket and contents"""
        try:
            logger.info(f"Cleaning up S3 bucket: {self.bucket_name}")
            
            objects_deleted = 0
            try:
                paginator = self.s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=self.bucket_name):
                    if 'Contents' in page:
                        objects = [{'Key': obj['Key']} for obj in page['Contents']]
                        self.s3.delete_objects(
                            Bucket=self.bucket_name,
                            Delete={'Objects': objects}
                        )
                        objects_deleted += len(objects)
                
                self.s3.delete_bucket(Bucket=self.bucket_name)
                logger.info(f"Deleted {objects_deleted} objects and bucket {self.bucket_name}")
                
            except self.s3.exceptions.NoSuchBucket:
                logger.info(f"Bucket {self.bucket_name} does not exist")
                
        except Exception as e:
            logger.error(f"Error cleaning up S3: {str(e)}")
            raise

    def cleanup_local_files(self):
        """Delete local files"""
        try:
            files_deleted = 0
            generated_dir = Path('generated_images')
            if generated_dir.exists():
                for file in generated_dir.glob('*'):
                    file.unlink()
                    files_deleted += 1
                generated_dir.rmdir()
                logger.info(f"Deleted {files_deleted} local files and directory")
            else:
                logger.info("No local files to clean up")
                
        except Exception as e:
            logger.error(f"Error cleaning up local files: {str(e)}")
            raise

    def cleanup_iam_policies(self):
        """Clean up IAM policies"""
        try:
            policies_deleted = 0
            policy_names = ['InternRekognitionPolicy', 'AIDemoPolicy', 'UpdatedAIDemoPolicy']
            
            for policy_name in policy_names:
                try:
                    response = self.iam.list_policies(Scope='Local')
                    for policy in response['Policies']:
                        if policy['PolicyName'] == policy_name:
                            policy_arn = policy['Arn']
                            
                            # Detach from users
                            for user in self.iam.list_entities_for_policy(
                                PolicyArn=policy_arn,
                                EntityFilter='User'
                            )['PolicyUsers']:
                                self.iam.detach_user_policy(
                                    UserName=user['UserName'],
                                    PolicyArn=policy_arn
                                )
                            
                            self.iam.delete_policy(PolicyArn=policy_arn)
                            policies_deleted += 1
                            
                except self.iam.exceptions.NoSuchEntityException:
                    continue
                    
            logger.info(f"Deleted {policies_deleted} IAM policies")
                    
        except Exception as e:
            logger.error(f"Error cleaning up IAM policies: {str(e)}")
            raise

    def print_detailed_cost_report(self, costs, usage):
        """Print detailed cost and usage report"""
        logger.info("\nDetailed AWS Cost and Usage Report")
        logger.info("================================")
        
        if costs:
            logger.info("\nActual Costs This Month:")
            logger.info("------------------------")
            logger.info("S3:")
            logger.info(f"  Storage: ${costs['S3']['storage']:.4f}")
            logger.info(f"  Requests: ${costs['S3']['requests']:.4f}")
            logger.info(f"  Data Transfer: ${costs['S3']['data_transfer']:.4f}")
            
            logger.info("\nRekognition:")
            logger.info(f"  Image Analysis: ${costs['Rekognition']['image_analysis']:.4f}")
            logger.info(f"  Inference Time: ${costs['Rekognition']['inference_time']:.4f}")
            
            logger.info("\nBedrock:")
            logger.info(f"  Inference: ${costs['Bedrock']['inference']:.4f}")
            logger.info(f"  Processing: ${costs['Bedrock']['processing']:.4f}")
            
            logger.info(f"\nTotal Cost: ${costs['Total']:.4f}")

        if usage:
            logger.info("\nResource Usage:")
            logger.info("--------------")
            logger.info(f"S3 Objects: {usage['S3']['objects']}")
            logger.info(f"Total Storage: {usage['S3']['size_bytes'] / 1024 / 1024:.2f} MB")
            
            # Calculate free tier usage
            logger.info("\nFree Tier Status:")
            logger.info("----------------")
            s3_storage_gb = usage['S3']['size_bytes'] / (1024 ** 3)
            logger.info(f"S3 Storage Used: {s3_storage_gb:.2f} GB (Free Tier: 5 GB)")
            if usage['S3']['objects'] > 0:
                logger.info(f"Rekognition Images: {usage['S3']['objects']} (Free Tier: 5,000 images/month)")
                logger.info(f"Bedrock Generations: {usage['S3']['objects']} (Pricing varies)")

def main():
    logger.info("Starting AWS resource cleanup with detailed cost analysis...")
    
    try:
        cleanup = AWSCleanupWithCosts()
        
        # Get initial costs and usage
        initial_costs = cleanup.get_detailed_costs()
        initial_usage = cleanup.get_resource_usage()
        
        # Confirm cleanup
        response = input("\nThis will delete ALL resources created during the demo. Continue? (yes/no): ").strip().lower()
        if response != 'yes':
            logger.info("Cleanup cancelled")
            return
        
        # Perform cleanup
        cleanup.cleanup_s3()
        cleanup.cleanup_local_files()
        cleanup.cleanup_iam_policies()
        
        # Print detailed cost report
        cleanup.print_detailed_cost_report(initial_costs, initial_usage)
        
        logger.info("\nCleanup completed successfully!")
        logger.info("All demo resources have been removed")
        
        # Save cost report
        report_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"cost_report_{report_time}.txt"
        with open(report_file, 'w') as f:
            f.write("AWS Demo Cost Report\n")
            f.write("==================\n\n")
            if initial_costs:
                f.write(f"Total Cost: ${initial_costs['Total']:.4f}\n")
                f.write(f"Generated: {datetime.now()}\n")
        logger.info(f"\nCost report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
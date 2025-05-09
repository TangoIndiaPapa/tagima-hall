import boto3
import logging
import sys

# Configure logging to show everything
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

def test_aws():
    """Basic AWS connectivity test"""
    try:
        logger.info("Starting AWS test...")

        # Test AWS credentials
        logger.info("Testing AWS credentials...")
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"AWS Account: {identity['Account']}")

        # Test S3
        logger.info("\nTesting S3...")
        s3 = boto3.client('s3')
        buckets = s3.list_buckets()
        logger.info(f"Found {len(buckets['Buckets'])} buckets")

        # Test Rekognition
        logger.info("\nTesting Rekognition...")
        rekognition = boto3.client('rekognition')
        logger.info("Rekognition client created successfully")

        # Test Bedrock
        logger.info("\nTesting Bedrock...")
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        logger.info("Bedrock client created successfully")

        logger.info("\nAll tests completed successfully!")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    print("Script starting...")  # Basic print to verify script execution
    test_aws()
    print("Script completed!")  # Basic print to verify script completion
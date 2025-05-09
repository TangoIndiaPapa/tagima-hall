import boto3
import yaml
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_aws_connections():
    """Test each AWS service connection"""
    try:
        # Test 1: Load config
        logger.info("Test 1: Loading config...")
        with open('config.yaml', 'r') as file:
            config = yaml.safe_load(file)
            logger.info(f"Config loaded: {config}")

        # Test 2: Check AWS credentials
        logger.info("\nTest 2: Checking AWS credentials...")
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        logger.info(f"AWS Identity: {identity}")

        # Test 3: Test S3 access
        logger.info("\nTest 3: Testing S3 access...")
        s3 = boto3.client('s3')
        buckets = s3.list_buckets()
        logger.info(f"S3 Buckets: {buckets}")

        # Test 4: Test Rekognition access
        logger.info("\nTest 4: Testing Rekognition access...")
        rekognition = boto3.client('rekognition')
        # Just testing connection, no actual API call

        # Test 5: Test Bedrock access
        logger.info("\nTest 5: Testing Bedrock access...")
        bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        # Just testing connection, no actual API call

        logger.info("\nAll connection tests completed successfully!")

    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        raise

if __name__ == "__main__":
    test_aws_connections()
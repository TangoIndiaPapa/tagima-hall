import boto3
import yaml
import json
import sys
import logging
import base64
import argparse
from datetime import datetime
import os
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

class RekognitionDemo:
    def __init__(self):
        print("Initializing AWS Services...")
        try:
            # Load config
            with open('config.yaml', 'r') as file:
                self.config = yaml.safe_load(file)
            
            # Initialize AWS clients
            self.s3 = boto3.client('s3')
            self.rekognition = boto3.client('rekognition')
            self.bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
            self.bucket_name = self.config['aws']['bucket_name']
            
            # Create output directory
            self.output_dir = Path('generated_images')
            self.output_dir.mkdir(exist_ok=True)
            
            print("AWS services initialized successfully")
            print(f"Images will be saved to: {self.output_dir.absolute()}")
            
        except Exception as e:
            print(f"Error in initialization: {str(e)}")
            raise

    def create_bucket(self):
        """Create S3 bucket if it doesn't exist"""
        try:
            print(f"Creating/checking bucket: {self.bucket_name}")
            try:
                self.s3.create_bucket(Bucket=self.bucket_name)
                print("Bucket created successfully")
            except self.s3.exceptions.BucketAlreadyExists:
                print(f"Using existing bucket: {self.bucket_name}")
            except self.s3.exceptions.BucketAlreadyOwnedByYou:
                print(f"Using your existing bucket: {self.bucket_name}")
        except Exception as e:
            print(f"Error with bucket: {str(e)}")
            raise

    def generate_image(self, prompt: str):
        """Generate image using AWS Bedrock"""
        try:
            print(f"\nGenerating image for: '{prompt}'")
            
            # Prepare request for Stable Diffusion
            body = json.dumps({
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 10,
                "steps": 50,
                "seed": 42
            })
            
            # Call Bedrock API
            response = self.bedrock.invoke_model(
                modelId="stability.stable-diffusion-xl-v1",
                body=body
            )
            
            # Extract image data
            response_body = json.loads(response['body'].read())
            image_data = response_body['artifacts'][0]['base64']
            
            print("Image generated successfully")
            return image_data
            
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            raise

    def process_image(self, prompt: str):
        """Main function to generate, save, and analyze image"""
        try:
            # Generate image
            base64_image = self.generate_image(prompt)
            image_data = base64.b64decode(base64_image)
            
            # Create filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_prompt = "".join(x for x in prompt if x.isalnum() or x in (' ', '-', '_'))[:50]
            image_filename = f"{safe_prompt}_{timestamp}.jpg"
            report_filename = f"{safe_prompt}_{timestamp}_analysis.txt"
            s3_key = f"test-images/{image_filename}"
            
            # Save image locally
            local_path = self.output_dir / image_filename
            with open(local_path, 'wb') as f:
                f.write(image_data)
            print(f"Image saved locally to: {local_path}")
            
            # Upload to S3
            print(f"Uploading to S3: {s3_key}")
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=image_data,
                ContentType='image/jpeg',
                Metadata={'prompt': prompt}
            )
            
            # Analyze with Rekognition
            print("Analyzing image with Rekognition...")
            response = self.rekognition.detect_labels(
                Image={
                    'S3Object': {
                        'Bucket': self.bucket_name,
                        'Name': s3_key
                    }
                },
                MaxLabels=10
            )
            
            # Save analysis report
            report_path = self.output_dir / report_filename
            with open(report_path, 'w') as f:
                f.write(f"Image Analysis Report\n")
                f.write(f"===================\n\n")
                f.write(f"Prompt: {prompt}\n")
                f.write(f"Generated: {timestamp}\n")
                f.write(f"Local Image: {local_path}\n")
                f.write(f"S3 Location: s3://{self.bucket_name}/{s3_key}\n\n")
                f.write("Detected Labels:\n")
                f.write("---------------\n")
                for label in response['Labels']:
                    f.write(f"- {label['Name']}: {label['Confidence']:.2f}%\n")
            
            print(f"Analysis report saved to: {report_path}")
            
            # Print results
            print("\nAnalysis Results:")
            print("================")
            for label in response['Labels']:
                print(f"- {label['Name']}: {label['Confidence']:.2f}%")
            
            return {
                'local_image': str(local_path),
                'report': str(report_path),
                's3_path': f"s3://{self.bucket_name}/{s3_key}"
            }
            
        except Exception as e:
            print(f"Error processing image: {str(e)}")
            raise

def get_prompt():
    """Get image prompt from user"""
    while True:
        prompt = input("\nEnter image description (or 'quit' to exit): ").strip()
        if prompt.lower() == 'quit':
            sys.exit(0)
        if prompt:
            return prompt
        print("Please enter a valid description!")

def main():
    print("\nAWS Image Generation and Analysis Demo")
    print("=====================================")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate and analyze images using AWS')
    parser.add_argument('--prompt', type=str, help='Image generation prompt')
    args = parser.parse_args()

    try:
        # Initialize AWS services
        demo = RekognitionDemo()
        
        # Create/verify S3 bucket
        demo.create_bucket()
        
        # Track generated images
        generated_images = []
        
        # Get first prompt
        prompt = args.prompt if args.prompt else get_prompt()
        
        # Process first image
        results = demo.process_image(prompt)
        generated_images.append(results)
        
        # Ask for more images
        while True:
            another = input("\nGenerate another image? (yes/no): ").strip().lower()
            if another == 'no':
                break
            elif another == 'yes':
                prompt = get_prompt()
                results = demo.process_image(prompt)
                generated_images.append(results)
            else:
                print("Please enter 'yes' or 'no'")
        
        # Print summary
        print("\nGenerated Images Summary:")
        print("=======================")
        for idx, img in enumerate(generated_images, 1):
            print(f"\nImage {idx}:")
            print(f"- Local file: {img['local_image']}")
            print(f"- Analysis report: {img['report']}")
            print(f"- S3 location: {img['s3_path']}")
        
        print(f"\nAll files saved in: {Path('generated_images').absolute()}")
        print("\nDemo completed successfully!")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
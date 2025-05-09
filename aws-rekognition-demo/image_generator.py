import boto3
import base64
import json
from logger_config import setup_logger

logger = setup_logger()

class BedrockImageGenerator:
    def __init__(self):
        self.bedrock = boto3.client(
            service_name='bedrock-runtime',
            region_name='us-east-1'
        )
        self.logger = logger

    def generate_image(self, prompt: str) -> bytes:
        """Generate image using AWS Bedrock"""
        try:
            self.logger.info(f"Generating image for prompt: {prompt}")
            
            body = json.dumps({
                "text_prompts": [{"text": prompt}],
                "cfg_scale": 10,
                "steps": 50,
                "seed": 42
            })
            
            response = self.bedrock.invoke_model(
                modelId="stability.stable-diffusion-xl-v1",
                body=body
            )
            
            response_body = json.loads(response['body'].read())
            image_data = base64.b64decode(response_body['artifacts'][0]['base64'])
            
            self.logger.info(f"Successfully generated image for prompt: {prompt}")
            return image_data
            
        except Exception as e:
            self.logger.error(f"Error generating image: {str(e)}")
            raise

    def generate_test_images(self) -> list:
        """Generate multiple test images with different prompts"""
        test_prompts = [
            "A professional office worker analyzing data on multiple screens",
            "A secure data center with servers and network equipment",
            "An AI robot performing image recognition tasks"
        ]
        
        generated_images = []
        for prompt in test_prompts:
            try:
                image_data = self.generate_image(prompt)
                generated_images.append({
                    'prompt': prompt,
                    'data': image_data
                })
                self.logger.info(f"Successfully generated image for prompt: {prompt}")
            except Exception as e:
                self.logger.error(f"Failed to generate image for prompt '{prompt}': {str(e)}")
                continue
                
        return generated_images
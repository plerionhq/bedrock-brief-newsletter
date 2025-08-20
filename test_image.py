#!/usr/bin/env python3
"""
Test script for image generation prompts using Amazon Titan Image Generator v2
"""

import json
import boto3
import base64
import random
import os
from typing import List, Optional

# Test introduction text
TEST_INTRODUCTION = """Welcome back, AI enthusiasts and cloud tinkerers! This week in the wild world of AWS, we've got a mixed bag of treats that'll make you laugh, cry, and possibly contemplate a career change to goat farming. (Don't worry, I hear there's an AWS service for that too.)

First up, AWS CEO Matt Garman is dishing out some parental wisdom that doesn't involve "turn it off and on again." He's betting big on critical thinking as the superhero skill of the AI age. Forget coding bootcamps—apparently, the secret sauce is asking more questions and playing board games. Who knew your Risk addiction was actually professional development? Check out the full story here for more on how to future-proof your career without a CS degree.

In less heartwarming news, AWS's new AI coding tool Kiro is causing wallets to weep across the developer landscape. What started as a promising spec-driven IDE has turned into a "wallet-wrecking tragedy" faster than you can say "unexpected charges." With pricing that makes some devs contemplate selling a kidney, it's clear that AWS missed the memo on "make it rain" not being a pricing strategy. Meanwhile, Amazon Q sits in the corner, looking suspiciously affordable by comparison.

Amidst the chaos, Arm is playing chess while everyone else is playing checkers. They've snagged Amazon's AI chip whiz, Rami Sinno, in a move that screams "if you can't beat 'em, poach 'em." With plans to build their own chips, Arm is stepping up from backseat driver to taking the wheel. Will this shake up the chip world, or is it just another tech giant midlife crisis? Only time (and probably a few overheated prototypes) will tell."""


def generate_image_prompt_from_introduction(introduction_text: str, model_id: str = "anthropic.claude-3-5-sonnet-20240620-v1:0") -> Optional[str]:
    """
    Use the primary LLM to generate a single high-quality image prompt for Titan based on the introduction.
    The prompt should describe a horizontal, text-free, creative feature image capturing the introduction's themes.
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

        prompt = (
            "Create a single creative prompt for an AI image model (Amazon Titan Image Generator) based on the newsletter introduction below.\n"
            "Requirements:\n"
            "- Use thick paint brush strokes and watercolor painting style"
            "- Abstract, cartoony imagery only (no people, no faces)\n"
            "- Include at least one rock element\n"
            "- No text, lettering, watermarks, logos, trademarks, or brand names\n"
            "- Do not depict specific products, UIs, or copyrighted characters\n"
            "- Horizontal/wide aspect composition suitable for a feature banner\n"
            "- Keep under 30 words.\n\n"
            "Respond with ONLY the image prompt text, no quotes or extra narration.\n\n"
            f"Introduction:\n{introduction_text}\n"
        )

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 300,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        })

        response = bedrock.invoke_model(
            body=body,
            modelId=model_id,
            accept="application/json",
            contentType="application/json"
        )
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text'].strip()
    except Exception as e:
        print(f"Error generating image prompt: {e}")
        return None


def generate_feature_image_and_save(prompt: str, output_dir: str = "test_output") -> Optional[str]:
    """
    Generate a horizontal feature image using Titan v2 and save locally.
    
    Returns the file path of the saved image on success, otherwise None.
    """
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        seed = random.randint(0, 2_147_483_647)

        # Build safe attempt prompts: original with safety prefix plus abstract fallbacks
        safety_prefix = (
            "Abstract, text-free, no people or faces, no logos or trademarks, no brand names."
        )
        attempts: List[str] = []
        if prompt:
            attempts.append((safety_prefix + (prompt or "")).strip())

        fallback_prompts = [
            "Abstract geometric waves and circuit traces in deep blue and teal, clean minimal tech banner, no text or logos",
            "Isometric circuit board patterns and network nodes, monochrome line art, modern wide banner, no text or branding",
            "Gradient mesh with polygonal network lines and subtle glows, futuristic technology vibe, wide banner, no text or logos",
        ]
        attempts.extend(fallback_prompts)

        for idx, attempt_prompt in enumerate(attempts):
            try:
                print(f"\n--- Attempt {idx + 1} ---")
                print(f"Prompt: {attempt_prompt}")
                
                safe_prompt = attempt_prompt.strip()[:512]
                cfg = 8.0 if idx == 0 else (6.5 if idx == 1 else 5.5)
                
                native_request = {
                    "taskType": "TEXT_IMAGE",
                    "textToImageParams": {
                        "text": safe_prompt
                    },
                    "imageGenerationConfig": {
                        "numberOfImages": 1,
                        "height": 768,
                        "width": 1408,
                        "cfgScale": cfg,
                        "seed": seed + idx
                    }
                }

                request = json.dumps(native_request)
                print(f"Request: {request}")
                
                response = bedrock.invoke_model(
                    modelId="amazon.titan-image-generator-v2:0",
                    body=request,
                    accept="application/json",
                    contentType="application/json",
                )
                
                model_response = json.loads(response["body"].read())
                base64_image_data = model_response["images"][0]
                image_bytes = base64.b64decode(base64_image_data)
                
                # Save image with attempt number
                filename = f"test_image_attempt_{idx + 1}.png"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                
                print(f"✅ Success! Image saved to: {filepath}")
                return filepath
                
            except Exception as e:
                err_text = str(e)
                print(f"❌ Attempt {idx + 1} failed: {err_text}")
                
                # Try next attempt if content was blocked or request malformed
                if "blocked" in err_text.lower() or "validationexception" in err_text.lower() or "malformed" in err_text.lower():
                    print("→ Content blocked or malformed, trying next attempt...")
                    continue
                else:
                    print("→ Other error, trying next attempt...")
                    continue
                    
    except Exception as e:
        print(f"❌ Error generating or saving feature image: {e}")
        return None


def main():
    """Main test function"""
    print("🎨 Testing Image Generation Prompts")
    print("=" * 50)
    
    # Check if AWS credentials are available
    try:
        boto3.client('sts').get_caller_identity()
        print("✅ AWS credentials found")
    except Exception as e:
        print(f"❌ AWS credentials not found: {e}")
        print("Please configure AWS credentials before running this script")
        return
    
    print(f"\n📝 Test Introduction Text:")
    print(f"Length: {len(TEST_INTRODUCTION)} characters")
    print(f"Preview: {TEST_INTRODUCTION[:200]}...")
    
    print(f"\n🤖 Generating Image Prompt...")
    image_prompt = generate_image_prompt_from_introduction(TEST_INTRODUCTION)
    
    if not image_prompt:
        print("❌ Failed to generate image prompt")
        return
    
    print(f"✅ Generated Prompt: {image_prompt}")
    
    print(f"\n🎨 Generating Image...")
    image_path = generate_feature_image_and_save(image_prompt)
    
    if image_path:
        print(f"\n🎉 Success! Test completed.")
        print(f"📁 Image saved to: {image_path}")
        print(f"🔍 Check the 'test_output' directory for generated images")
    else:
        print(f"\n❌ Failed to generate image after all attempts")


if __name__ == "__main__":
    main()

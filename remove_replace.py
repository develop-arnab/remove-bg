import boto3
from rembg import remove
import requests
from PIL import Image
from io import BytesIO
import base64
import json
import os

# Initialize the S3 client
s3_client = boto3.client("s3")


def lambda_handler(event, context):
    # Set your S3 bucket name
    bucket_name = "background-remover-bucket"

    # Check if the request contains an img_url or a base64 image in the body
    img_url = None
    img_name = None
    img_bytes = None

    try:
        if (
            "queryStringParameters" in event
            and "img_url" in event["queryStringParameters"]
        ):
            # Case 1: Image URL provided
            img_url = event["queryStringParameters"]["img_url"]
            img_name = img_url.split("/")[-1]

            # Download the image from the URL
            response = requests.get(img_url)
            img = Image.open(BytesIO(response.content))
            img_bytes = BytesIO()
            img.save(img_bytes, format="JPEG")
            img_bytes.seek(0)

        elif event.get("body"):
            # Case 2: Base64 image provided
            body = json.loads(event["body"])
            image_base64 = body.get("image_base64")

            if image_base64:
                # Decode the base64 image
                img_data = base64.b64decode(
                    image_base64.split(",")[1]
                )  # Ignore the data URL prefix
                img = Image.open(BytesIO(img_data))

                img_name = "uploaded_image.jpg"  # Or generate a unique name if needed
                img_bytes = BytesIO(img_data)
                img_bytes.seek(0)

        if not img_bytes:
            return {"statusCode": 400, "body": "Invalid image data"}

    except Exception as e:
        return {"statusCode": 400, "body": f"Error retrieving image: {str(e)}"}

    try:
        # Save the original image to S3
        original_s3_key = f"original/{img_name}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=original_s3_key,
            Body=img_bytes,
            ContentType="image/jpeg",
        )
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error saving original image to S3: {str(e)}",
        }

    try:
        # Step 3: Remove the background
        result = remove(img_bytes.getvalue())

        # Step 4: Save the background-removed image to S3
        output = BytesIO(result)
        removed_bg_s3_key = f"masked/{img_name}"
        s3_client.put_object(
            Bucket=bucket_name,
            Key=removed_bg_s3_key,
            Body=output,
            ContentType="image/jpeg",
        )
    except Exception as e:
        return {"statusCode": 500, "body": f"Error processing image: {str(e)}"}

    try:
        # Generate presigned URLs for the images
        original_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": original_s3_key},
            ExpiresIn=3600,  # 1 hour expiry time
        )
        removed_bg_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": removed_bg_s3_key},
            ExpiresIn=3600,  # 1 hour expiry time
        )
    except Exception as e:
        return {"statusCode": 500, "body": f"Error generating presigned URLs: {str(e)}"}
    print(" Original URL:", original_url, "Background-removed URL:", removed_bg_url)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "original_image_url": original_url,
                "background_removed_image_url": removed_bg_url,
            }
        ),
    }

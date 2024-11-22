FROM public.ecr.aws/lambda/python:3.8
RUN pip install requests rembg-aws-lambda boto3
COPY remove_replace.py ./
CMD ["remove_replace.lambda_handler"]
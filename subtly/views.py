from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.files.storage import default_storage
import subprocess
import os
import re
import boto3
import uuid



def index(request):
    return render(request,"index.html")


def upload_file(request):
    if request.method == 'POST':
        uploaded_file = request.FILES['file']
        myfilename = handle_uploaded_file(uploaded_file)
        # return render(request, 'index.html')
        extract_subtitles(myfilename)
        # subtitles = parse_srt_file(sub_path)
        # print(uploaded_file.name)
        
        # save_to_dynamo(uploaded_file.name, subtitles)
        save_to_s3(myfilename)
        
        return redirect(f'/subtitle/{myfilename}')
    
    return


def request_subtitle(request,fileid):
    if request.method == 'GET':
        # srtpath = os.path.join(f'media/output/{fileid}.srt')
        # subtitles = parse_srt_file(srtpath)
        # return HttpResponse(str(subtitles))
        return render(request, 'search.html', {'passed':True})
    elif request.method == 'POST':
        srtpath = os.path.join(f'media/output/{fileid}.srt')
        subtitles = parse_srt_file(srtpath)
        
        keyword = request.POST.get('keyword')
        if keyword==None or keyword=='':
            keyword='~!@@#$^%*'
        querysub = search_subtitles(keyword.strip(),subtitles)
        
        save_to_dynamo(fileid, querysub, keyword)
        
        return render(request, 'search.html', {'subtitles_data':querysub, 'passed':False}) 
    return


def handle_uploaded_file(uploaded_file):
    newfilename = str(uuid.uuid4()) + uploaded_file.name
    default_storage.save(newfilename, uploaded_file)
    return newfilename



def extract_subtitles(filename):
    video_file_location = os.path.join(f'media/{filename}')
    output_path = os.path.join(f'media/output/{filename}.srt')
    print(video_file_location)
    subprocess.run(['ccextractor', video_file_location, '-o', output_path])
    return output_path

    
    
def parse_srt_file(srt_file_path):
    subtitles = []
    with open(srt_file_path, 'r', encoding='utf-8-sig') as file:
        srt_data = file.read()
        subtitle_blocks = re.split(r'\n\s*\n', srt_data.strip())
        
        for block in subtitle_blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                index = int(lines[0].lstrip('\ufeff'))
                times = re.findall(r'(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                start_time, end_time = times[0], times[1]
                text = '\n'.join(lines[2:])
                
                subtitle = {
                    'index': index,
                    'start_time': start_time,
                    'end_time': end_time,
                    'text': text
                }
                
                subtitles.append(subtitle)
    
    return subtitles



def search_subtitles(keyword,subtitles):
    filtered_subs = []
    for i in subtitles:
        if keyword.lower() in i['text'].lower():
            filtered_subs.append(i)
    return filtered_subs


def save_to_s3(file_name):
    video_file_location = os.path.join(f'media/{file_name}')
    # Specify the file path, S3 bucket name, key (path + filename) on S3, and the credentials
    bucket_name = 'subtly'
    s3_key = 'videos/' + file_name

    # Create an S3 client with specified credentials and region
    s3 = boto3.client('s3', 
            aws_access_key_id='AKIAUQE3YQI5EU4XPFBQ', 
            aws_secret_access_key='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', 
            region_name='ap-south-1')

    # Upload the file
    s3.upload_file(video_file_location, bucket_name, s3_key)
    

def save_to_dynamo(file_name,subtitles,keyword):
    
    # Create a DynamoDB resource with specified credentials and region
    dynamodb = boto3.resource('dynamodb', 
                aws_access_key_id='AKIAUQE3YQI5EU4XPFBQ',
            aws_secret_access_key='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',
            region_name='ap-south-1'
    )
    # Specify the table name
    table_name = 'subtly'


    table = dynamodb.Table(table_name)

    # Specify the item to be inserted
    item = {
        'id': str(uuid.uuid4()),
        'video': file_name,
        'keyword': keyword,
        'result': subtitles
    }

    table.put_item(Item=item)

    print(f"Item inserted into DynamoDB table: {table_name}")

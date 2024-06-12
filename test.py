import time
import subprocess
from picamera2 import Picamera2, Preview
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime, timedelta
from firebase_admin import storage
from uuid import uuid4
import subprocess
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
CREDENTIALS_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH")

cred = credentials.Certificate(CREDENTIALS_PATH)
defaultapp = firebase_admin.initialize_app(cred, {
    'storageBucket': f"{PROJECT_ID}.appspot.com"
})
bucket = storage.bucket()
db = firestore.client()

# video capture
def capture_photo(file_path):
    picam = Picamera2()
    config = picam.create_preview_configuration()
    picam.configure(config)
    
    picam.start()
    #picam.start_preview(Preview.QTGL)
    
    time.sleep(2)
    picam.capture_file(file_path)
    print(f"Image captured: {file_path}")

    picam.stop()
    picam.close()
    
# yolo detect
def detect_objects(image_path):
    command = f"python detect.py --source {image_path} --project result --name img --weights yolov5s.pt --conf 0.25 --class 0 56 60 --save-txt"
    subprocess.run(command, shell=True)

# firebase img save
def file_upload(file, destination):
    blob = bucket.blob(destination)
    new_token = uuid4()
    metadata = {"firebaseStorageDownloadTokens": new_token}
    blob.metadata = metadata
    blob.upload_from_filename(filename=file, content_type='image/jpeg')
    print(blob.public_url)  # Storage path print
    print(blob.public_url.split('/')[-1])

# firebase text save
def save_class_counts_to_firestore(person, chair, table, timestamp):
    current_time = timestamp.strftime("%Y%m%d%H%M%S")
    doc_ref = db.collection(u'restaurant').document(current_time)
    timestamp2 = timestamp - timedelta(hours=9)
    print(timestamp2)
    doc_ref.set({
        u'person_counts': person,
        u'chair_count': chair,
        u'table_count': table,
        'time': timestamp2
    }) 

def read_class_counts_from_output(output_file_path):
    person_count = 0
    chair_count = 0
    table_count = 0

    file_list = [os.path.join(output_file_path, f) for f in os.listdir(output_file_path) if f.endswith('.txt')]
    recent_file = max(file_list, key=os.path.getctime)

    with open(recent_file, 'r') as file:
        lines = file.readlines()
        for line in lines:
            class_id = int(line.split()[0])

            if class_id == 0:
                person_count += 1
            elif class_id == 56:
                chair_count += 1
            elif class_id == 60:
                table_count += 1
    return {
        'person': person_count,
        'chair': chair_count,
        'table': table_count
    }
    
def main():
    try:
        capture_count = 1
        while True:
            image_path = f"capture{capture_count}.jpg"
            
            capture_photo(image_path)

            detect_objects(image_path)
            
            file = f"result/img/capture{capture_count}.jpg"
            destination = "result/" + image_path
            file_upload(file, destination) 
            
            class_counts = read_class_counts_from_output(f"result/img/labels/")
            
            timestamp = datetime.now()
            
            save_class_counts_to_firestore(class_counts['person'], class_counts['chair'], class_counts['table'], timestamp)
            print(timestamp)
            capture_count += 1
            time.sleep(5)

    except KeyboardInterrupt:
        print("Keyboard interrupt. Exiting...")

if __name__ == "__main__":
    main()
    print('success')
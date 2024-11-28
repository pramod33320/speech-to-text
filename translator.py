import os
import googletrans
import speech_recognition as sr
from datetime import datetime
import sys
import codecs
from pymongo import MongoClient
import gridfs

# Setting up the output encoding
sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Initialize speech recognition and translation
recognizer = sr.Recognizer()
translator = googletrans.Translator()

# MongoDB connection
MONGO_URI = "YOUR_MONGO_URI"
client = MongoClient(MONGO_URI)

# Connect to MongoDB using the URI
db = client['speech_to_text_db']  # Create or connect to the database
fs = gridfs.GridFS(db)  # Use GridFS for audio file storage
collection = db['audio_transcripts']  # Collection for text documents

# Create the "translator" folder if it doesn't exist
translator_folder = "Path_to_Store_your_Audio_&_txt_file."
os.makedirs(translator_folder, exist_ok=True)

# File paths for saving audio and text
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
text_file_path = os.path.join(translator_folder, f"speech_to_text_output_{current_time}.txt")
MIC_TIMEOUT = 5

# Capture audio from the microphone
with sr.Microphone() as source:
    print(f"Speak now in Hindi... You have {MIC_TIMEOUT} seconds to speak.")

    recognizer.adjust_for_ambient_noise(source)

    try:
        audio = recognizer.listen(source, timeout=MIC_TIMEOUT)

        text = recognizer.recognize_google(audio, language="hi-IN")
        print(f"Recognized Hindi Text: {text}")

    except sr.WaitTimeoutError:
        print(f"Listening timed out after {MIC_TIMEOUT} seconds.")
        text = None
    except sr.UnknownValueError:
        print("Sorry, I could not understand the audio.")
        text = None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        text = None

# If valid text is recognized, proceed with translation and saving to MongoDB
if text and text.strip():
    try:
        translation = translator.translate(text, dest="en")
        print(f"Translated English Text: {translation.text}")

        # Save text to the MongoDB collection
        text_document = {
            "recognized_hindi_text": text,
            "translated_english_text": translation.text,
            "timestamp": current_time
        }
        collection.insert_one(text_document)
        print(f"Text saved to MongoDB: {text_document}")

        # Save text to a file
        with open(text_file_path, "w", encoding="utf-8") as file:
            file.write(f"Recognized Hindi Text: {text}\n")
            file.write(f"Translated English Text: {translation.text}\n")

        print(f"Output saved to {text_file_path}")

    except Exception as e:
        print(f"Error occurred during translation or saving: {e}")
else:
    print("No valid text to translate.")

# Save the audio file to MongoDB using GridFS
audio_file_path = os.path.join(translator_folder, f"output_{current_time}.wav")
with open(audio_file_path, "wb") as f:
    f.write(audio.get_wav_data())
    print(f"Audio saved to {audio_file_path} for debugging.")

# Store audio in MongoDB GridFS
with open(audio_file_path, 'rb') as audio_file:
    audio_id = fs.put(audio_file, filename=f"output_{current_time}.wav")
    print(f"Audio file saved to MongoDB with ID: {audio_id}")

# Optionally, you can link the audio file ID with the text document in MongoDB
collection.update_one(
    {"_id": text_document["_id"]},
    {"$set": {"audio_id": audio_id}}
)

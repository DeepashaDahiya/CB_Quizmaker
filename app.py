import os
import re
import fitz  # PyMuPDF
from flask import Flask, request, render_template, redirect, url_for, jsonify, session
from flask_session import Session  # Import Flask-Session
from summarizer import Summarizer
import fitz
import gensim
import spacy
import nltk
from transformers import AutoTokenizer
from sklearn.feature_extraction.text import TfidfVectorizer
from fuzzywuzzy import fuzz
import pandas as pd
from nltk.corpus import stopwords
import nltk

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

from miss import *
from questiongenerator import QuestionGenerator
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
app = Flask(__name__)
AutoTokenizer.from_pretrained("iarfmoose/t5-base-question-generator")
# ✅ Properly Configure Flask-Session
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.path.join(os.getcwd(), "flask_sessions")  # Ensures session data is stored
app.config["SESSION_USE_SIGNER"] = True  # Prevents session tampering
app.config["SESSION_COOKIE_NAME"] = "my_session_cookie"  # Custom session cookie
app.config["SESSION_COOKIE_SECURE"] = False  # Change to True if using HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevents JavaScript from modifying session
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Ensures session is not lost on navigation
Session(app)  # Initialize Flask-Session


app.secret_key = "supersecretkey"  # Required to keep session data

nlp = spacy.load('en_core_web_sm', disable=['parser', 'ner'])

# Define folder to store uploaded PDFs
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure folder exists
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Load summarization model
summarizer = Summarizer()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/syllabus", methods=["GET"])
def syllabus_page():
    return render_template("syllabus.html")  # Ensure syllabus.html exist
@app.route("/summarization")
def summarization():
    """Fetch uploaded files from session and extract text"""
    if "uploaded_files" not in session:
        print("ERROR: No files found in session!")
        return render_template("summarization.html", summary="No files uploaded yet.")

    file_paths = session["uploaded_files"]
    print(f"DEBUG: Using uploaded files: {file_paths}")  # ✅ Debugging log

    extracted_text = ""
    for file_path in file_paths:
        extracted_text += extract_text_from_pdf(file_path) + "\n\n"  # ✅ Read each file

    return render_template("summarization.html", summary=extracted_text)

@app.route("/quiz")
def quiz():
    return render_template("quiz.html")

qg = QuestionGenerator()  # ✅ Correct Initialization


@app.route("/generate_quiz", methods=["POST"])
def generate_quiz():
    """Generates a quiz from uploaded notes."""
    if "uploaded_files" not in session:
        return jsonify({"error": "No file uploaded."})

    file_paths = session["uploaded_files"]
    full_text = ""

    # Extract text from all uploaded PDFs
    for file_path in file_paths:
        full_text += extract_text_from_pdf(file_path) + "\n\n"

    print("DEBUG: Generating quiz from text...")
    questions = qg.generate(full_text, num_questions=10, answer_style="sentences")  # Customize as needed

    return jsonify({"questions": questions})

@app.route("/analyze_gaps",methods=['POST'])
def analyze_gaps():
    try:
        print("DEBUG: /analyze_gaps endpoint called")
        if "uploaded_files" not in session or "syllabus" not in session:
            print("ERROR: No files found in session!")
            return jsonify({"error": "No files uploaded."})

        file_paths = session["uploaded_files"]
    # print(f"DEBUG: Summarizing entire text from files: {file_paths}")

        syllabus_paths = session["syllabus"]

        print("hi")

        if not file_paths or not syllabus_paths:
            return jsonify({"error": "No notes or syllabus uploaded"}), 400

    # Extract text from syllabus PDF
        syllabus_text = extract_text_from_pdf(syllabus_paths[0])
    
    # Extract textract_text_from_notes(notes_paths)

    # Extract topics from syllabus and notes
        syllabus_topics = extract_words_until_comma(syllabus_text)
        notes_texts=extract_text_from_notes(file_paths)
    # Preprocess and tokenize the notes text
        processed_texts = [preprocess_text(doc) for doc in notes_texts]
        lemmas = [tokenize(text) for text in processed_texts]

    # Create a dictionary and corpus for topic modeling
        id2word = gensim.corpora.Dictionary(lemmas)
        corpus = [id2word.doc2bow(text) for text in lemmas]

    # Build LDA model
        lda_model = gensim.models.LdaModel(corpus=corpus, id2word=id2word, num_topics=30, random_state=100, update_every=1, chunksize=100, passes=10, alpha='auto', per_word_topics=True)

    # Extract topics from LDA model
        topic_names = extract_topic_names(lda_model, num_words=30)
        LDA_topics = list(set([word for sublist in topic_names for word in sublist]))

        # Extract TF-IDF topics
        tfidf_topics = extract_tfidf_topics(notes_texts, n_topics=30)

    # Combine LDA and TF-IDF topics
        topics = list(set(tfidf_topics) | set(LDA_topics))
        print("topics")
        print("syllabus_topics")
    # Perform gap analysis
        missing_topics = check_missing_topics(syllabus_topics, topics)
    # print(f"Missing Topics: {missing_topics}")

    # Return missing topics as result
        print(f"DEBUG: Generated entire text summary.")
        return jsonify({"missing_topics":missing_topics})
    except Exception as e:
        print("CRITICAL ERROR:", str(e))  # Print error in Flask console
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500

@app.route("/upload_syllabus", methods=['POST'])
def upload_syllabus():

    file = request.files["syllabusUpload"]
    
    if file.filename == '':
        print("DEBUG: Empty filename received!")
        return jsonify({"error": "Empty file uploaded."})

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)

    session["syllabus"] = [file_path]  # Save syllabus in session
    session.modified = True

    print(f"DEBUG: Syllabus uploaded: {session['syllabus']}")
    return jsonify({"success": "File uploaded successfully!"})

@app.route("/debug_session")  # Change the route name
def debug_session():
    return jsonify({
        "uploaded_files": session.get("uploaded_files", "No files uploaded"),
        "syllabus": session.get("syllabus", "No syllabus uploaded")
    })



@app.route('/summarize_entire', methods=['POST'])
def summarize_entire():
    """Generates a summary for the entire uploaded text."""
    if "uploaded_files" not in session:
        print("ERROR: No files found in session!")
        return jsonify({"summary": "No files uploaded."})

    file_paths = session["uploaded_files"]
    print(f"DEBUG: Summarizing entire text from files: {file_paths}")

    # ✅ Extract text from all uploaded PDFs
    full_text = ""
    for file_path in file_paths:
        full_text += extract_text_from_pdf(file_path) + "\n\n"

    # ✅ Generate summary
    summary = summarizer(full_text, ratio=0.3) if full_text.strip() else "No content found in the uploaded files."

    print(f"DEBUG: Generated entire text summary.")
    return jsonify({"summary": summary})

# @app.route('/check_missing_topics', methods=['POST'])
# def check_missing_topics():
    
   


@app.route('/summarize_specific', methods=['POST'])
def summarize_specific():
    data = request.get_json()

    print("DEBUG: Received request to /summarize_specific with data:", data)  # ✅ Debugging log

    if not data or "topic" not in data:
        print("ERROR: No topic provided in request!")
        return jsonify({"summary": "No topic provided."})

    topic = data.get("topic", "").strip()

    print(f"DEBUG: Checking session before summarization: {session}")  # ✅ Print session data

    if "uploaded_files" not in session:
        print("ERROR: No file found in session!")  # ✅ Debugging log
        return jsonify({"summary": "No file uploaded."})

    file_paths = session["uploaded_files"]
    print(f"DEBUG: Using uploaded files: {file_paths}")  # ✅ Debugging log

    extracted_text = ""
    for file_path in file_paths:
        extracted_text += extract_text_from_pdf(file_path) + "\n\n"

    relevant_text = extract_relevant_text(extracted_text, [topic])
    summary = summarizer(relevant_text, ratio=0.3) if relevant_text != "No relevant sections found." else relevant_text

    print(f"DEBUG: Generated summary for topic '{topic}'")  # ✅ Debugging log
    return jsonify({"summary": summary})


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handles multiple file uploads without redirecting or displaying JSON"""
    files = request.files.getlist("fileUpload")  # Get all uploaded files
    topics_input = request.form.get("topics", "")

    if not files or files[0].filename == '':
        print("DEBUG: No file selected.")
        return "", 204  # ✅ Return an empty response (no content)

    uploaded_files = []  # ✅ Store all file paths

    for file in files:
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(file_path)  # Save each file
        uploaded_files.append(file_path)  # Store file path in list

    # ✅ Store all filenames in session
    session["uploaded_files"] = uploaded_files
    session["topics"] = topics_input
    session.modified = True  # ✅ Ensure session is saved

    print(f"DEBUG: Files uploaded and stored in session: {session.get('uploaded_files')}")
    
    # ✅ Return a completely empty response (no JSON, no redirect)
    return "", 204


@app.route('/check_session')
def check_session():
    """Debugging route to check session storage"""
    return jsonify({"uploaded_file": session.get("uploaded_file", "No file stored")})


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file"""
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

def extract_relevant_text(text, topics):
    """Extracts relevant paragraphs based on user-selected topics"""
    relevant_text = []
    paragraphs = text.split("\n\n")  # Split text into paragraphs

    for para in paragraphs:
        for topic in topics:
            if re.search(rf'\b{re.escape(topic)}\b', para, re.IGNORECASE):  # Case-insensitive search
                relevant_text.append(para)
                break  # Avoid duplicate entries

    return "\n\n".join(relevant_text) if relevant_text else "No relevant sections found."

if __name__ == '__main__':
    app.run(debug=True)


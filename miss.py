import os
from flask import Flask, request, render_template, redirect, url_for, session
import fitz  # PyMuPDF
import re
import gensim
import spacy
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from fuzzywuzzy import fuzz
import pandas as pd
from nltk.corpus import stopwords
# Initialize necessary components
stop_words = set(stopwords.words('english'))
def extract_text_from_notes(pdf_paths):
    all_text = []  # List to store texts from each document

    for pdf in pdf_paths:
        text = ""
        doc = fitz.open(pdf)

        # Extract text from each page
        for page in doc:
            text += page.get_text("text") + "\n"

        # Store the text of each document in the list (in lowercase)
        all_text.append(f'"""{text.lower()}"""')  # Store each document's text in triple quotes

    return all_text  # Return the list of texts
# Helper function to extract text from PDF
# def extract_text_from_pdf(pdf_path):
#     text = ""
#     doc = fitz.open(pdf_path)
#     for page in doc:
#         text += page.get_text("text") + "\n"
#     return text.lower() # PyMuPDF

# def extract_text_from_pdf(pdf_paths):
#     all_text = ""  # String to store the combined text from all PDFs
    
#     for pdf in pdf_paths:
#         doc = fitz.open(pdf)  # Open the PDF document
        
#         # Extract text from each page of the current document
#         for page in doc:
#             all_text += page.get_text("text") + "\n"  # Add text from each page to the all_text
    
#     # Convert all the text to lowercase (optional)
#     all_text = all_text.lower()
    
#     return all_text  # Return the combined text as a single string
def extract_text_from_pdf(pdf_input):
    all_text = ""  # String to store extracted text

    # ✅ FIX: If a single file is given, convert it to a list
    pdf_paths = [pdf_input] if isinstance(pdf_input, str) else pdf_input

    for pdf in pdf_paths:
        doc = fitz.open(pdf)  # Open the PDF document
        
        # Extract text from each page of the current document
        for page in doc:
            all_text += page.get_text("text") + "\n"  # Add text from each page
    
    return all_text.lower()  # Convert text to lowercase


# Function to extract words from text, until commas and parentheses
def extract_words_until_comma(text):
    text = re.sub(r'[\u200B-\u200D\u202A-\u202E\u202C\u200C\u200E\u200F\u202F\u2060\u2061\u2062\u2063\u2064\u206A-\u206D\u206F\uFEFF]', '', text)
    parts = text.split(',')
    final_list = []
    for part in parts:
        part = part.strip()
        split_by_parenthesis = re.split(r'\(', part)
        for segment in split_by_parenthesis:
            cleaned_part = segment.replace(')', '').replace('\n', '').strip()
            if cleaned_part:
                final_list.append(cleaned_part)
    return final_list

# Gap Analysis using fuzzywuzzy
def check_missing_topics(syllabus_topics, topics, threshold=50):
    missing_topics = []
    for topic in syllabus_topics:
        match_found = False
        for existing_topic in topics:
            similarity = fuzz.token_set_ratio(topic.lower(), existing_topic.lower())
            if similarity >= threshold:
                match_found = True
                break
        if not match_found:
            missing_topics.append(topic)
    return missing_topics

def preprocess_text(text):
    text = re.sub('\s+', ' ', text)  # Remove extra spaces
    text = re.sub('\S*@\S*\s?', '', text)  # Remove emails
    text = re.sub('\'', '', text)  # Remove apostrophes
    text = re.sub('[^a-zA-Z]', ' ', text)  # Remove non-alphabet characters
    text = text.lower()  # Convert to lowercase
    return text
def tokenize(text):
    tokens = gensim.utils.simple_preprocess(text, deacc=True)
    tokens = [token for token in tokens if token not in stop_words]
    return tokens


def lemmatize(tokens):
    doc = nlp(" ".join(tokens))
    return [token.lemma_ for token in doc]

# TF-IDF topic extraction
def extract_tfidf_topics(corpus, n_topics=30):
    cleaned_corpus = [preprocess_text(text) for text in corpus]
    tokens_list = [tokenize(text) for text in cleaned_corpus]
    cleaned_lemmas = [' '.join(tokens) for tokens in tokens_list]

    tfidf_vectorizer = TfidfVectorizer(max_features=30, stop_words='english')
    tfidf_matrix = tfidf_vectorizer.fit_transform(cleaned_lemmas)
    terms = tfidf_vectorizer.get_feature_names_out()

    tfidf_scores = pd.DataFrame(tfidf_matrix.toarray(), columns=terms)
    return list(tfidf_scores.sum(axis=0).sort_values(ascending=False).head(n_topics).index)

# LDA topic extraction
def extract_topic_names(lda_model, num_words=30):
    topic_names = []
    topics = lda_model.print_topics(num_words=num_words)
    for topic in topics:
        topic_words = topic[1].split(' + ')
        topic_name = [word.split('*')[1].strip().replace('"', '') for word in topic_words]
        topic_names.append(topic_name)
    return topic_names



